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
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from services.api.auth import discord_client as discord_client_module
from services.api.auth import roles as roles_module
from services.api.services import notification_schedule as notification_schedule_service
from services.api.services import participant_resolver as resolver_module
from shared.messaging import events as messaging_events
from shared.messaging import publisher as messaging_publisher
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import game_status_schedule as game_status_schedule_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import template as template_model
from shared.models import user as user_model
from shared.schemas import game as game_schemas
from shared.utils import participant_sorting

logger = logging.getLogger(__name__)

# Default game duration when expected_duration_minutes is not set
DEFAULT_GAME_DURATION_MINUTES = 60


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
        Create new game session from template with optional pre-populated participants.

        Args:
            game_data: Game creation data with template_id
            host_user_id: Host's database user ID (UUID)
            access_token: User's access token for Discord API

        Returns:
            Created game session

        Raises:
            ValidationError: If @mentions cannot be resolved
            ValueError: If template not found or user unauthorized
        """
        # Get template
        template_result = await self.db.execute(
            select(template_model.GameTemplate).where(
                template_model.GameTemplate.id == game_data.template_id
            )
        )
        template = template_result.scalar_one_or_none()
        if template is None:
            raise ValueError(f"Template not found for ID: {game_data.template_id}")

        # Get guild config for permission checks
        guild_result = await self.db.execute(
            select(guild_model.GuildConfiguration).where(
                guild_model.GuildConfiguration.id == template.guild_id
            )
        )
        guild_config = guild_result.scalar_one_or_none()
        if guild_config is None:
            raise ValueError(f"Guild configuration not found for ID: {template.guild_id}")

        # Get host user from database
        host_result = await self.db.execute(
            select(user_model.User).where(user_model.User.id == host_user_id)
        )
        host_user = host_result.scalar_one_or_none()
        if host_user is None:
            raise ValueError(f"Host user not found for ID: {host_user_id}")

        # Check if user can host games with this template
        role_service = roles_module.get_role_service()
        can_host = await role_service.check_game_host_permission(
            host_user.discord_id,
            guild_config.guild_id,
            self.db,
            template.allowed_host_role_ids,
            access_token,
        )
        if not can_host:
            raise ValueError("User does not have permission to create games with this template")

        # Get channel config
        channel_result = await self.db.execute(
            select(channel_model.ChannelConfiguration).where(
                channel_model.ChannelConfiguration.id == template.channel_id
            )
        )
        channel_config = channel_result.scalar_one_or_none()
        if channel_config is None:
            raise ValueError(f"Channel configuration not found for ID: {template.channel_id}")

        # Use template defaults for optional fields
        max_players = game_data.max_players or template.max_players or 10
        reminder_minutes = game_data.reminder_minutes or template.reminder_minutes or [60, 15]
        expected_duration_minutes = (
            game_data.expected_duration_minutes or template.expected_duration_minutes
        )
        where = game_data.where or template.where
        signup_instructions = game_data.signup_instructions or template.signup_instructions

        # Locked fields from template
        channel_id = template.channel_id
        notify_role_ids = template.notify_role_ids
        allowed_player_role_ids = template.allowed_player_role_ids

        # Resolve initial participants if provided
        valid_participants: list[dict[str, Any]] = []
        if game_data.initial_participants:
            (
                valid_participants,
                validation_errors,
            ) = await self.participant_resolver.resolve_initial_participants(
                guild_config.guild_id,
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
            signup_instructions=signup_instructions,
            scheduled_at=scheduled_at_naive,
            where=where,
            template_id=template.id,
            guild_id=guild_config.id,
            channel_id=channel_id,
            host_id=host_user.id,
            max_players=max_players,
            reminder_minutes=reminder_minutes,
            expected_duration_minutes=expected_duration_minutes,
            notify_role_ids=notify_role_ids,
            allowed_player_role_ids=allowed_player_role_ids,
            status=game_model.GameStatus.SCHEDULED.value,
        )

        self.db.add(game)
        await self.db.flush()

        # Assign sequential positions to pre-populated participants
        # Position starts at 1 and increments for each pre-filled participant
        for position, participant_data in enumerate(valid_participants, start=1):
            if participant_data["type"] == "discord":
                user = await self.participant_resolver.ensure_user_exists(
                    self.db, participant_data["discord_id"]
                )
                participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=user.id,
                    display_name=None,
                    pre_filled_position=position,
                )
            else:  # placeholder
                participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=None,
                    display_name=participant_data["display_name"],
                    pre_filled_position=position,
                )
            self.db.add(participant)

        # Populate notification schedule
        schedule_service = notification_schedule_service.NotificationScheduleService(self.db)
        await schedule_service.populate_schedule(game, reminder_minutes)

        # Populate status transition schedule for SCHEDULED games
        if game.status == game_model.GameStatus.SCHEDULED.value:
            # Create IN_PROGRESS transition at scheduled time
            in_progress_schedule = game_status_schedule_model.GameStatusSchedule(
                id=str(uuid.uuid4()),
                game_id=game.id,
                target_status=game_model.GameStatus.IN_PROGRESS.value,
                transition_time=game.scheduled_at,
                executed=False,
            )
            self.db.add(in_progress_schedule)

            # Create COMPLETED transition at scheduled time + duration
            duration_minutes = expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
            completion_time = game.scheduled_at + datetime.timedelta(minutes=duration_minutes)

            completed_schedule = game_status_schedule_model.GameStatusSchedule(
                id=str(uuid.uuid4()),
                game_id=game.id,
                target_status=game_model.GameStatus.COMPLETED.value,
                transition_time=completion_time,
                executed=False,
            )
            self.db.add(completed_schedule)

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

    def _update_game_fields(
        self,
        game: game_model.GameSession,
        update_data: game_schemas.GameUpdateRequest,
    ) -> tuple[bool, bool]:
        """
        Update game fields from request data.

        Args:
            game: Game session to update
            update_data: Update data

        Returns:
            Tuple of (schedule_needs_update, status_schedule_needs_update)
        """
        schedule_needs_update = False
        status_schedule_needs_update = False

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
                game.scheduled_at = update_data.scheduled_at
            schedule_needs_update = True
            status_schedule_needs_update = True
        if update_data.where is not None:
            game.where = update_data.where
        if update_data.max_players is not None:
            game.max_players = update_data.max_players
        if update_data.reminder_minutes is not None:
            game.reminder_minutes = update_data.reminder_minutes
            schedule_needs_update = True
        if update_data.expected_duration_minutes is not None:
            game.expected_duration_minutes = update_data.expected_duration_minutes
        if update_data.notify_role_ids is not None:
            game.notify_role_ids = update_data.notify_role_ids
        if update_data.status is not None:
            game.status = update_data.status
            status_schedule_needs_update = True

        return schedule_needs_update, status_schedule_needs_update

    async def _remove_participants(
        self,
        game: game_model.GameSession,
        participant_ids: list[str],
    ) -> None:
        """
        Remove specified participants from game.

        Args:
            game: Game session
            participant_ids: List of participant IDs to remove
        """
        for participant_id in participant_ids:
            result = await self.db.execute(
                select(participant_model.GameParticipant).where(
                    participant_model.GameParticipant.id == participant_id,
                    participant_model.GameParticipant.game_session_id == game.id,
                )
            )
            participant = result.scalar_one_or_none()
            if participant:
                await self._publish_player_removed(game, participant)
                await self.db.delete(participant)
        await self.db.flush()

    async def _update_prefilled_participants(
        self,
        game: game_model.GameSession,
        participant_data_list: list[dict[str, Any]],
    ) -> None:
        """
        Update pre-filled participants for a game.

        Args:
            game: Game session
            participant_data_list: List of participant data dicts

        Raises:
            ValidationError: If @mentions cannot be resolved
        """
        # Get current pre-filled participants
        current_prefilled = await self.db.execute(
            select(participant_model.GameParticipant).where(
                participant_model.GameParticipant.game_session_id == game.id,
                participant_model.GameParticipant.pre_filled_position.isnot(None),
            )
        )
        current_participants = current_prefilled.scalars().all()

        # Separate existing participants (by ID) from new mentions
        existing_participant_ids = set()
        mentions_with_positions = []

        for participant_data in participant_data_list:
            if participant_data.get("participant_id"):
                existing_participant_ids.add(participant_data["participant_id"])
            elif str(participant_data.get("mention", "")).strip():
                mentions_with_positions.append(
                    (
                        str(participant_data["mention"]),
                        int(participant_data.get("pre_filled_position", 0)),
                    )
                )

        # Remove pre-filled participants not in the existing list
        for p in current_participants:
            if p.id not in existing_participant_ids:
                await self.db.delete(p)

        # Update positions for existing participants
        for participant_data in participant_data_list:
            if participant_data.get("participant_id"):
                participant_id = str(participant_data["participant_id"])
                position = int(participant_data.get("pre_filled_position", 0))
                for p in current_participants:
                    if p.id == participant_id:
                        p.pre_filled_position = position
                        break

        await self.db.flush()

        # Resolve and add new mentions
        if mentions_with_positions:
            await self._add_new_mentions(
                game=game,
                mentions_with_positions=mentions_with_positions,
            )

    async def _add_new_mentions(
        self,
        game: game_model.GameSession,
        mentions_with_positions: list[tuple[str, int]],
    ) -> None:
        """
        Resolve and add new participant mentions.

        Args:
            game: Game session
            mentions_with_positions: List of (mention, position) tuples

        Raises:
            ValidationError: If @mentions cannot be resolved
        """
        mentions = [mention for mention, _ in mentions_with_positions]

        (
            valid_participants,
            validation_errors,
        ) = await self.participant_resolver.resolve_initial_participants(
            game.guild.guild_id,
            mentions,
            "",
        )

        if validation_errors:
            raise resolver_module.ValidationError(
                invalid_mentions=validation_errors,
                valid_participants=[p["original_input"] for p in valid_participants],
            )

        # Create participant records
        for idx, p_data in enumerate(valid_participants):
            position = mentions_with_positions[idx][1]
            if p_data["type"] == "discord":
                user = await self.participant_resolver.ensure_user_exists(
                    self.db, p_data["discord_id"]
                )
                new_participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=user.id,
                    display_name=None,
                    pre_filled_position=position,
                )
            else:
                new_participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=None,
                    display_name=p_data["display_name"],
                    pre_filled_position=position,
                )
            self.db.add(new_participant)

        await self.db.flush()

    async def _update_status_schedules(
        self,
        game: game_model.GameSession,
    ) -> None:
        """
        Update status transition schedules for game.

        Args:
            game: Game session
        """
        status_schedule_result = await self.db.execute(
            select(game_status_schedule_model.GameStatusSchedule).where(
                game_status_schedule_model.GameStatusSchedule.game_id == game.id
            )
        )
        status_schedules = status_schedule_result.scalars().all()

        if game.status == game_model.GameStatus.SCHEDULED.value:
            # Ensure both IN_PROGRESS and COMPLETED schedules exist
            await self._ensure_in_progress_schedule(game, status_schedules)
            await self._ensure_completed_schedule(game, status_schedules)
        else:
            # Delete all schedules if game is not SCHEDULED
            for schedule in status_schedules:
                await self.db.delete(schedule)

    async def _ensure_in_progress_schedule(
        self,
        game: game_model.GameSession,
        status_schedules: Sequence[game_status_schedule_model.GameStatusSchedule],
    ) -> None:
        """
        Ensure IN_PROGRESS status schedule exists and is up to date.

        Args:
            game: Game session
            status_schedules: Existing status schedules
        """
        in_progress_schedule = next(
            (
                s
                for s in status_schedules
                if s.target_status == game_model.GameStatus.IN_PROGRESS.value
            ),
            None,
        )
        if in_progress_schedule:
            in_progress_schedule.transition_time = game.scheduled_at
            in_progress_schedule.executed = False
        else:
            in_progress_schedule = game_status_schedule_model.GameStatusSchedule(
                id=str(uuid.uuid4()),
                game_id=game.id,
                target_status=game_model.GameStatus.IN_PROGRESS.value,
                transition_time=game.scheduled_at,
                executed=False,
            )
            self.db.add(in_progress_schedule)

    async def _ensure_completed_schedule(
        self,
        game: game_model.GameSession,
        status_schedules: Sequence[game_status_schedule_model.GameStatusSchedule],
    ) -> None:
        """
        Ensure COMPLETED status schedule exists and is up to date.

        Args:
            game: Game session
            status_schedules: Existing status schedules
        """
        completed_schedule = next(
            (
                s
                for s in status_schedules
                if s.target_status == game_model.GameStatus.COMPLETED.value
            ),
            None,
        )
        duration_minutes = game.expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
        completion_time = game.scheduled_at + datetime.timedelta(minutes=duration_minutes)

        if completed_schedule:
            completed_schedule.transition_time = completion_time
            completed_schedule.executed = False
        else:
            completed_schedule = game_status_schedule_model.GameStatusSchedule(
                id=str(uuid.uuid4()),
                game_id=game.id,
                target_status=game_model.GameStatus.COMPLETED.value,
                transition_time=completion_time,
                executed=False,
            )
            self.db.add(completed_schedule)

    async def update_game(
        self,
        game_id: str,
        update_data: game_schemas.GameUpdateRequest,
        current_user,
        role_service,
    ) -> game_model.GameSession:
        """
        Update game session with Bot Manager authorization.

        Args:
            game_id: Game session UUID
            update_data: Update data
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service

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
            db=self.db,
        )

        if not can_manage:
            raise ValueError(
                "You don't have permission to update this game. "
                "Only the host, Bot Managers, or guild admins can edit games."
            )

        # Capture current participant state for promotion detection
        old_max_players = game.max_players or 10
        old_all_participants = [p for p in game.participants if p.user_id and p.user]
        old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
        old_overflow_ids = {
            p.user.discord_id
            for p in old_sorted_participants[old_max_players:]
            if p.user is not None
        }

        # Update game fields
        schedule_needs_update, status_schedule_needs_update = self._update_game_fields(
            game, update_data
        )

        # Handle participant removals
        if update_data.removed_participant_ids:
            await self._remove_participants(game, update_data.removed_participant_ids)

        # Handle participant updates
        if update_data.participants is not None:
            await self._update_prefilled_participants(game, update_data.participants)

        # Update notification schedule if needed
        if schedule_needs_update:
            reminder_minutes = (
                game.reminder_minutes if game.reminder_minutes is not None else [60, 15]
            )
            schedule_service = notification_schedule_service.NotificationScheduleService(self.db)
            await schedule_service.update_schedule(game, reminder_minutes)

        # Update status transition schedules if needed
        if status_schedule_needs_update:
            await self._update_status_schedules(game)

        await self.db.commit()

        # Reload game with all relationships
        game = await self.get_game(game.id)
        if game is None:
            raise ValueError("Failed to reload updated game")

        # Detect promotions from overflow to confirmed participants
        await self._detect_and_notify_promotions(
            game=game,
            old_overflow_ids=old_overflow_ids,
        )

        # Publish game.updated event
        await self._publish_game_updated(game)

        return game

    async def delete_game(
        self,
        game_id: str,
        current_user,
        role_service,
    ) -> None:
        """
        Cancel game session with Bot Manager authorization.

        Args:
            game_id: Game session UUID
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service

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
            db=self.db,
        )

        if not can_manage:
            raise ValueError(
                "You don't have permission to cancel this game. "
                "Only the host, Bot Managers, or guild admins can cancel games."
            )

        # Delete status schedules (CASCADE will handle game deletion)
        status_schedule_result = await self.db.execute(
            select(game_status_schedule_model.GameStatusSchedule).where(
                game_status_schedule_model.GameStatusSchedule.game_id == game.id
            )
        )
        status_schedules = status_schedule_result.scalars().all()
        for status_schedule in status_schedules:
            await self.db.delete(status_schedule)

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

        # Use game's max_players or default to 10
        max_players = game.max_players if game.max_players is not None else 10

        if max_players is not None and participant_count >= max_players:
            raise ValueError("Game is full")

        # Add participant
        participant = participant_model.GameParticipant(
            game_session_id=game_id,
            user_id=user.id,
            display_name=None,
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

    async def _publish_player_removed(
        self,
        game: game_model.GameSession,
        participant: participant_model.GameParticipant,
    ) -> None:
        """Publish game.player_removed event to RabbitMQ."""
        event = messaging_events.Event(
            event_type=messaging_events.EventType.PLAYER_REMOVED,
            data={
                "game_id": game.id,
                "participant_id": participant.id,
                "user_id": participant.user_id,
                "discord_id": participant.user.discord_id if participant.user else None,
                "display_name": participant.display_name,
                "message_id": game.message_id or "",
                "channel_id": game.channel_id,
                "game_title": game.title,
                "game_scheduled_at": game.scheduled_at.isoformat() if game.scheduled_at else None,
            },
        )

        await self.event_publisher.publish(event=event)

        logger.info(
            f"Published game.player_removed event for participant {participant.id} "
            f"from game {game.id}"
        )

    async def _detect_and_notify_promotions(
        self,
        game: game_model.GameSession,
        old_overflow_ids: set[str],
    ) -> None:
        """
        Detect and notify users promoted from overflow to confirmed participants.

        Compares previous overflow list with current confirmed list to identify
        users who were promoted. Sends DM notification to each promoted user.

        Args:
            game: Game session after updates applied
            old_overflow_ids: Set of Discord IDs that were in overflow before update
        """
        if not old_overflow_ids:
            # No one was in overflow, no promotions possible
            return

        # Get current participant state
        current_max_players = game.max_players or 10
        current_all_participants = [p for p in game.participants if p.user_id and p.user]
        current_sorted_participants = participant_sorting.sort_participants(
            current_all_participants
        )
        current_confirmed_participants = current_sorted_participants[:current_max_players]

        # Identify promoted users (were in overflow, now in confirmed)
        promoted_user_ids = [
            p.user.discord_id
            for p in current_confirmed_participants
            if p.user and p.user.discord_id in old_overflow_ids
        ]

        if not promoted_user_ids:
            logger.debug(f"No promotions detected for game {game.id}")
            return

        logger.info(
            f"Detected {len(promoted_user_ids)} promotions for game {game.id}: {promoted_user_ids}"
        )

        # Send notification to each promoted user
        for discord_id in promoted_user_ids:
            await self._publish_promotion_notification(
                game=game,
                discord_id=discord_id,
            )

    async def _publish_promotion_notification(
        self,
        game: game_model.GameSession,
        discord_id: str,
    ) -> None:
        """
        Publish promotion notification for a user moved from overflow to confirmed.

        Args:
            game: Game session
            discord_id: Discord ID of promoted user
        """
        scheduled_at_unix = int(game.scheduled_at.timestamp())

        message = (
            f"✅ Good news! A spot opened up in **{game.title}** "
            f"scheduled for <t:{scheduled_at_unix}:F>. "
            f"You've been moved from the waitlist to confirmed participants!"
        )

        notification_event = messaging_events.NotificationSendDMEvent(
            user_id=discord_id,
            game_id=uuid.UUID(game.id),
            game_title=game.title,
            game_time_unix=scheduled_at_unix,
            notification_type="waitlist_promotion",
            message=message,
        )

        event = messaging_events.Event(
            event_type=messaging_events.EventType.NOTIFICATION_SEND_DM,
            data=notification_event.model_dump(mode="json"),
        )

        await self.event_publisher.publish(event=event)

        logger.info(f"Published promotion notification for user {discord_id} in game {game.id}")
