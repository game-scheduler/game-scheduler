# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Game management service with business logic.

Handles game CRUD operations, participant management, and event publishing.
"""

import datetime
import logging
import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from services.api.auth import discord_client as discord_client_module
from services.api.services import config as config_service
from services.api.services import participant_resolver as resolver_module
from shared.messaging import events as messaging_events
from shared.messaging import publisher as messaging_publisher
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import user as user_model
from shared.schemas import game as game_schemas

logger = logging.getLogger(__name__)


class GameService:
    """Service for game session management."""

    def __init__(
        self,
        db: AsyncSession,
        event_publisher: messaging_publisher.EventPublisher,
        discord_client: discord_client_module.DiscordAPIClient,
        participant_resolver: resolver_module.ParticipantResolver,
    ):
        """
        Initialize game service.

        Args:
            db: Database session
            event_publisher: RabbitMQ event publisher
            discord_client: Discord API client
            participant_resolver: Participant resolver service
        """
        self.db = db
        self.event_publisher = event_publisher
        self.discord_client = discord_client
        self.participant_resolver = participant_resolver

    async def create_game(
        self,
        game_data: game_schemas.GameCreateRequest,
        host_user_id: str,
        access_token: str,
    ) -> game_model.GameSession:
        """
        Create new game session with optional pre-populated participants.

        Args:
            game_data: Game creation data
            host_user_id: Host's database user ID (UUID)
            access_token: User's access token for Discord API

        Returns:
            Created game session

        Raises:
            ValidationError: If @mentions cannot be resolved
        """
        # Get guild and channel configurations
        guild_result = await self.db.execute(
            select(guild_model.GuildConfiguration).where(
                guild_model.GuildConfiguration.id == game_data.guild_id
            )
        )
        guild_config = guild_result.scalar_one_or_none()
        if guild_config is None:
            raise ValueError(f"Guild configuration not found for ID: {game_data.guild_id}")

        channel_result = await self.db.execute(
            select(channel_model.ChannelConfiguration).where(
                channel_model.ChannelConfiguration.id == game_data.channel_id
            )
        )
        channel_config = channel_result.scalar_one_or_none()
        if channel_config is None:
            raise ValueError(f"Channel configuration not found for ID: {game_data.channel_id}")

        # Get host user from database
        host_result = await self.db.execute(
            select(user_model.User).where(user_model.User.id == host_user_id)
        )
        host_user = host_result.scalar_one_or_none()
        if host_user is None:
            raise ValueError(f"Host user not found for ID: {host_user_id}")

        # Resolve settings with inheritance
        resolved_max_players = (
            game_data.max_players
            if game_data.max_players is not None
            else channel_config.max_players
            if channel_config.max_players is not None
            else guild_config.default_max_players
            if guild_config.default_max_players is not None
            else 10
        )
        resolved_reminder_minutes = (
            game_data.reminder_minutes
            if game_data.reminder_minutes is not None
            else channel_config.reminder_minutes
            if channel_config.reminder_minutes is not None
            else guild_config.default_reminder_minutes
            if guild_config.default_reminder_minutes is not None
            else [60, 15]
        )
        resolved_min_players = game_data.min_players

        # Validate min_players <= resolved max_players
        if resolved_min_players > resolved_max_players:
            raise ValueError(
                "Minimum players cannot be greater than maximum players "
                f"(min: {resolved_min_players}, max: {resolved_max_players})"
            )

        # Resolve initial participants if provided
        valid_participants = []
        if game_data.initial_participants:
            (
                valid_participants,
                validation_errors,
            ) = await self.participant_resolver.resolve_initial_participants(
                channel_config.channel_id,
                game_data.initial_participants,
                access_token,
            )

            if validation_errors:
                # Raise validation error with all form data
                raise resolver_module.ValidationError(
                    invalid_mentions=validation_errors,
                    valid_participants=[p["original_input"] for p in valid_participants],
                )

        # Create game session
        # Database stores timestamps as naive UTC, so convert timezone-aware inputs
        if game_data.scheduled_at.tzinfo is not None:
            scheduled_at_naive = game_data.scheduled_at.astimezone(datetime.UTC).replace(
                tzinfo=None
            )
        else:
            # Already naive, assume UTC
            scheduled_at_naive = game_data.scheduled_at

        game = game_model.GameSession(
            id=game_model.generate_uuid(),
            title=game_data.title,
            description=game_data.description,
            signup_instructions=game_data.signup_instructions,
            scheduled_at=scheduled_at_naive,
            guild_id=guild_config.id,
            channel_id=channel_config.id,
            host_id=host_user.id,
            max_players=resolved_max_players,
            min_players=resolved_min_players,
            reminder_minutes=resolved_reminder_minutes,
            notify_role_ids=game_data.notify_role_ids,
            status=game_model.GameStatus.SCHEDULED.value,
        )

        self.db.add(game)
        await self.db.flush()

        # Add pre-populated participants (host not included)
        for participant_data in valid_participants:
            if participant_data["type"] == "discord":
                user = await self.participant_resolver.ensure_user_exists(
                    self.db, participant_data["discord_id"]
                )
                participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=user.id,
                    display_name=None,
                    status=participant_model.ParticipantStatus.JOINED.value,
                    is_pre_populated=True,
                )
            else:  # placeholder
                participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=None,
                    display_name=participant_data["display_name"],
                    status=participant_model.ParticipantStatus.PLACEHOLDER.value,
                    is_pre_populated=True,
                )
            self.db.add(participant)

        await self.db.commit()

        # Reload game with relationships
        game = await self.get_game(game.id)
        if game is None:
            raise ValueError("Failed to reload created game")

        # Publish game.created event
        await self._publish_game_created(game, channel_config)

        return game

    async def get_game(self, game_id: str) -> game_model.GameSession | None:
        """
        Get game session by ID with participants, guild, and channel loaded.

        Args:
            game_id: Game session UUID

        Returns:
            Game session or None if not found
        """
        result = await self.db.execute(
            select(game_model.GameSession)
            .options(
                selectinload(game_model.GameSession.host),
                selectinload(game_model.GameSession.guild),
                selectinload(game_model.GameSession.channel),
                selectinload(game_model.GameSession.participants).selectinload(
                    participant_model.GameParticipant.user
                ),
            )
            .where(game_model.GameSession.id == game_id)
        )
        return result.scalar_one_or_none()

    async def list_games(
        self,
        guild_id: str | None = None,
        channel_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[game_model.GameSession], int]:
        """
        List games with optional filters.

        Args:
            guild_id: Filter by guild UUID
            channel_id: Filter by channel UUID
            status: Filter by status (SCHEDULED, IN_PROGRESS, etc.)
            limit: Maximum results
            offset: Results offset

        Returns:
            Tuple of (games list, total count)
        """
        query = select(game_model.GameSession).options(
            selectinload(game_model.GameSession.host),
            selectinload(game_model.GameSession.guild),
            selectinload(game_model.GameSession.channel),
            selectinload(game_model.GameSession.participants).selectinload(
                participant_model.GameParticipant.user
            ),
        )

        if guild_id:
            query = query.where(game_model.GameSession.guild_id == guild_id)
        if channel_id:
            query = query.where(game_model.GameSession.channel_id == channel_id)
        if status:
            query = query.where(game_model.GameSession.status == status)

        # Get total count
        count_query = select(func.count(game_model.GameSession.id))
        if guild_id:
            count_query = count_query.where(game_model.GameSession.guild_id == guild_id)
        if channel_id:
            count_query = count_query.where(game_model.GameSession.channel_id == channel_id)
        if status:
            count_query = count_query.where(game_model.GameSession.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = (
            query.order_by(game_model.GameSession.scheduled_at.asc()).limit(limit).offset(offset)
        )
        result = await self.db.execute(query)
        games = result.scalars().all()

        return list(games), total

    async def update_game(
        self,
        game_id: str,
        update_data: game_schemas.GameUpdateRequest,
        current_user,
        role_service,
        db: AsyncSession,
    ) -> game_model.GameSession:
        """
        Update game session with Bot Manager authorization.

        Args:
            game_id: Game session UUID
            update_data: Update data
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service
            db: Database session for authorization queries

        Returns:
            Updated game session

        Raises:
            ValueError: If game not found or user lacks permission
        """
        game = await self.get_game(game_id)
        if game is None:
            raise ValueError("Game not found")

        # Import here to avoid circular dependency
        from services.api.dependencies import permissions as permissions_deps

        # Check authorization: host, Bot Manager, or admin
        can_manage = await permissions_deps.can_manage_game(
            game_host_id=game.host.discord_id,
            guild_id=game.guild.guild_id,
            current_user=current_user,
            role_service=role_service,
            db=db,
        )

        if not can_manage:
            raise ValueError(
                "You don't have permission to update this game. "
                "Only the host, Bot Managers, or guild admins can edit games."
            )

        # Update fields
        if update_data.title is not None:
            game.title = update_data.title
        if update_data.description is not None:
            game.description = update_data.description
        if update_data.signup_instructions is not None:
            game.signup_instructions = update_data.signup_instructions
        if update_data.scheduled_at is not None:
            # Database stores timestamps as naive UTC, so convert timezone-aware inputs
            if update_data.scheduled_at.tzinfo is not None:
                game.scheduled_at = update_data.scheduled_at.astimezone(datetime.UTC).replace(
                    tzinfo=None
                )
            else:
                # Already naive, assume UTC
                game.scheduled_at = update_data.scheduled_at
        if update_data.max_players is not None:
            game.max_players = update_data.max_players
        if update_data.min_players is not None:
            game.min_players = update_data.min_players
        if update_data.reminder_minutes is not None:
            game.reminder_minutes = update_data.reminder_minutes
        if update_data.notify_role_ids is not None:
            game.notify_role_ids = update_data.notify_role_ids
        if update_data.status is not None:
            game.status = update_data.status

        # Validate min_players <= max_players after updates (if both are set)
        if (
            game.min_players is not None
            and game.max_players is not None
            and game.min_players > game.max_players
        ):
            raise ValueError(
                "Minimum players cannot be greater than maximum players "
                f"(min: {game.min_players}, max: {game.max_players})"
            )

        await self.db.commit()
        await self.db.refresh(game)

        # Publish game.updated event
        await self._publish_game_updated(game)

        return game

    async def delete_game(
        self,
        game_id: str,
        current_user,
        role_service,
        db: AsyncSession,
    ) -> None:
        """
        Cancel game session with Bot Manager authorization.

        Args:
            game_id: Game session UUID
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service
            db: Database session for authorization queries

        Raises:
            ValueError: If game not found or user lacks permission
        """
        game = await self.get_game(game_id)
        if game is None:
            raise ValueError("Game not found")

        # Import here to avoid circular dependency
        from services.api.dependencies import permissions as permissions_deps

        # Check authorization: host, Bot Manager, or admin
        can_manage = await permissions_deps.can_manage_game(
            game_host_id=game.host.discord_id,
            guild_id=game.guild.guild_id,
            current_user=current_user,
            role_service=role_service,
            db=db,
        )

        if not can_manage:
            raise ValueError(
                "You don't have permission to cancel this game. "
                "Only the host, Bot Managers, or guild admins can cancel games."
            )

        game.status = game_model.GameStatus.CANCELLED.value
        await self.db.commit()

        # Publish game.cancelled event
        await self._publish_game_cancelled(game)

    async def join_game(
        self,
        game_id: str,
        user_discord_id: str,
    ) -> participant_model.GameParticipant:
        """
        Join game as participant.

        Args:
            game_id: Game session UUID
            user_discord_id: User's Discord ID

        Returns:
            Created participant record

        Raises:
            ValueError: If already joined, game full, or game not scheduled
        """
        game = await self.get_game(game_id)
        if game is None:
            raise ValueError("Game not found")

        if game.status != game_model.GameStatus.SCHEDULED.value:
            raise ValueError("Game is not open for joining")

        # Get user (create if not exists)
        user = await self.participant_resolver.ensure_user_exists(self.db, user_discord_id)

        # Check if game is full (count non-placeholder participants)
        count_result = await self.db.execute(
            select(func.count(participant_model.GameParticipant.id)).where(
                participant_model.GameParticipant.game_session_id == game_id,
                participant_model.GameParticipant.user_id.isnot(None),
            )
        )
        participant_count = count_result.scalar() or 0

        # Resolve max players with inheritance
        guild_result = await self.db.execute(
            select(guild_model.GuildConfiguration).where(
                guild_model.GuildConfiguration.id == game.guild_id
            )
        )
        guild_config = guild_result.scalar_one_or_none()
        if guild_config is None:
            raise ValueError(f"Guild configuration not found for ID: {game.guild_id}")

        channel_result = await self.db.execute(
            select(channel_model.ChannelConfiguration).where(
                channel_model.ChannelConfiguration.id == game.channel_id
            )
        )
        channel_config = channel_result.scalar_one_or_none()
        if channel_config is None:
            raise ValueError(f"Channel configuration not found for ID: {game.channel_id}")

        resolver = config_service.SettingsResolver()
        max_players = resolver.resolve_max_players(game, channel_config, guild_config)

        if max_players is not None and participant_count >= max_players:
            raise ValueError("Game is full")

        # Add participant
        participant = participant_model.GameParticipant(
            game_session_id=game_id,
            user_id=user.id,
            display_name=None,
            status=participant_model.ParticipantStatus.JOINED.value,
            is_pre_populated=False,
        )
        self.db.add(participant)
        try:
            await self.db.commit()
            await self.db.refresh(participant)
        except IntegrityError:
            raise ValueError("User has already joined this game") from None

        # Publish game.updated event
        await self._publish_game_updated(game)

        return participant

    async def leave_game(
        self,
        game_id: str,
        user_discord_id: str,
    ) -> None:
        """
        Leave game as participant.

        Args:
            game_id: Game session UUID
            user_discord_id: User's Discord ID

        Raises:
            ValueError: If not a participant or game completed
        """
        logger.info(f"leave_game service: game_id={game_id}, user_discord_id={user_discord_id}")
        game = await self.get_game(game_id)
        if game is None:
            logger.error(f"Game not found: {game_id}")
            raise ValueError("Game not found")

        if game.status == game_model.GameStatus.COMPLETED.value:
            logger.error(f"Cannot leave completed game: {game_id}")
            raise ValueError("Cannot leave completed game")

        # Get user
        user_result = await self.db.execute(
            select(user_model.User).where(user_model.User.discord_id == user_discord_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            logger.error(f"User not found: discord_id={user_discord_id}")
            raise ValueError("User not found")

        logger.info(f"Found user: id={user.id}, discord_id={user.discord_id}")

        # Find participant
        participant_result = await self.db.execute(
            select(participant_model.GameParticipant).where(
                participant_model.GameParticipant.game_session_id == game_id,
                participant_model.GameParticipant.user_id == user.id,
            )
        )
        participant = participant_result.scalar_one_or_none()
        if participant is None:
            logger.error(f"Participant not found: game_id={game_id}, user_id={user.id}")
            raise ValueError("Not a participant of this game")

        logger.info(f"Found participant: id={participant.id}, deleting...")

        # Remove participant
        await self.db.delete(participant)
        await self.db.commit()
        logger.info("Participant deleted and committed")

        # Publish game.updated event
        await self._publish_game_updated(game)

    async def _publish_game_created(
        self,
        game: game_model.GameSession,
        channel_config: channel_model.ChannelConfiguration,
    ) -> None:
        """Publish game.created event to RabbitMQ."""
        event_data = messaging_events.GameCreatedEvent(
            game_id=uuid.UUID(game.id),
            title=game.title,
            guild_id=game.guild_id,
            channel_id=channel_config.channel_id,
            host_id=game.host_id,
            scheduled_at=game.scheduled_at,
            scheduled_at_unix=int(game.scheduled_at.timestamp()),
            max_players=game.max_players,
            notify_role_ids=game.notify_role_ids,
        )

        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_CREATED,
            data=event_data.model_dump(mode="json"),
        )

        await self.event_publisher.publish(event=event)

        logger.info(f"Published game.created event for game {game.id}")

    async def _publish_game_updated(self, game: game_model.GameSession) -> None:
        """Publish game.updated event to RabbitMQ."""
        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_UPDATED,
            data={
                "game_id": game.id,
                "message_id": game.message_id or "",
                "channel_id": game.channel_id,
            },
        )

        await self.event_publisher.publish(event=event)

        logger.info(f"Published game.updated event for game {game.id}")

    async def _publish_game_cancelled(self, game: game_model.GameSession) -> None:
        """Publish game.cancelled event to RabbitMQ."""
        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_CANCELLED,
            data={
                "game_id": game.id,
                "message_id": game.message_id or "",
                "channel_id": game.channel_id,
            },
        )

        await self.event_publisher.publish(event=event)

        logger.info(f"Published game.cancelled event for game {game.id}")
