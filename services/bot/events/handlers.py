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


"""Event handlers for consuming RabbitMQ messages in bot service."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.dependencies.discord_client import get_discord_client
from services.bot.formatters.game_message import format_game_announcement
from services.bot.utils.discord_format import get_member_display_info
from shared.cache.client import get_redis_client
from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL
from shared.database import get_db_session
from shared.message_formats import DMFormats
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import (
    Event,
    EventType,
    NotificationDueEvent,
    NotificationSendDMEvent,
)
from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models import user as user_model
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.schemas.events import GameStatusTransitionDueEvent
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import partition_participants
from shared.utils.status_transitions import is_valid_transition

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class EventHandlers:
    """
    Handle incoming events from RabbitMQ for bot service.

    Processes game updates, notifications, and other events that require
    Discord bot actions.
    """

    def __init__(self, bot: discord.Client) -> None:
        """
        Initialize event handlers.

        Args:
            bot: Discord bot client instance
        """
        self.bot = bot
        self.consumer: EventConsumer | None = None
        self._handlers: dict[EventType, Callable] = {
            EventType.GAME_UPDATED: self._handle_game_updated,
            EventType.NOTIFICATION_DUE: self._handle_notification_due,
            EventType.GAME_STATUS_TRANSITION_DUE: self._handle_status_transition_due,
            EventType.NOTIFICATION_SEND_DM: self._handle_send_notification,
            EventType.GAME_CREATED: self._handle_game_created,
            EventType.PLAYER_REMOVED: self._handle_player_removed,
            EventType.GAME_CANCELLED: self._handle_game_cancelled,
        }
        # Track pending refreshes to ensure final state is always applied
        self._pending_refreshes: set[str] = set()
        # Track background tasks to prevent them from being garbage collected
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def start_consuming(self, queue_name: str = "bot_events") -> None:
        """
        Start consuming events from RabbitMQ queue.

        Args:
            queue_name: Name of the queue to consume from
        """
        self.consumer = EventConsumer(queue_name=queue_name)
        await self.consumer.connect()

        # Bind to relevant routing keys
        await self.consumer.bind("game.*")
        await self.consumer.bind("notification.*")

        # Register handlers
        self.consumer.register_handler(
            EventType.GAME_UPDATED, lambda e: self._handle_game_updated(e.data)
        )
        self.consumer.register_handler(
            EventType.NOTIFICATION_DUE,
            lambda e: self._handle_notification_due(e.data),
        )
        self.consumer.register_handler(
            EventType.NOTIFICATION_SEND_DM,
            lambda e: self._handle_send_notification(e.data),
        )
        self.consumer.register_handler(
            EventType.GAME_CREATED, lambda e: self._handle_game_created(e.data)
        )
        self.consumer.register_handler(
            EventType.PLAYER_REMOVED, lambda e: self._handle_player_removed(e.data)
        )
        self.consumer.register_handler(
            EventType.GAME_STATUS_TRANSITION_DUE,
            lambda e: self._handle_status_transition_due(e.data),
        )
        self.consumer.register_handler(
            EventType.GAME_CANCELLED, lambda e: self._handle_game_cancelled(e.data)
        )

        logger.info("Started consuming events from queue: %s", queue_name)

        await self.consumer.start_consuming()

    async def stop_consuming(self) -> None:
        """Stop consuming events and close connection."""
        self._pending_refreshes.clear()

        if self.consumer:
            await self.consumer.close()
            logger.info("Stopped consuming events")

    async def _process_event(self, event: Event) -> None:
        """
        Process incoming event by routing to appropriate handler.

        Args:
            event: Event to process
        """
        handler = self._handlers.get(event.event_type)

        if handler is None:
            logger.warning("No handler registered for event type: %s", event.event_type)
            return

        try:
            await handler(event.data)
            logger.debug("Successfully processed event: %s", event.event_type)
        except Exception as e:
            logger.exception("Error processing event %s: %s", event.event_type, e)
            raise

    async def _validate_game_created_event(
        self, game_id: str | None, channel_id: str | None
    ) -> tuple[str, str] | None:
        """Validate game.created event has required fields."""
        if not game_id or not channel_id:
            logger.error("Missing game_id or channel_id in game.created event")
            return None
        return (game_id, channel_id)

    async def _validate_discord_channel(self, channel_id: str) -> bool:
        """Validate channel exists and is accessible via Discord API."""
        discord_api = get_discord_client()
        channel_data = await discord_api.fetch_channel(channel_id)
        if not channel_data:
            logger.error("Invalid or inaccessible channel: %s", channel_id)
            return False
        return True

    async def _get_bot_channel(self, channel_id: str) -> discord.TextChannel | None:
        """Get Discord channel object from bot, fetching if necessary."""
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_channel(int(channel_id))

        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error("Invalid channel: %s", channel_id)
            return None
        return channel

    async def _handle_game_created(self, data: dict[str, Any]) -> None:
        """
        Handle game.created event by posting announcement to Discord.

        Args:
            data: Event payload with game details
        """
        validated = await self._validate_game_created_event(
            data.get("game_id"), data.get("channel_id")
        )
        if not validated:
            return
        game_id, channel_id = validated

        try:
            if not await self._validate_discord_channel(channel_id):
                return

            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error("Game not found: %s", game_id)
                    return

                content, embed, view = await self._create_game_announcement(game)

                channel = await self._get_bot_channel(channel_id)
                if not channel:
                    return

                # Allow role mentions (including @everyone) in game announcements
                allowed_mentions = discord.AllowedMentions(roles=True, everyone=True)
                message = await channel.send(
                    content=content,
                    embed=embed,
                    view=view,
                    allowed_mentions=allowed_mentions,
                )

                game.message_id = str(message.id)
                await db.commit()

                logger.info(
                    "Posted game announcement: game=%s, channel=%s, message=%s",
                    game_id,
                    channel_id,
                    message.id,
                )

        except Exception as e:
            logger.exception("Failed to post game announcement: %s", e)

    async def _handle_game_updated(self, data: dict[str, Any]) -> None:
        """
        Handle game.updated event by refreshing Discord message.

        Uses Redis-based rate limiting to prevent hitting Discord's rate limits.
        Ensures final state is always applied by scheduling a trailing refresh
        when updates are throttled.

        Args:
            data: Event payload with game_id and updated fields
        """
        game_id = data.get("game_id")

        if not game_id:
            logger.error("Missing game_id in game.updated event")
            return

        try:
            redis = await get_redis_client()
            cache_key = CacheKeys.message_update_throttle(game_id)

            # Check if we can update immediately
            if not await redis.exists(cache_key):
                # No recent update, refresh immediately
                logger.info("Refreshing game %s message (immediate)", game_id)
                await self._refresh_game_message(game_id)
                return

            # Throttled - schedule a trailing refresh to ensure final state is applied
            logger.debug("Game %s updated recently, scheduling trailing refresh", game_id)

            # Skip if refresh already scheduled for this game
            if game_id in self._pending_refreshes:
                logger.debug("Trailing refresh already scheduled for game %s", game_id)
                return

            # Schedule refresh after TTL expires
            self._pending_refreshes.add(game_id)
            task = asyncio.create_task(
                self._delayed_refresh(game_id, CacheTTL.MESSAGE_UPDATE_THROTTLE)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        except Exception as e:
            # Fail open: if Redis unavailable, allow update to proceed
            logger.warning("Redis error during throttle check, allowing update: %s", e)
            await self._refresh_game_message(game_id)

    async def _delayed_refresh(self, game_id: str, delay: float) -> None:
        """
        Refresh message after delay to ensure final state is applied.

        This trailing edge refresh ensures that rapid bursts of updates
        don't prevent the final state from being displayed.

        Args:
            game_id: Game session UUID
            delay: Seconds to wait before refreshing
        """
        try:
            await asyncio.sleep(delay)
            logger.info("Executing trailing refresh for game %s", game_id)
            await self._refresh_game_message(game_id)
        finally:
            self._pending_refreshes.discard(game_id)

    async def _fetch_game_for_refresh(
        self, db: AsyncSession, game_id: str
    ) -> game_model.GameSession | None:
        """
        Fetch game with participants for message refresh.

        Args:
            db: Database session
            game_id: Game session UUID

        Returns:
            Game with participants if found and has message_id, None otherwise
        """
        game = await self._get_game_with_participants(db, game_id)
        if not game or not game.message_id:
            logger.warning("Game or message not found: %s", game_id)
            return None
        return game

    async def _validate_channel_for_refresh(self, channel_id: str) -> discord.TextChannel | None:
        """
        Validate channel exists and is accessible via both API and bot.

        Args:
            channel_id: Discord channel ID

        Returns:
            Discord TextChannel if valid, None otherwise
        """
        discord_api = get_discord_client()
        channel_data = await discord_api.fetch_channel(channel_id)

        if not channel_data:
            logger.error("Invalid channel: %s", channel_id)
            return None

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_channel(int(channel_id))

        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error("Invalid channel: %s", channel_id)
            return None

        return channel

    async def _fetch_message_for_refresh(
        self, channel: discord.TextChannel, message_id: str
    ) -> discord.Message | None:
        """
        Fetch Discord message with error handling.

        Args:
            channel: Discord text channel
            message_id: Message ID to fetch

        Returns:
            Discord Message if found, None otherwise
        """
        try:
            return await channel.fetch_message(int(message_id))
        except discord.NotFound:
            logger.warning("Message not found: %s", message_id)
            return None

    async def _fetch_channel_and_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> tuple[discord.TextChannel, discord.Message] | None:
        """
        Fetch Discord channel and message objects with validation.

        Args:
            channel_id: Discord channel ID
            message_id: Discord message ID

        Returns:
            Tuple of (channel, message) or None if not found/invalid
        """
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except Exception as e:
                logger.error("Invalid or inaccessible channel: %s - %s", channel_id, e)
                return None

        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error("Invalid or inaccessible channel: %s", channel_id)
            return None

        try:
            message = await channel.fetch_message(int(message_id))
            return (channel, message)
        except Exception as e:
            logger.error("Failed to fetch message %s: %s", message_id, e)
            return None

    async def _update_game_message_content(
        self, message: discord.Message, game: game_model.GameSession
    ) -> None:
        """
        Update Discord message with new game content.

        Args:
            message: Discord message to update
            game: Game session with updated data
        """
        content, embed, view = await self._create_game_announcement(game)
        await message.edit(content=content, embed=embed, view=view)
        logger.info("Refreshed game message: game=%s, message=%s", game.id, game.message_id)

    async def _set_message_refresh_throttle(self, game_id: str) -> None:
        """
        Set Redis throttle key to prevent immediate subsequent updates.

        Args:
            game_id: Game session UUID
        """
        redis = await get_redis_client()
        cache_key = CacheKeys.message_update_throttle(game_id)
        await redis.set(cache_key, "1", ttl=CacheTTL.MESSAGE_UPDATE_THROTTLE)

    async def _refresh_game_message(self, game_id: str) -> None:
        """
        Refresh Discord message for a game.

        Args:
            game_id: Game session UUID
        """
        try:
            async with get_db_session() as db:
                game = await self._fetch_game_for_refresh(db, game_id)
                if not game:
                    return

                channel = await self._validate_channel_for_refresh(str(game.channel.channel_id))
                if not channel:
                    return

                message = await self._fetch_message_for_refresh(channel, game.message_id)
                if not message:
                    return

                await self._update_game_message_content(message, game)
                await self._set_message_refresh_throttle(game_id)

        except Exception as e:
            logger.exception("Failed to refresh game message: %s", e)

    async def _handle_notification_due(self, data: dict[str, Any]) -> None:
        """
        Handle game.notification_due event by routing to appropriate handler.

        Routes based on notification_type:
        - 'reminder': Game reminder notifications to all participants
        - 'join_notification': Delayed join notification for specific participant

        Args:
            data: Event payload with game_id, notification_type, participant_id
        """
        logger.info("=== Received game.notification_due event: %s ===", data)

        try:
            notification_event = NotificationDueEvent(**data)
            logger.info(
                "Parsed notification event: game_id=%s, type=%s, participant_id=%s",
                notification_event.game_id,
                notification_event.notification_type,
                notification_event.participant_id,
            )
        except Exception as e:
            logger.exception("Invalid notification event data: %s", e)
            return

        if notification_event.notification_type == "reminder":
            await self._handle_game_reminder(notification_event)
        elif notification_event.notification_type == "join_notification":
            await self._handle_join_notification(notification_event)
        else:
            logger.error(
                "Unknown notification type: %s for game %s",
                notification_event.notification_type,
                notification_event.game_id,
            )

    async def _validate_game_for_reminder(
        self,
        game: game_model.GameSession,
        game_id: str,
    ) -> bool:
        """Validate game state is appropriate for sending reminders."""
        if game.scheduled_at < utc_now():
            logger.info(
                "Game %s already started at %s, skipping stale notification",
                game_id,
                game.scheduled_at,
            )
            return False

        if game.status != "SCHEDULED":
            logger.info("Game %s status is %s, skipping notifications", game_id, game.status)
            return False

        return True

    def _partition_and_filter_participants(
        self,
        game: game_model.GameSession,
    ) -> tuple[list[participant_model.GameParticipant], list[participant_model.GameParticipant]]:
        """Partition participants and filter to real users only."""
        partitioned = partition_participants(game.participants, game.max_players)

        confirmed = [p for p in partitioned.confirmed if p.user]
        overflow = [p for p in partitioned.overflow if p.user]

        logger.info(
            "Game %s: %s confirmed, %s waitlist participants",
            game.id,
            len(confirmed),
            len(overflow),
        )

        return confirmed, overflow

    async def _send_participant_reminders(
        self,
        participants: list[participant_model.GameParticipant],
        game_title: str,
        game_time_unix: int,
        is_waitlist: bool,
    ) -> None:
        """Send reminder DMs to a list of participants."""
        participant_type = "waitlist" if is_waitlist else "confirmed"

        for participant in participants:
            try:
                await self._send_reminder_dm(
                    user_discord_id=participant.user.discord_id,
                    game_title=game_title,
                    game_time_unix=game_time_unix,
                    _reminder_minutes=0,
                    is_waitlist=is_waitlist,
                )
            except Exception as e:
                logger.exception(
                    "Failed to send reminder to %s participant %s: %s",
                    participant_type,
                    participant.user_id,
                    e,
                )

    async def _send_host_reminder(
        self,
        host: user_model.User | None,
        game_title: str,
        game_time_unix: int,
    ) -> None:
        """Send reminder DM to game host if present."""
        if not host or not host.discord_id:
            return

        try:
            await self._send_reminder_dm(
                user_discord_id=host.discord_id,
                game_title=game_title,
                game_time_unix=game_time_unix,
                _reminder_minutes=0,
                is_waitlist=False,
                is_host=True,
            )
            logger.info("Sent reminder to host %s", host.discord_id)
        except Exception as e:
            logger.exception(
                "Failed to send reminder to host %s: %s",
                host.discord_id,
                e,
            )

    async def _handle_game_reminder(self, reminder_event: NotificationDueEvent) -> None:
        """
        Handle game reminder notifications by sending DMs to all eligible participants.

        Processes participants according to game rules:
        - Filters to only real participants (user_id IS NOT NULL)
        - Sorts by position_type, position, then joined_at
        - Determines active vs waitlist based on max_players
        - Sends DM to each eligible participant

        Args:
            reminder_event: Notification event with game_id
        """

        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, str(reminder_event.game_id))

                if not game:
                    logger.error("Game not found: %s", reminder_event.game_id)
                    return

                if not await self._validate_game_for_reminder(game, str(reminder_event.game_id)):
                    return

                confirmed, overflow = self._partition_and_filter_participants(game)

                game_time_unix = int(game.scheduled_at.timestamp())

                await self._send_participant_reminders(
                    confirmed,
                    game.title,
                    game_time_unix,
                    is_waitlist=False,
                )
                await self._send_participant_reminders(
                    overflow,
                    game.title,
                    game_time_unix,
                    is_waitlist=True,
                )
                await self._send_host_reminder(
                    game.host,
                    game.title,
                    game_time_unix,
                )

                logger.info(
                    "✓ Completed reminder notifications for game %s: "
                    "%s confirmed, %s waitlist, host notified",
                    reminder_event.game_id,
                    len(confirmed),
                    len(overflow),
                )

        except Exception as e:
            logger.exception(
                "Failed to handle game reminder due event: %s",
                e,
            )

    async def _fetch_join_notification_data(
        self,
        db: AsyncSession,
        event: NotificationDueEvent,
    ) -> tuple[GameSession | None, GameParticipant | None]:
        """
        Fetch game and participant for join notification.

        Args:
            db: Database session
            event: Notification event with game_id and participant_id

        Returns:
            Tuple of (game, participant) or (None, None) if not found
        """
        game = await self._get_game_with_participants(db, str(event.game_id))

        if not game:
            logger.error("Game not found: %s", event.game_id)
            return None, None

        participant_result = await db.execute(
            select(GameParticipant).where(GameParticipant.id == event.participant_id)
        )
        participant = participant_result.scalar_one_or_none()

        if not participant or not participant.user:
            logger.info(
                "Participant %s no longer active for game %s",
                event.participant_id,
                event.game_id,
            )
            return None, None

        return game, participant

    def _is_participant_confirmed(
        self,
        participant: GameParticipant,
        game: GameSession,
    ) -> bool:
        """
        Check if participant is confirmed (not on waitlist).

        Args:
            participant: The participant to check
            game: The game session

        Returns:
            True if participant is confirmed, False if waitlisted
        """
        partitioned = partition_participants(game.participants, game.max_players)
        is_confirmed = participant in partitioned.confirmed

        if not is_confirmed:
            logger.info(
                "Participant %s is waitlisted, skipping join notification for game %s",
                participant.id,
                game.id,
            )

        return is_confirmed

    def _format_join_notification_message(
        self,
        game: GameSession,
    ) -> str:
        """
        Format join notification message with conditional signup instructions.

        Args:
            game: The game session

        Returns:
            Formatted message string
        """
        if game.signup_instructions:
            return DMFormats.join_with_instructions(
                game.title,
                game.signup_instructions,
                int(game.scheduled_at.timestamp()),
            )
        return DMFormats.join_simple(game.title)

    async def _send_join_notification_dm(
        self,
        participant: GameParticipant,
        message: str,
        game_id: str,
    ) -> None:
        """
        Send join notification DM and log result.

        Args:
            participant: The participant to notify
            message: The formatted message to send
            game_id: The game ID for logging
        """
        success = await self._send_dm(participant.user.discord_id, message)

        if success:
            logger.info(
                "✓ Sent join notification to %s for game %s",
                participant.user.discord_id,
                game_id,
            )
        else:
            logger.warning(
                "Failed to send join notification to %s for game %s",
                participant.user.discord_id,
                game_id,
            )

    async def _handle_join_notification(self, event: NotificationDueEvent) -> None:
        """
        Handle join notification by sending DM with conditional signup instructions.

        Checks if participant still exists and is confirmed (not waitlisted).
        Includes signup instructions in message if present in game.

        Args:
            event: Notification event with game_id and participant_id
        """
        try:
            async with get_db_session() as db:
                game, participant = await self._fetch_join_notification_data(db, event)

                if not game or not participant:
                    return

                if not self._is_participant_confirmed(participant, game):
                    return

                message = self._format_join_notification_message(game)
                await self._send_join_notification_dm(participant, message, str(event.game_id))

        except Exception as e:
            logger.exception(
                "Failed to handle join notification for game %s, participant %s: %s",
                event.game_id,
                event.participant_id,
                e,
            )

    async def _send_dm(self, user_discord_id: str, message: str) -> bool:
        """
        Send DM to a Discord user with consistent error handling.

        Args:
            user_discord_id: Discord user ID (snowflake string)
            message: Message content to send

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            discord_api = get_discord_client()
            user_data = await discord_api.fetch_user(user_discord_id)

            if not user_data:
                logger.error("User not found in Discord: %s", user_discord_id)
                return False

            user = await self.bot.fetch_user(int(user_discord_id))
            if not user:
                logger.error("Could not get user object: %s", user_discord_id)
                return False

            await user.send(message)
            logger.debug("✓ Sent DM to %s", user_discord_id)
            return True

        except discord.Forbidden:
            logger.warning(
                "Cannot send DM to user %s: DMs disabled or bot blocked",
                user_discord_id,
            )
            return False
        except discord.HTTPException as e:
            logger.exception(
                "Discord HTTP error sending DM to %s: %s",
                user_discord_id,
                e,
            )
            return False
        except Exception as e:
            logger.exception(
                "Failed to send DM to %s: %s",
                user_discord_id,
                e,
            )
            return False

    async def _send_reminder_dm(
        self,
        user_discord_id: str,
        game_title: str,
        game_time_unix: int,
        _reminder_minutes: int,
        is_waitlist: bool,
        is_host: bool = False,
    ) -> None:
        """
        Send reminder DM to a single participant or host.

        Args:
            user_discord_id: Discord user ID (snowflake string)
            game_title: Title of the game
            game_time_unix: Unix timestamp of game start time
            reminder_minutes: Minutes before game
            is_waitlist: Whether participant is on waitlist
            is_host: Whether recipient is the game host
        """
        if is_host:
            message = DMFormats.reminder_host(game_title, game_time_unix)
        else:
            message = DMFormats.reminder_participant(game_title, game_time_unix, is_waitlist)
        await self._send_dm(user_discord_id, message)

    async def _handle_send_notification(self, data: dict[str, Any]) -> None:
        """
        Handle notification.send_dm event by sending DM to user.

        Args:
            data: Event payload with notification details
        """
        logger.info("=== Received notification.send_dm event: %s ===", data)

        try:
            notification = NotificationSendDMEvent(**data)
            logger.info(
                "Parsed notification event: user_id=%s, game_id=%s, type=%s",
                notification.user_id,
                notification.game_id,
                notification.notification_type,
            )
        except Exception as e:
            logger.exception("Invalid notification event data: %s", e)
            return

        success = await self._send_dm(notification.user_id, notification.message)

        if success:
            logger.info(
                "✓ Successfully sent notification DM: user=%s, game=%s, type=%s",
                notification.user_id,
                notification.game_id,
                notification.notification_type,
            )

    async def _update_message_for_player_removal(
        self, game_id: str, message_id: str, channel_id: str
    ) -> None:
        """
        Update Discord message to reflect player removal.

        Args:
            game_id: Game ID
            message_id: Discord message ID
            channel_id: Discord channel ID
        """
        async with get_db_session() as db:
            game = await self._get_game_with_participants(db, game_id)
            if not game:
                logger.error("Game not found: %s", game_id)
                return

            result = await self._fetch_channel_and_message(channel_id, message_id)
            if not result:
                return

            _channel, message = result
            try:
                content, embed, view = await self._create_game_announcement(game)
                await message.edit(content=content, embed=embed, view=view)
                logger.info("Updated game message after participant removal: %s", message_id)

            except discord.NotFound:
                logger.warning("Game message not found: %s", message_id)
            except Exception as e:
                logger.exception("Failed to update game message: %s", e)

    def _build_removal_dm_message(self, game_title: str, game_scheduled_at: str | None) -> str:
        """
        Build DM message for removed player.

        Args:
            game_title: Title of the game
            game_scheduled_at: ISO format scheduled time, if any

        Returns:
            Formatted DM message
        """
        dm_message = DMFormats.removal(game_title)
        if game_scheduled_at:
            try:
                scheduled_dt = datetime.fromisoformat(game_scheduled_at)
                dm_message += f" scheduled for <t:{int(scheduled_dt.timestamp())}:F>"
            except (ValueError, TypeError):
                pass
        return dm_message

    async def _notify_removed_player(
        self, discord_id: str | None, game_title: str, game_scheduled_at: str | None
    ) -> None:
        """
        Send DM notification to removed player.

        Args:
            discord_id: Discord user ID
            game_title: Title of the game
            game_scheduled_at: ISO format scheduled time, if any
        """
        if not discord_id:
            logger.warning("No discord_id provided for removal DM")
            return

        logger.info(
            "Preparing to send removal DM to user %s for game %s",
            discord_id,
            game_title,
        )
        dm_message = self._build_removal_dm_message(game_title, game_scheduled_at)

        logger.info("Sending DM to %s: %s", discord_id, dm_message)
        success = await self._send_dm(discord_id, dm_message)
        if success:
            logger.info("✓ Successfully sent removal DM to user %s", discord_id)
        else:
            logger.warning("Failed to send removal DM to user %s", discord_id)

    async def _handle_player_removed(self, data: dict[str, Any]) -> None:
        """
        Handle game.player_removed event by updating Discord message and notifying user.

        Args:
            data: Event payload with player removal details
        """
        game_id = data.get("game_id")
        discord_id = data.get("discord_id")
        message_id = data.get("message_id")
        channel_id = data.get("channel_id")
        game_title = data.get("game_title")
        game_scheduled_at = data.get("game_scheduled_at")

        if not game_id or not message_id or not channel_id:
            logger.error("Missing required fields in participant.removed event")
            return

        try:
            await self._update_message_for_player_removal(game_id, message_id, channel_id)
            await self._notify_removed_player(discord_id, game_title, game_scheduled_at)

        except Exception as e:
            logger.exception("Failed to handle participant removal: %s", e)

    def _validate_cancellation_event_data(
        self, data: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """
        Validate required fields for game cancellation event.

        Args:
            data: Event payload containing game_id, message_id, and channel_id

        Returns:
            Tuple of (game_id, message_id, channel_id) if valid, None otherwise
        """
        game_id = data.get("game_id")
        message_id = data.get("message_id")
        channel_id = data.get("channel_id")

        if not game_id or not message_id or not channel_id:
            logger.error("Missing required fields in game.cancelled event: %s", data)
            return None

        return (game_id, message_id, channel_id)

    async def _handle_game_cancelled(self, data: dict[str, Any]) -> None:
        """
        Handle game.cancelled event by updating Discord message to show cancellation.

        Args:
            data: Event payload with game_id, message_id, and channel_id
        """
        event_data = self._validate_cancellation_event_data(data)
        if not event_data:
            return

        game_id, message_id, channel_id = event_data

        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error("Game not found: %s", game_id)
                    return

                result = await self._fetch_channel_and_message(channel_id, message_id)
                if not result:
                    return

                _channel, message = result
                try:
                    content, embed, view = await self._create_game_announcement(game)
                    await message.edit(content=content, embed=embed, view=view)
                    logger.info("Updated cancelled game message: %s", message_id)

                except discord.NotFound:
                    logger.warning("Game message not found: %s", message_id)
                except Exception as e:
                    logger.exception("Failed to update cancelled game message: %s", e)

        except Exception as e:
            logger.exception("Failed to handle game.cancelled event: %s", e)

    async def _handle_status_transition_due(self, data: dict[str, Any]) -> None:
        """
        Handle game.status_transition_due event by updating game status.

        Transitions game status to target status if the transition is valid
        according to game lifecycle rules.

        Args:
            data: Event payload with game_id, target_status, and transition_time
        """
        logger.info("=== Received game.status_transition_due event: %s ===", data)

        try:
            transition_event = GameStatusTransitionDueEvent(**data)
            logger.info(
                "Parsed status transition event: game_id=%s, target_status=%s",
                transition_event.game_id,
                transition_event.target_status,
            )
        except Exception as e:
            logger.exception("Invalid status transition event data: %s", e)
            return

        game_id = str(transition_event.game_id)

        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error("Game %s not found for status transition", game_id)
                    return

                # Validate transition is valid based on current status
                if not is_valid_transition(game.status, transition_event.target_status):
                    logger.warning(
                        "Invalid status transition for game %s: %s → %s. Skipping.",
                        game_id,
                        game.status,
                        transition_event.target_status,
                    )
                    return

                # Check if already at target status (idempotency)
                if game.status == transition_event.target_status:
                    logger.info(
                        "Game %s already at status %s, skipping transition",
                        game_id,
                        game.status,
                    )
                    return

                current_status = game.status
                game.status = transition_event.target_status
                # updated_at handled automatically by SQLAlchemy onupdate
                await db.commit()

                logger.info(
                    "✓ Transitioned game %s from %s to %s",
                    game_id,
                    current_status,
                    transition_event.target_status,
                )

            # Refresh Discord message to reflect new status
            await self._refresh_game_message(game_id)

        except Exception as e:
            logger.exception(
                "Failed to handle status transition for game %s: %s",
                game_id,
                e,
            )

    def _format_participants_for_display(self, game: GameSession) -> tuple[list[str], list[str]]:
        """
        Format game participants for Discord message display.

        Sorts all participants (including placeholders) and splits them into
        confirmed and overflow lists based on max_players.

        Args:
            game: Game session with participants loaded

        Returns:
            Tuple of (confirmed_ids, overflow_ids) where IDs are
            Discord user IDs (formatted as mentions) or placeholder names
        """
        partitioned = partition_participants(game.participants, game.max_players)

        confirmed_ids = [
            p.user.discord_id if p.user else p.display_name for p in partitioned.confirmed
        ]
        overflow_ids = [
            p.user.discord_id if p.user else p.display_name for p in partitioned.overflow
        ]

        return confirmed_ids, overflow_ids

    async def _create_game_announcement(
        self, game: GameSession
    ) -> tuple[str | None, discord.Embed, discord.ui.View]:
        """
        Create Discord announcement content for a game.

        Args:
            game: Game session with participants loaded

        Returns:
            Tuple of (content, embed, view) for Discord message
        """
        confirmed_ids, overflow_ids = self._format_participants_for_display(game)

        # Get host display name and avatar URL from Discord
        host_display_name = None
        host_avatar_url = None
        if game.host and game.guild:
            host_display_name, host_avatar_url = await get_member_display_info(
                self.bot, game.guild.guild_id, game.host.discord_id
            )

        return format_game_announcement(
            game_id=str(game.id),
            game_title=game.title,
            description=game.description,
            scheduled_at=game.scheduled_at,
            host_id=game.host.discord_id,
            participant_ids=confirmed_ids,
            overflow_ids=overflow_ids,
            current_count=len(confirmed_ids),
            max_players=resolve_max_players(game.max_players),
            status=game.status,
            signup_method=game.signup_method,
            signup_instructions=game.signup_instructions,
            expected_duration_minutes=game.expected_duration_minutes,
            notify_role_ids=game.notify_role_ids or [],
            where=game.where,
            host_display_name=host_display_name,
            host_avatar_url=host_avatar_url,
            has_thumbnail=game.thumbnail_data is not None,
            has_image=game.image_data is not None,
            guild_id=game.guild.guild_id if game.guild else None,
        )

    async def _get_game_with_participants(
        self, db: AsyncSession, game_id: str
    ) -> GameSession | None:
        """
        Fetch game session with participants from database.

        Args:
            db: Database session
            game_id: UUID of the game session

        Returns:
            GameSession with participants loaded, or None if not found
        """
        from uuid import UUID  # noqa: PLC0415 - avoid top-level UUID conflict

        from sqlalchemy.orm import selectinload  # noqa: PLC0415

        result = await db.execute(
            select(GameSession)
            .options(selectinload(GameSession.participants).selectinload(GameParticipant.user))
            .options(selectinload(GameSession.host))
            .options(selectinload(GameSession.channel))
            .options(selectinload(GameSession.guild))
            .where(GameSession.id == str(UUID(game_id)))
        )
        return result.scalar_one_or_none()
