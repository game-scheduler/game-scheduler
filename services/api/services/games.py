# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Game management service with business logic.

Handles game CRUD operations, participant management, and event publishing.
"""

import datetime
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from services.api.auth import roles as roles_module
from services.api.services import notification_schedule as notification_schedule_service
from services.api.services import participant_resolver as resolver_module
from services.api.services.notification_schedule import schedule_join_notification
from shared.discord import client as discord_client_module
from shared.message_formats import DMFormats
from shared.messaging import deferred_publisher as messaging_deferred_publisher
from shared.messaging import events as messaging_events
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import game_status_schedule as game_status_schedule_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import template as template_model
from shared.models import user as user_model
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.schemas import auth as auth_schemas
from shared.schemas import game as game_schemas
from shared.services.image_storage import release_image, store_image
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import (
    PartitionedParticipants,
    partition_participants,
)

logger = logging.getLogger(__name__)

# Default game duration when expected_duration_minutes is not set
DEFAULT_GAME_DURATION_MINUTES = 60


@dataclass
class GameMediaAttachments:
    """Media attachments for game creation."""

    thumbnail_data: bytes | None = None
    thumbnail_mime_type: str | None = None
    image_data: bytes | None = None
    image_mime_type: str | None = None


class GameService:
    """Service for game session management."""

    def __init__(
        self,
        db: AsyncSession,
        event_publisher: messaging_deferred_publisher.DeferredEventPublisher,
        discord_client: discord_client_module.DiscordAPIClient,
        participant_resolver: resolver_module.ParticipantResolver,
    ) -> None:
        """
        Initialize game service.

        Args:
            db: Database session
            event_publisher: Deferred RabbitMQ event publisher
            discord_client: Discord API client
            participant_resolver: Participant resolver service
        """
        self.db = db
        self.event_publisher = event_publisher
        self.discord_client = discord_client
        self.participant_resolver = participant_resolver

    async def _verify_bot_manager_permission(
        self,
        requester_user_id: str,
        guild_id: str,
        access_token: str,
    ) -> None:
        """Verify requester has bot manager permission."""
        requester_result = await self.db.execute(
            select(user_model.User).where(user_model.User.id == requester_user_id)
        )
        requester_user = requester_result.scalar_one_or_none()
        if requester_user is None:
            msg = f"Requester user not found for ID: {requester_user_id}"
            raise ValueError(msg)

        role_service = roles_module.get_role_service()
        is_bot_manager = await role_service.check_bot_manager_permission(
            requester_user.discord_id,
            guild_id,
            self.db,
            access_token,
        )

        if not is_bot_manager:
            msg = "Only bot managers can specify the game host"
            raise ValueError(msg)

    async def _resolve_and_validate_host_participant(
        self,
        host_mention: str,
        guild_id: str,
        access_token: str,
    ) -> dict[str, Any]:
        """Resolve host mention to a Discord user participant."""
        (
            resolved_hosts,
            validation_errors,
        ) = await self.participant_resolver.resolve_initial_participants(
            guild_id,
            [host_mention],
            access_token,
        )

        if validation_errors:
            raise resolver_module.ValidationError(
                invalid_mentions=validation_errors,
                valid_participants=[],
            )

        if not resolved_hosts:
            msg = f"Could not resolve host: {host_mention}"
            raise ValueError(msg)

        if resolved_hosts[0].get("type") != "discord":
            raise resolver_module.ValidationError(
                invalid_mentions=[
                    {
                        "input": host_mention,
                        "reason": (
                            "Game host must be a Discord user (use @username format). "
                            "Placeholder strings are not allowed for the host field."
                        ),
                        "suggestions": [],
                    }
                ],
                valid_participants=[],
            )

        return resolved_hosts[0]

    async def _get_or_create_user_by_discord_id(
        self,
        discord_id: str,
    ) -> user_model.User:
        """Get existing user or create new one for Discord ID."""
        host_user_result = await self.db.execute(
            select(user_model.User).where(user_model.User.discord_id == discord_id)
        )
        resolved_host_user = host_user_result.scalar_one_or_none()

        if resolved_host_user is None:
            resolved_host_user = user_model.User(
                id=user_model.generate_uuid(),
                discord_id=discord_id,
            )
            self.db.add(resolved_host_user)
            await self.db.flush()

        return resolved_host_user

    async def _resolve_game_host(
        self,
        game_data: game_schemas.GameCreateRequest,
        guild_config: guild_model.GuildConfiguration,
        requester_user_id: str,
        access_token: str,
    ) -> tuple[str, user_model.User]:
        """
        Resolve game host, handling override for bot managers.

        Args:
            game_data: Game creation data with optional host override
            guild_config: Guild configuration for permission checks
            requester_user_id: Database user ID of request initiator
            access_token: User's access token for Discord API

        Returns:
            Tuple of (host_user_id, host_user_object)

        Raises:
            ValueError: If user lacks bot manager permission or host cannot be resolved
            ValidationError: If host mention is invalid or not a Discord user
        """
        actual_host_user_id = requester_user_id

        if game_data.host and game_data.host.strip():
            await self._verify_bot_manager_permission(
                requester_user_id,
                guild_config.guild_id,
                access_token,
            )

            try:
                resolved_host = await self._resolve_and_validate_host_participant(
                    game_data.host,
                    guild_config.guild_id,
                    access_token,
                )

                host_discord_id = resolved_host["discord_id"]
                resolved_host_user = await self._get_or_create_user_by_discord_id(host_discord_id)
                actual_host_user_id = resolved_host_user.id

            except resolver_module.ValidationError:
                raise
            except Exception as e:
                msg = f"Failed to resolve host mention: {e!s}"
                raise ValueError(msg) from e

        host_result = await self.db.execute(
            select(user_model.User).where(user_model.User.id == actual_host_user_id)
        )
        host_user = host_result.scalar_one_or_none()
        if host_user is None:
            msg = f"Host user not found for ID: {actual_host_user_id}"
            raise ValueError(msg)

        return actual_host_user_id, host_user

    async def _create_participant_records(
        self,
        game_id: str,
        valid_participants: list[dict[str, Any]],
    ) -> None:
        """
        Create participant records for pre-filled participants.

        Handles both Discord users and placeholder participants, assigning
        sequential positions starting at 1.

        Args:
            game_id: ID of the game session
            valid_participants: List of validated participant data dictionaries
        """
        for position, participant_data in enumerate(valid_participants, start=1):
            if participant_data["type"] == "discord":
                user = await self.participant_resolver.ensure_user_exists(
                    self.db, participant_data["discord_id"]
                )
                participant = participant_model.GameParticipant(
                    game_session_id=game_id,
                    user_id=user.id,
                    display_name=None,
                    position_type=ParticipantType.HOST_ADDED,
                    position=position,
                )
            else:  # placeholder
                participant = participant_model.GameParticipant(
                    game_session_id=game_id,
                    user_id=None,
                    display_name=participant_data["display_name"],
                    position_type=ParticipantType.HOST_ADDED,
                    position=position,
                )
            self.db.add(participant)

        await self.db.flush()

    async def _create_game_status_schedules(
        self,
        game: game_model.GameSession,
        expected_duration_minutes: int | None,
    ) -> None:
        """
        Create status transition schedules for scheduled games.

        Creates IN_PROGRESS transition at scheduled time and COMPLETED transition
        at scheduled time + duration. Only creates schedules if game is SCHEDULED.

        Args:
            game: The game session to create schedules for
            expected_duration_minutes: Expected game duration, uses default if None
        """
        if game.status != game_model.GameStatus.SCHEDULED.value:
            return

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

    def _resolve_template_fields(
        self,
        game_data: game_schemas.GameCreateRequest,
        template: template_model.GameTemplate,
    ) -> dict[str, Any]:
        """
        Resolve game fields from request data and template defaults.

        Returns:
            Dictionary of resolved field values with keys: max_players,
            reminder_minutes, expected_duration_minutes, where,
            signup_instructions, signup_method
        """
        max_players = resolve_max_players(
            game_data.max_players if game_data.max_players is not None else template.max_players
        )
        reminder_minutes = (
            game_data.reminder_minutes
            if game_data.reminder_minutes is not None
            else (template.reminder_minutes or [60, 15])
        )
        expected_duration_minutes = (
            game_data.expected_duration_minutes
            if game_data.expected_duration_minutes is not None
            else template.expected_duration_minutes
        )
        where = game_data.where if game_data.where is not None else template.where
        signup_instructions = (
            game_data.signup_instructions
            if game_data.signup_instructions is not None
            else template.signup_instructions
        )

        signup_method = (
            game_data.signup_method
            or template.default_signup_method
            or SignupMethod.SELF_SIGNUP.value
        )

        # Validate signup method against template's allowed list if specified
        if template.allowed_signup_methods and signup_method not in template.allowed_signup_methods:
            allowed_str = ", ".join(template.allowed_signup_methods)
            msg = (
                f"Signup method '{signup_method}' not allowed for this template. "
                f"Allowed methods: {allowed_str}"
            )
            raise ValueError(msg)

        return {
            "max_players": max_players,
            "reminder_minutes": reminder_minutes,
            "expected_duration_minutes": expected_duration_minutes,
            "where": where,
            "signup_instructions": signup_instructions,
            "signup_method": signup_method,
        }

    async def _load_game_dependencies(
        self, template_id: str
    ) -> tuple[
        template_model.GameTemplate,
        guild_model.GuildConfiguration,
        channel_model.ChannelConfiguration,
    ]:
        """
        Load and validate template, guild, and channel configurations.

        Args:
            template_id: Template UUID to load dependencies for

        Returns:
            Tuple of (template, guild_config, channel_config)

        Raises:
            ValueError: If template, guild config, or channel config not found
        """
        template_result = await self.db.execute(
            select(template_model.GameTemplate).where(template_model.GameTemplate.id == template_id)
        )
        template = template_result.scalar_one_or_none()
        if template is None:
            msg = f"Template not found for ID: {template_id}"
            raise ValueError(msg)

        guild_result = await self.db.execute(
            select(guild_model.GuildConfiguration).where(
                guild_model.GuildConfiguration.id == template.guild_id
            )
        )
        guild_config = guild_result.scalar_one_or_none()
        if guild_config is None:
            msg = f"Guild configuration not found for ID: {template.guild_id}"
            raise ValueError(msg)

        channel_result = await self.db.execute(
            select(channel_model.ChannelConfiguration).where(
                channel_model.ChannelConfiguration.id == template.channel_id
            )
        )
        channel_config = channel_result.scalar_one_or_none()
        if channel_config is None:
            msg = f"Channel configuration not found for ID: {template.channel_id}"
            raise ValueError(msg)

        return template, guild_config, channel_config

    async def _build_game_session(
        self,
        game_data: game_schemas.GameCreateRequest,
        template: template_model.GameTemplate,
        guild_config: guild_model.GuildConfiguration,
        host_user: user_model.User,
        resolved_fields: dict[str, Any],
        media: GameMediaAttachments,
    ) -> game_model.GameSession:
        """
        Build GameSession instance with normalized data.

        Stores image data in game_images table and links via foreign keys.

        Args:
            game_data: Game creation request data
            template: Game template configuration
            guild_config: Guild configuration
            host_user: Host user record
            resolved_fields: Resolved template field values
            media: Media attachment data (thumbnail and banner image)

        Returns:
            GameSession instance ready for persistence
        """
        channel_id = template.channel_id
        notify_role_ids = template.notify_role_ids
        allowed_player_role_ids = template.allowed_player_role_ids

        # Database stores timestamps as naive UTC, so convert timezone-aware inputs
        if game_data.scheduled_at.tzinfo is not None:
            scheduled_at_naive = game_data.scheduled_at.astimezone(datetime.UTC).replace(
                tzinfo=None
            )
        else:
            scheduled_at_naive = game_data.scheduled_at

        # Store images and get IDs (handles deduplication automatically)
        thumbnail_id = None
        if media.thumbnail_data:
            logger.info(
                "_build_game_session: Storing thumbnail, size=%s",
                len(media.thumbnail_data),
            )
            thumbnail_id = await store_image(
                self.db, media.thumbnail_data, media.thumbnail_mime_type or "image/png"
            )
            logger.info("_build_game_session: Thumbnail stored with ID %s", thumbnail_id)

        banner_image_id = None
        if media.image_data:
            logger.info("_build_game_session: Storing banner, size=%s", len(media.image_data))
            banner_image_id = await store_image(
                self.db, media.image_data, media.image_mime_type or "image/png"
            )
            logger.info("_build_game_session: Banner stored with ID %s", banner_image_id)

        return game_model.GameSession(
            id=game_model.generate_uuid(),
            title=game_data.title,
            description=game_data.description,
            signup_instructions=resolved_fields["signup_instructions"],
            scheduled_at=scheduled_at_naive,
            where=resolved_fields["where"],
            template_id=template.id,
            guild_id=guild_config.id,
            channel_id=channel_id,
            host_id=host_user.id,
            max_players=resolved_fields["max_players"],
            reminder_minutes=resolved_fields["reminder_minutes"],
            expected_duration_minutes=resolved_fields["expected_duration_minutes"],
            notify_role_ids=notify_role_ids,
            allowed_player_role_ids=allowed_player_role_ids,
            signup_method=resolved_fields["signup_method"],
            status=game_model.GameStatus.SCHEDULED.value,
            thumbnail_id=thumbnail_id,
            banner_image_id=banner_image_id,
        )

    async def _setup_game_schedules(
        self,
        game: game_model.GameSession,
        reminder_minutes: list[int],
        expected_duration_minutes: int | None,
    ) -> None:
        """
        Set up all game schedules (join notifications, reminders, status transitions).

        Args:
            game: Game session to schedule notifications for
            reminder_minutes: List of minutes before game to send reminders
            expected_duration_minutes: Expected game duration in minutes (for status transitions)
        """
        # Schedule join notifications for newly added participants
        await self._schedule_join_notifications_for_game(game)

        # Populate reminder notification schedule
        schedule_service = notification_schedule_service.NotificationScheduleService(self.db)
        await schedule_service.populate_schedule(game, reminder_minutes)

        # Populate status transition schedule for SCHEDULED games
        await self._create_game_status_schedules(game, expected_duration_minutes)

    async def create_game(
        self,
        game_data: game_schemas.GameCreateRequest,
        host_user_id: str,
        access_token: str,
        thumbnail_data: bytes | None = None,
        thumbnail_mime_type: str | None = None,
        image_data: bytes | None = None,
        image_mime_type: str | None = None,
    ) -> game_model.GameSession:
        """
        Create new game session from template with optional pre-populated participants.

        Does not commit. Caller must commit transaction.

        Args:
            game_data: Game creation data with template_id
            host_user_id: Host's database user ID (UUID)
            access_token: User's access token for Discord API
            thumbnail_data: Optional thumbnail image binary data
            thumbnail_mime_type: Optional thumbnail MIME type
            image_data: Optional banner image binary data
            image_mime_type: Optional banner MIME type

        Returns:
            Created game session

        Raises:
            ValidationError: If @mentions cannot be resolved
            ValueError: If template not found or user unauthorized
        """
        # Load template, guild, and channel configurations
        template, guild_config, channel_config = await self._load_game_dependencies(
            game_data.template_id
        )

        # Resolve host (handles bot manager override)
        _actual_host_user_id, host_user = await self._resolve_game_host(
            game_data, guild_config, host_user_id, access_token
        )

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
            msg = "User does not have permission to create games with this template"
            raise ValueError(msg)

        # Resolve field values from request and template
        resolved_fields = self._resolve_template_fields(game_data, template)

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

        # Build game session with media attachments
        media = GameMediaAttachments(
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime_type,
            image_data=image_data,
            image_mime_type=image_mime_type,
        )

        game = await self._build_game_session(
            game_data, template, guild_config, host_user, resolved_fields, media
        )

        self.db.add(game)
        await self.db.flush()

        # Create participant records for pre-filled participants
        await self._create_participant_records(game.id, valid_participants)

        # Reload game with participants to check confirmed vs waitlisted
        # Use selectinload to eager load participants AND their nested user relationships
        # to prevent lazy loading errors in partition_participants()
        result = await self.db.execute(
            select(game_model.GameSession)
            .where(game_model.GameSession.id == game.id)
            .options(
                selectinload(game_model.GameSession.participants).selectinload(
                    participant_model.GameParticipant.user
                )
            )
        )
        game = result.scalar_one()

        # Set up all game schedules (join notifications, reminders, status transitions)
        await self._setup_game_schedules(
            game,
            resolved_fields["reminder_minutes"],
            resolved_fields["expected_duration_minutes"],
        )

        # Reload game with relationships
        game = await self.get_game(game.id)
        if game is None:
            msg = "Failed to reload created game"
            raise ValueError(msg)

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

    def _update_simple_text_fields(
        self,
        game: game_model.GameSession,
        update_data: game_schemas.GameUpdateRequest,
    ) -> None:
        """
        Update simple text fields that don't affect schedules.

        Args:
            game: Game session to update
            update_data: Update data
        """
        if update_data.title is not None:
            game.title = update_data.title
        if update_data.description is not None:
            game.description = update_data.description
        if update_data.signup_instructions is not None:
            game.signup_instructions = update_data.signup_instructions
        if update_data.where is not None:
            game.where = update_data.where

    def _update_scheduled_at_field(
        self,
        game: game_model.GameSession,
        update_data: game_schemas.GameUpdateRequest,
    ) -> bool:
        """
        Update scheduled_at field with timezone handling.

        Args:
            game: Game session to update
            update_data: Update data

        Returns:
            True if schedule needs update, False otherwise
        """
        if update_data.scheduled_at is None:
            return False

        if update_data.scheduled_at.tzinfo is not None:
            game.scheduled_at = update_data.scheduled_at.astimezone(datetime.UTC).replace(
                tzinfo=None
            )
        else:
            game.scheduled_at = update_data.scheduled_at
        return True

    def _update_schedule_affecting_fields(
        self,
        game: game_model.GameSession,
        update_data: game_schemas.GameUpdateRequest,
    ) -> bool:
        """
        Update fields that affect notification schedules.

        Args:
            game: Game session to update
            update_data: Update data

        Returns:
            True if schedule needs update, False otherwise
        """
        schedule_needs_update = False

        if update_data.reminder_minutes is not None:
            game.reminder_minutes = update_data.reminder_minutes
            schedule_needs_update = True

        return schedule_needs_update

    def _update_remaining_fields(
        self,
        game: game_model.GameSession,
        update_data: game_schemas.GameUpdateRequest,
    ) -> bool:
        """
        Update remaining fields (max_players, duration, roles, status, signup_method).

        Args:
            game: Game session to update
            update_data: Update data

        Returns:
            True if status schedule needs update, False otherwise
        """
        status_schedule_needs_update = False

        if update_data.max_players is not None:
            game.max_players = update_data.max_players
        if update_data.expected_duration_minutes is not None:
            game.expected_duration_minutes = update_data.expected_duration_minutes
        if update_data.notify_role_ids is not None:
            game.notify_role_ids = update_data.notify_role_ids
        if update_data.status is not None:
            game.status = update_data.status
            status_schedule_needs_update = True
        if update_data.signup_method is not None:
            game.signup_method = update_data.signup_method

        return status_schedule_needs_update

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
        # Update simple text fields that don't affect schedules
        self._update_simple_text_fields(game, update_data)

        # Update scheduled_at with timezone handling (affects both schedules)
        scheduled_at_updated = self._update_scheduled_at_field(game, update_data)

        # Update fields that affect notification schedules
        schedule_needs_update = self._update_schedule_affecting_fields(game, update_data)

        # Update remaining fields (max_players, duration, roles, status, signup_method)
        status_schedule_needs_update = self._update_remaining_fields(game, update_data)

        # scheduled_at affects both schedules
        if scheduled_at_updated:
            schedule_needs_update = True
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
                select(participant_model.GameParticipant)
                .where(
                    participant_model.GameParticipant.id == participant_id,
                    participant_model.GameParticipant.game_session_id == game.id,
                )
                .options(selectinload(participant_model.GameParticipant.user))
            )
            participant = result.scalar_one_or_none()
            if participant:
                await self._publish_player_removed(game, participant)
                await self.db.delete(participant)
        await self.db.flush()

    def _separate_existing_and_new_participants(
        self, participant_data_list: list[dict[str, Any]]
    ) -> tuple[set[str], list[tuple[str, int]]]:
        """
        Separate existing participant IDs from new mentions.

        Args:
            participant_data_list: List of participant data dicts

        Returns:
            Tuple of (existing_participant_ids, mentions_with_positions)
        """
        existing_participant_ids = set()
        mentions_with_positions = []

        for participant_data in participant_data_list:
            if participant_data.get("participant_id"):
                existing_participant_ids.add(participant_data["participant_id"])
            elif str(participant_data.get("mention", "")).strip():
                mentions_with_positions.append((
                    str(participant_data["mention"]),
                    int(participant_data.get("position", 0)),
                ))

        return existing_participant_ids, mentions_with_positions

    async def _remove_outdated_participants(
        self,
        current_participants: Sequence[participant_model.GameParticipant],
        existing_participant_ids: set[str],
    ) -> None:
        """
        Remove pre-filled participants not in the existing list.

        Args:
            current_participants: Current host-added participants
            existing_participant_ids: Set of participant IDs to keep
        """
        for p in current_participants:
            if p.id not in existing_participant_ids:
                await self.db.delete(p)

    def _update_participant_positions(
        self,
        current_participants: Sequence[participant_model.GameParticipant],
        participant_data_list: list[dict[str, Any]],
    ) -> None:
        """
        Update positions for existing participants.

        Args:
            current_participants: Current host-added participants
            participant_data_list: List of participant data dicts with positions
        """
        for participant_data in participant_data_list:
            if participant_data.get("participant_id"):
                participant_id = str(participant_data["participant_id"])
                position = int(participant_data.get("position", 0))
                for p in current_participants:
                    if p.id == participant_id:
                        p.position = position
                        break

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
        # Get current host-added participants
        current_prefilled = await self.db.execute(
            select(participant_model.GameParticipant).where(
                participant_model.GameParticipant.game_session_id == game.id,
                participant_model.GameParticipant.position_type == ParticipantType.HOST_ADDED,
            )
        )
        current_participants = current_prefilled.scalars().all()

        # Separate existing participants (by ID) from new mentions
        (
            existing_participant_ids,
            mentions_with_positions,
        ) = self._separate_existing_and_new_participants(participant_data_list)

        # Remove pre-filled participants not in the existing list
        await self._remove_outdated_participants(current_participants, existing_participant_ids)

        # Update positions for existing participants
        self._update_participant_positions(current_participants, participant_data_list)

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
                    position_type=ParticipantType.HOST_ADDED,
                    position=position,
                )
            else:
                new_participant = participant_model.GameParticipant(
                    game_session_id=game.id,
                    user_id=None,
                    display_name=p_data["display_name"],
                    position_type=ParticipantType.HOST_ADDED,
                    position=position,
                )
            self.db.add(new_participant)

        await self.db.flush()

        # Schedule join notifications for newly added participants
        await self._schedule_join_notifications_for_game(game)

    async def _schedule_join_notifications_for_game(self, game: game_model.GameSession) -> None:
        """
        Schedule join notifications for confirmed Discord participants of a game.

        Creates notification schedule entries for Discord users (participants with user_id)
        who are confirmed (not on waitlist). Each notification is scheduled to be sent
        60 seconds after the participant joined.

        Args:
            game: Game session with participants relationship loaded
        """
        # Only notify confirmed participants, not waitlisted ones
        partitioned = partition_participants(game.participants, game.max_players)

        for participant in partitioned.confirmed:
            # Only schedule for Discord users (participants with user_id)
            if participant.user_id:
                await schedule_join_notification(
                    db=self.db,
                    game_id=game.id,
                    participant_id=participant.id,
                    game_scheduled_at=game.scheduled_at,
                    delay_seconds=60,
                )

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

    def _capture_old_state(
        self, game: game_model.GameSession
    ) -> tuple[int, list[participant_model.GameParticipant], PartitionedParticipants]:
        """
        Capture game participant state before updates for promotion detection.

        Args:
            game: Game session before updates

        Returns:
            Tuple of (old_max_players, old_participants_snapshot, old_partitioned)
        """
        old_max_players = resolve_max_players(game.max_players)
        old_participants_snapshot = [
            participant_model.GameParticipant(
                id=p.id,
                game_session_id=p.game_session_id,
                user_id=p.user_id,
                user=p.user,
                display_name=p.display_name,
                position=p.position,
                position_type=p.position_type,
                joined_at=p.joined_at,
            )
            for p in game.participants
        ]
        old_partitioned = partition_participants(old_participants_snapshot, old_max_players)
        return old_max_players, old_participants_snapshot, old_partitioned

    async def _update_image_fields(
        self,
        game: game_model.GameSession,
        thumbnail_data: bytes | None,
        thumbnail_mime_type: str | None,
        image_data: bytes | None,
        image_mime_type: str | None,
    ) -> None:
        """
        Update game thumbnail and banner images with reference counting.

        Releases old images (decrements reference count) before storing new ones.
        Images are automatically deleted when reference count reaches zero.

        Args:
            game: Game session to update
            thumbnail_data: Optional thumbnail binary data (empty bytes to remove)
            thumbnail_mime_type: Optional thumbnail MIME type
            image_data: Optional banner image binary data (empty bytes to remove)
            image_mime_type: Optional banner MIME type
        """
        if thumbnail_data is not None:
            if thumbnail_data == b"":
                # Remove thumbnail: release old image
                await release_image(self.db, game.thumbnail_id)
                game.thumbnail_id = None
            else:
                # Replace thumbnail: release old, store new
                await release_image(self.db, game.thumbnail_id)
                game.thumbnail_id = await store_image(
                    self.db, thumbnail_data, thumbnail_mime_type or "image/png"
                )

        if image_data is not None:
            if image_data == b"":
                # Remove banner: release old image
                await release_image(self.db, game.banner_image_id)
                game.banner_image_id = None
            else:
                # Replace banner: release old, store new
                await release_image(self.db, game.banner_image_id)
                game.banner_image_id = await store_image(
                    self.db, image_data, image_mime_type or "image/png"
                )

    async def _process_game_update_schedules(
        self,
        game: game_model.GameSession,
        schedule_needs_update: bool,
        status_schedule_needs_update: bool,
    ) -> None:
        """
        Update notification and status transition schedules if needed.

        Args:
            game: Game session
            schedule_needs_update: Whether notification schedule needs update
            status_schedule_needs_update: Whether status schedule needs update
        """
        if schedule_needs_update:
            reminder_minutes = (
                game.reminder_minutes if game.reminder_minutes is not None else [60, 15]
            )
            schedule_service = notification_schedule_service.NotificationScheduleService(self.db)
            await schedule_service.update_schedule(game, reminder_minutes)

        if status_schedule_needs_update:
            await self._update_status_schedules(game)

    async def _detect_and_notify_promotions(
        self,
        game: game_model.GameSession,
        old_partitioned: PartitionedParticipants,
    ) -> None:
        """
        Detect waitlist promotions and notify promoted users.

        Args:
            game: Updated game session
            old_partitioned: Partitioned participants before update
        """
        new_max_players = resolve_max_players(game.max_players)
        new_partitioned = partition_participants(game.participants, new_max_players)
        promoted_discord_ids = new_partitioned.cleared_waitlist(old_partitioned)

        if promoted_discord_ids:
            await self._notify_promoted_users(
                game=game,
                promoted_discord_ids=promoted_discord_ids,
            )

    async def update_game(
        self,
        game_id: str,
        update_data: game_schemas.GameUpdateRequest,
        current_user: auth_schemas.CurrentUser,
        role_service: roles_module.RoleVerificationService,
        thumbnail_data: bytes | None = None,
        thumbnail_mime_type: str | None = None,
        image_data: bytes | None = None,
        image_mime_type: str | None = None,
    ) -> game_model.GameSession:
        """
        Update game session with Bot Manager authorization.

        Does not commit. Caller must commit transaction.

        Args:
            game_id: Game session UUID
            update_data: Update data
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service
            thumbnail_data: Optional thumbnail image binary data (empty bytes to remove)
            thumbnail_mime_type: Optional thumbnail MIME type (empty string to remove)
            image_data: Optional banner image binary data (empty bytes to remove)
            image_mime_type: Optional banner MIME type (empty string to remove)

        Returns:
            Updated game session

        Raises:
            ValueError: If game not found or user lacks permission
        """
        game = await self.get_game(game_id)
        if game is None:
            msg = "Game not found"
            raise ValueError(msg)

        from services.api.dependencies import (  # noqa: PLC0415
            permissions as permissions_deps,
        )

        # Check authorization: host, Bot Manager, or admin
        can_manage = await permissions_deps.can_manage_game(
            game_host_id=game.host.discord_id,
            guild_id=game.guild.guild_id,
            current_user=current_user,
            role_service=role_service,
            db=self.db,
        )

        if not can_manage:
            msg = (
                "You don't have permission to update this game. "
                "Only the host, Bot Managers, or guild admins can edit games."
            )
            raise ValueError(msg)

        # Capture current participant state for promotion detection
        (
            _old_max_players,
            _old_participants_snapshot,
            old_partitioned,
        ) = self._capture_old_state(game)

        # Update game fields
        schedule_needs_update, status_schedule_needs_update = self._update_game_fields(
            game, update_data
        )

        # Update images if provided
        await self._update_image_fields(
            game, thumbnail_data, thumbnail_mime_type, image_data, image_mime_type
        )

        # Handle participant removals
        if update_data.removed_participant_ids:
            await self._remove_participants(game, update_data.removed_participant_ids)

        # Handle participant updates
        if update_data.participants is not None:
            await self._update_prefilled_participants(game, update_data.participants)

        # Update schedules if needed
        await self._process_game_update_schedules(
            game, schedule_needs_update, status_schedule_needs_update
        )

        # Refresh game object to get updated relationships from database
        await self.db.refresh(game, ["participants"])

        # Reload game with all relationships
        game = await self.get_game(game.id)
        if game is None:
            msg = "Failed to reload updated game"
            raise ValueError(msg)

        # Detect promotions and notify promoted users
        await self._detect_and_notify_promotions(game, old_partitioned)

        # Publish game.updated event
        await self._publish_game_updated(game)

        return game

    async def delete_game(
        self,
        game_id: str,
        current_user: auth_schemas.CurrentUser,
        role_service: roles_module.RoleVerificationService,
    ) -> None:
        """
        Cancel game session with Bot Manager authorization.

        Does not commit. Caller must commit transaction.

        Args:
            game_id: Game session UUID
            current_user: Current authenticated user (CurrentUser schema)
            role_service: Role verification service

        Raises:
            ValueError: If game not found or user lacks permission
        """
        game = await self.get_game(game_id)
        if game is None:
            msg = "Game not found"
            raise ValueError(msg)

        from services.api.dependencies import (  # noqa: PLC0415
            permissions as permissions_deps,
        )

        # Check authorization: host, Bot Manager, or admin
        can_manage = await permissions_deps.can_manage_game(
            game_host_id=game.host.discord_id,
            guild_id=game.guild.guild_id,
            current_user=current_user,
            role_service=role_service,
            db=self.db,
        )

        if not can_manage:
            msg = (
                "You don't have permission to cancel this game. "
                "Only the host, Bot Managers, or guild admins can cancel games."
            )
            raise ValueError(msg)

        # Release image references (decrements count, deletes if zero)
        await release_image(self.db, game.thumbnail_id)
        await release_image(self.db, game.banner_image_id)

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

        # Reload game with relationships for event publishing
        game = await self.get_game(game.id)
        if game is None:
            msg = "Failed to reload cancelled game"
            raise ValueError(msg)

        # Publish game.cancelled event
        await self._publish_game_cancelled(game)

    async def join_game(
        self,
        game_id: str,
        user_discord_id: str,
    ) -> participant_model.GameParticipant:
        """
        Join game as participant.

        Does not commit. Caller must commit transaction.

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
            msg = "Game not found"
            raise ValueError(msg)

        if game.status != game_model.GameStatus.SCHEDULED.value:
            msg = "Game is not open for joining"
            raise ValueError(msg)

        # Get user (create if not exists)
        user = await self.participant_resolver.ensure_user_exists(self.db, user_discord_id)

        # Check if user is already a participant (idempotent operation)
        existing_participant_result = await self.db.execute(
            select(participant_model.GameParticipant).where(
                participant_model.GameParticipant.game_session_id == game_id,
                participant_model.GameParticipant.user_id == user.id,
            )
        )
        existing_participant = existing_participant_result.scalar_one_or_none()
        if existing_participant is not None:
            logger.info(
                "User already in game (idempotent join): game_id=%s, user_id=%s",
                game_id,
                user.id,
            )
            return existing_participant

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
            msg = f"Guild configuration not found for ID: {game.guild_id}"
            raise ValueError(msg)

        channel_result = await self.db.execute(
            select(channel_model.ChannelConfiguration).where(
                channel_model.ChannelConfiguration.id == game.channel_id
            )
        )
        channel_config = channel_result.scalar_one_or_none()
        if channel_config is None:
            msg = f"Channel configuration not found for ID: {game.channel_id}"
            raise ValueError(msg)

        # Use game's max_players or default to DEFAULT_MAX_PLAYERS
        max_players = resolve_max_players(game.max_players)

        if max_players is not None and participant_count >= max_players:
            msg = "Game is full"
            raise ValueError(msg)

        # Add participant
        participant = participant_model.GameParticipant(
            game_session_id=game_id,
            user_id=user.id,
            display_name=None,
            position_type=ParticipantType.SELF_ADDED,
            position=0,
        )
        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)

        # Create delayed join notification schedule
        await schedule_join_notification(
            db=self.db,
            game_id=game_id,
            participant_id=participant.id,
            game_scheduled_at=game.scheduled_at,
            delay_seconds=60,
        )

        # Reload game with relationships for event publishing
        game = await self.get_game(game_id)
        if game is None:
            msg = "Failed to reload game after join"
            raise ValueError(msg)

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

        Does not commit. Caller must commit transaction.

        Args:
            game_id: Game session UUID
            user_discord_id: User's Discord ID

        Raises:
            ValueError: If not a participant or game completed
        """
        logger.info(
            "leave_game service: game_id=%s, user_discord_id=%s",
            game_id,
            user_discord_id,
        )
        game = await self.get_game(game_id)
        if game is None:
            logger.error("Game not found: %s", game_id)
            msg = "Game not found"
            raise ValueError(msg)

        if game.status == game_model.GameStatus.COMPLETED.value:
            logger.error("Cannot leave completed game: %s", game_id)
            msg = "Cannot leave completed game"
            raise ValueError(msg)

        # Get user
        user_result = await self.db.execute(
            select(user_model.User).where(user_model.User.discord_id == user_discord_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            logger.error("User not found: discord_id=%s", user_discord_id)
            msg = "User not found"
            raise ValueError(msg)

        logger.info("Found user: id=%s, discord_id=%s", user.id, user.discord_id)

        # Find participant
        participant_result = await self.db.execute(
            select(participant_model.GameParticipant).where(
                participant_model.GameParticipant.game_session_id == game_id,
                participant_model.GameParticipant.user_id == user.id,
            )
        )
        participant = participant_result.scalar_one_or_none()
        if participant is None:
            logger.info(
                "User not in game (already left or never joined): game_id=%s, user_id=%s",
                game_id,
                user.id,
            )
            return

        logger.info("Found participant: id=%s, deleting...", participant.id)

        # Remove participant
        await self.db.delete(participant)
        logger.info("Participant deleted")

        # Reload game with relationships for event publishing
        game = await self.get_game(game_id)
        if game is None:
            msg = "Failed to reload game after leave"
            raise ValueError(msg)

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
            signup_method=game.signup_method,
        )

        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_CREATED,
            data=event_data.model_dump(mode="json"),
        )

        self.event_publisher.publish_deferred(event=event)

        logger.info("Deferred game.created event for game %s", game.id)

    async def _publish_game_updated(self, game: game_model.GameSession) -> None:
        """Publish game.updated event to RabbitMQ."""
        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_UPDATED,
            data={
                "game_id": game.id,
                "guild_id": game.guild_id,
                "message_id": game.message_id or "",
                "channel_id": game.channel.channel_id,
            },
        )

        routing_key = f"game.updated.{game.guild_id}"
        self.event_publisher.publish_deferred(event=event, routing_key=routing_key)

        logger.info("Deferred game.updated event for game %s", game.id)

    async def _publish_game_cancelled(self, game: game_model.GameSession) -> None:
        """Publish game.cancelled event to RabbitMQ."""
        event = messaging_events.Event(
            event_type=messaging_events.EventType.GAME_CANCELLED,
            data={
                "game_id": game.id,
                "message_id": game.message_id or "",
                "channel_id": game.channel.channel_id,
            },
        )

        self.event_publisher.publish_deferred(event=event)

        logger.info("Deferred game.cancelled event for game %s", game.id)

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
                "channel_id": game.channel.channel_id,
                "game_title": game.title,
                "game_scheduled_at": (game.scheduled_at.isoformat() if game.scheduled_at else None),
            },
        )

        self.event_publisher.publish_deferred(event=event)

        logger.info(
            "Deferred game.player_removed event for participant %s from game %s",
            participant.id,
            game.id,
        )

    async def _notify_promoted_users(
        self,
        game: game_model.GameSession,
        promoted_discord_ids: set[str],
    ) -> None:
        """
        Send promotion notifications to users who cleared the waitlist.

        Args:
            game: Game session after updates applied
            promoted_discord_ids: Set of Discord IDs of promoted users
        """
        if not promoted_discord_ids:
            return

        logger.info(
            "Notifying %s promoted users for game %s: %s",
            len(promoted_discord_ids),
            game.id,
            promoted_discord_ids,
        )

        # Send notification to each promoted user
        for discord_id in promoted_discord_ids:
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

        message = DMFormats.promotion(game.title, scheduled_at_unix)

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

        self.event_publisher.publish_deferred(event=event)

        logger.info(
            "Deferred promotion notification for user %s in game %s",
            discord_id,
            game.id,
        )
