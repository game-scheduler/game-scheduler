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


"""Event handlers for consuming RabbitMQ messages in bot service."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

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
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import (
    Event,
    EventType,
    NotificationDueEvent,
    NotificationSendDMEvent,
)
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.schemas.events import GameStatusTransitionDueEvent
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import partition_participants
from shared.utils.status_transitions import is_valid_transition

logger = logging.getLogger(__name__)


class EventHandlers:
    """
    Handle incoming events from RabbitMQ for bot service.

    Processes game updates, notifications, and other events that require
    Discord bot actions.
    """

    def __init__(self, bot: discord.Client):
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

        logger.info(f"Started consuming events from queue: {queue_name}")

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
            logger.warning(f"No handler registered for event type: {event.event_type}")
            return

        try:
            await handler(event.data)
            logger.debug(f"Successfully processed event: {event.event_type}")
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}", exc_info=True)
            raise

    async def _handle_game_created(self, data: dict[str, Any]) -> None:
        """
        Handle game.created event by posting announcement to Discord.

        Args:
            data: Event payload with game details
        """
        game_id = data.get("game_id")
        channel_id = data.get("channel_id")

        if not game_id or not channel_id:
            logger.error("Missing game_id or channel_id in game.created event")
            return

        try:
            discord_api = get_discord_client()
            channel_data = await discord_api.fetch_channel(channel_id)

            if not channel_data:
                logger.error(f"Invalid or inaccessible channel: {channel_id}")
                return

            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error(f"Game not found: {game_id}")
                    return

                content, embed, view = await self._create_game_announcement(game)

                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))

                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid channel: {channel_id}")
                    return

                message = await channel.send(content=content, embed=embed, view=view)

                game.message_id = str(message.id)
                await db.commit()

                logger.info(
                    f"Posted game announcement: game={game_id}, "
                    f"channel={channel_id}, message={message.id}"
                )

        except Exception as e:
            logger.error(f"Failed to post game announcement: {e}", exc_info=True)

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
                logger.info(f"Refreshing game {game_id} message (immediate)")
                await self._refresh_game_message(game_id)
                return

            # Throttled - schedule a trailing refresh to ensure final state is applied
            logger.debug(f"Game {game_id} updated recently, scheduling trailing refresh")

            # Skip if refresh already scheduled for this game
            if game_id in self._pending_refreshes:
                logger.debug(f"Trailing refresh already scheduled for game {game_id}")
                return

            # Schedule refresh after TTL expires
            self._pending_refreshes.add(game_id)
            asyncio.create_task(self._delayed_refresh(game_id, CacheTTL.MESSAGE_UPDATE_THROTTLE))

        except Exception as e:
            # Fail open: if Redis unavailable, allow update to proceed
            logger.warning(f"Redis error during throttle check, allowing update: {e}")
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
            logger.info(f"Executing trailing refresh for game {game_id}")
            await self._refresh_game_message(game_id)
        finally:
            self._pending_refreshes.discard(game_id)

    async def _refresh_game_message(self, game_id: str) -> None:
        """
        Refresh Discord message for a game.

        Args:
            game_id: Game session UUID
        """
        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game or not game.message_id:
                    logger.warning(f"Game or message not found: {game_id}")
                    return

                discord_api = get_discord_client()
                channel_data = await discord_api.fetch_channel(str(game.channel.channel_id))

                if not channel_data:
                    logger.error(f"Invalid channel: {game.channel.channel_id}")
                    return

                channel = self.bot.get_channel(int(game.channel.channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(game.channel.channel_id))

                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid channel: {game.channel.channel_id}")
                    return

                try:
                    message = await channel.fetch_message(int(game.message_id))
                except discord.NotFound:
                    logger.warning(f"Message not found: {game.message_id}")
                    return

                content, embed, view = await self._create_game_announcement(game)

                await message.edit(content=content, embed=embed, view=view)

                logger.info(f"Refreshed game message: game={game_id}, message={game.message_id}")

                # Set throttle key to prevent immediate subsequent updates
                redis = await get_redis_client()
                cache_key = CacheKeys.message_update_throttle(game_id)
                await redis.set(cache_key, "1", ttl=CacheTTL.MESSAGE_UPDATE_THROTTLE)

        except Exception as e:
            logger.error(f"Failed to refresh game message: {e}", exc_info=True)

    async def _handle_notification_due(self, data: dict[str, Any]) -> None:
        """
        Handle game.notification_due event by routing to appropriate handler.

        Routes based on notification_type:
        - 'reminder': Game reminder notifications to all participants
        - 'join_notification': Delayed join notification for specific participant

        Args:
            data: Event payload with game_id, notification_type, participant_id
        """
        logger.info(f"=== Received game.notification_due event: {data} ===")

        try:
            notification_event = NotificationDueEvent(**data)
            logger.info(
                f"Parsed notification event: game_id={notification_event.game_id}, "
                f"type={notification_event.notification_type}, "
                f"participant_id={notification_event.participant_id}"
            )
        except Exception as e:
            logger.error(f"Invalid notification event data: {e}", exc_info=True)
            return

        if notification_event.notification_type == "reminder":
            await self._handle_game_reminder(notification_event)
        elif notification_event.notification_type == "join_notification":
            await self._handle_join_notification(notification_event)
        else:
            logger.error(
                f"Unknown notification type: {notification_event.notification_type} "
                f"for game {notification_event.game_id}"
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
                    logger.error(f"Game not found: {reminder_event.game_id}")
                    return

                if game.scheduled_at < utc_now():
                    logger.info(
                        f"Game {reminder_event.game_id} already started at "
                        f"{game.scheduled_at}, skipping stale notification"
                    )
                    return

                if game.status != "SCHEDULED":
                    logger.info(
                        f"Game {reminder_event.game_id} status is {game.status}, "
                        f"skipping notifications"
                    )
                    return

                # Partition participants into confirmed and overflow
                partitioned = partition_participants(game.participants, game.max_players)

                # Filter to only real users (exclude placeholders)
                confirmed_participants = [p for p in partitioned.confirmed if p.user]
                overflow_participants = [p for p in partitioned.overflow if p.user]

                logger.info(
                    f"Game {reminder_event.game_id}: {len(confirmed_participants)} confirmed, "
                    f"{len(overflow_participants)} waitlist participants"
                )

                # Calculate game time for message
                game_time_unix = int(game.scheduled_at.timestamp())

                # Send notifications to confirmed participants
                for participant in confirmed_participants:
                    try:
                        await self._send_reminder_dm(
                            user_discord_id=participant.user.discord_id,
                            game_title=game.title,
                            game_time_unix=game_time_unix,
                            reminder_minutes=0,  # Not used in message formatting
                            is_waitlist=False,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to send reminder to participant {participant.user_id}: {e}",
                            exc_info=True,
                        )

                # Send notifications to waitlist participants
                for participant in overflow_participants:
                    try:
                        await self._send_reminder_dm(
                            user_discord_id=participant.user.discord_id,
                            game_title=game.title,
                            game_time_unix=game_time_unix,
                            reminder_minutes=0,  # Not used in message formatting
                            is_waitlist=True,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to send reminder to waitlist participant "
                            f"{participant.user_id}: {e}",
                            exc_info=True,
                        )

                # Send notification to game host
                if game.host and game.host.discord_id:
                    try:
                        await self._send_reminder_dm(
                            user_discord_id=game.host.discord_id,
                            game_title=game.title,
                            game_time_unix=game_time_unix,
                            reminder_minutes=0,  # Not used in message formatting
                            is_waitlist=False,
                            is_host=True,
                        )
                        logger.info(f"Sent reminder to host {game.host.discord_id}")
                    except Exception as e:
                        logger.error(
                            f"Failed to send reminder to host {game.host.discord_id}: {e}",
                            exc_info=True,
                        )

                logger.info(
                    f"✓ Completed reminder notifications for game {reminder_event.game_id}: "
                    f"{len(confirmed_participants)} confirmed, "
                    f"{len(overflow_participants)} waitlist, host notified"
                )

        except Exception as e:
            logger.error(
                f"Failed to handle game reminder due event: {e}",
                exc_info=True,
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
                # Query game with relationships
                game = await self._get_game_with_participants(db, str(event.game_id))

                if not game:
                    logger.error(f"Game not found: {event.game_id}")
                    return

                # Query specific participant
                participant_result = await db.execute(
                    select(GameParticipant).where(GameParticipant.id == event.participant_id)
                )
                participant = participant_result.scalar_one_or_none()

                # Verify participant still exists and has user
                if not participant or not participant.user:
                    logger.info(
                        f"Participant {event.participant_id} no longer active for game "
                        f"{event.game_id}"
                    )
                    return

                # Check if participant is confirmed (not on waitlist)
                partitioned = partition_participants(game.participants, game.max_players)

                if participant not in partitioned.confirmed:
                    logger.info(
                        f"Participant {event.participant_id} is waitlisted, skipping join "
                        f"notification for game {event.game_id}"
                    )
                    return

                # Format message based on signup_instructions presence
                if game.signup_instructions:
                    message = (
                        f"✅ **You've joined {game.title}**\n\n"
                        f"📋 **Signup Instructions**\n"
                        f"{game.signup_instructions}\n\n"
                        f"Game starts <t:{int(game.scheduled_at.timestamp())}:R>"
                    )
                else:
                    message = f"✅ You've joined **{game.title}**!"

                # Send DM
                success = await self._send_dm(participant.user.discord_id, message)

                if success:
                    logger.info(
                        f"✓ Sent join notification to {participant.user.discord_id} "
                        f"for game {event.game_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to send join notification to {participant.user.discord_id} "
                        f"for game {event.game_id}"
                    )

        except Exception as e:
            logger.error(
                f"Failed to handle join notification for game {event.game_id}, "
                f"participant {event.participant_id}: {e}",
                exc_info=True,
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
                logger.error(f"User not found in Discord: {user_discord_id}")
                return False

            user = await self.bot.fetch_user(int(user_discord_id))
            if not user:
                logger.error(f"Could not get user object: {user_discord_id}")
                return False

            await user.send(message)
            logger.debug(f"✓ Sent DM to {user_discord_id}")
            return True

        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user_discord_id}: DMs disabled or bot blocked")
            return False
        except discord.HTTPException as e:
            logger.error(
                f"Discord HTTP error sending DM to {user_discord_id}: {e}",
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to send DM to {user_discord_id}: {e}",
                exc_info=True,
            )
            return False

    async def _send_reminder_dm(
        self,
        user_discord_id: str,
        game_title: str,
        game_time_unix: int,
        reminder_minutes: int,
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
            message = f"🎮 **[Host]** Your game '{game_title}' starts <t:{game_time_unix}:R>"
        else:
            waitlist_prefix = "🎫 **[Waitlist]** " if is_waitlist else ""
            message = f"{waitlist_prefix}Your game '{game_title}' starts <t:{game_time_unix}:R>"
        await self._send_dm(user_discord_id, message)

    async def _handle_send_notification(self, data: dict[str, Any]) -> None:
        """
        Handle notification.send_dm event by sending DM to user.

        Args:
            data: Event payload with notification details
        """
        logger.info(f"=== Received notification.send_dm event: {data} ===")

        try:
            notification = NotificationSendDMEvent(**data)
            logger.info(
                f"Parsed notification event: user_id={notification.user_id}, "
                f"game_id={notification.game_id}, type={notification.notification_type}"
            )
        except Exception as e:
            logger.error(f"Invalid notification event data: {e}", exc_info=True)
            return

        success = await self._send_dm(notification.user_id, notification.message)

        if success:
            logger.info(
                f"✓ Successfully sent notification DM: user={notification.user_id}, "
                f"game={notification.game_id}, type={notification.notification_type}"
            )

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
            # Update Discord message to reflect removal
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error(f"Game not found: {game_id}")
                    return

                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))

                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid or inaccessible channel: {channel_id}")
                    return

                try:
                    message = await channel.fetch_message(int(message_id))

                    content, embed, view = await self._create_game_announcement(game)

                    await message.edit(content=content, embed=embed, view=view)
                    logger.info(f"Updated game message after participant removal: {message_id}")

                except discord.NotFound:
                    logger.warning(f"Game message not found: {message_id}")
                except Exception as e:
                    logger.error(f"Failed to update game message: {e}", exc_info=True)

            # Send DM to removed user
            if discord_id:
                logger.info(
                    f"Preparing to send removal DM to user {discord_id} for game {game_title}"
                )
                dm_message = f"❌ You were removed from **{game_title}**"
                if game_scheduled_at:
                    from datetime import datetime

                    try:
                        scheduled_dt = datetime.fromisoformat(game_scheduled_at)
                        dm_message += f" scheduled for <t:{int(scheduled_dt.timestamp())}:F>"
                    except (ValueError, TypeError):
                        pass

                logger.info(f"Sending DM to {discord_id}: {dm_message}")
                success = await self._send_dm(discord_id, dm_message)
                if success:
                    logger.info(f"✓ Successfully sent removal DM to user {discord_id}")
                else:
                    logger.warning(f"Failed to send removal DM to user {discord_id}")
            else:
                logger.warning("No discord_id provided for removal DM")

        except Exception as e:
            logger.error(f"Failed to handle participant removal: {e}", exc_info=True)

    async def _handle_game_cancelled(self, data: dict[str, Any]) -> None:
        """
        Handle game.cancelled event by updating Discord message to show cancellation.

        Args:
            data: Event payload with game_id, message_id, and channel_id
        """
        game_id = data.get("game_id")
        message_id = data.get("message_id")
        channel_id = data.get("channel_id")

        if not game_id or not message_id or not channel_id:
            logger.error(f"Missing required fields in game.cancelled event: {data}")
            return

        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error(f"Game not found: {game_id}")
                    return

                discord_api = get_discord_client()
                channel_data = await discord_api.fetch_channel(channel_id)
                if not channel_data:
                    logger.error(f"Invalid or inaccessible channel: {channel_id}")
                    return

                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))

                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid or inaccessible channel: {channel_id}")
                    return

                try:
                    message = await channel.fetch_message(int(message_id))

                    content, embed, view = await self._create_game_announcement(game)

                    await message.edit(content=content, embed=embed, view=view)
                    logger.info(f"Updated cancelled game message: {message_id}")

                except discord.NotFound:
                    logger.warning(f"Game message not found: {message_id}")
                except Exception as e:
                    logger.error(f"Failed to update cancelled game message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to handle game.cancelled event: {e}", exc_info=True)

    async def _handle_status_transition_due(self, data: dict[str, Any]) -> None:
        """
        Handle game.status_transition_due event by updating game status.

        Transitions game status to target status if the transition is valid
        according to game lifecycle rules.

        Args:
            data: Event payload with game_id, target_status, and transition_time
        """
        logger.info(f"=== Received game.status_transition_due event: {data} ===")

        try:
            transition_event = GameStatusTransitionDueEvent(**data)
            logger.info(
                f"Parsed status transition event: game_id={transition_event.game_id}, "
                f"target_status={transition_event.target_status}"
            )
        except Exception as e:
            logger.error(f"Invalid status transition event data: {e}", exc_info=True)
            return

        game_id = str(transition_event.game_id)

        try:
            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error(f"Game {game_id} not found for status transition")
                    return

                # Validate transition is valid based on current status
                if not is_valid_transition(game.status, transition_event.target_status):
                    logger.warning(
                        f"Invalid status transition for game {game_id}: "
                        f"{game.status} → {transition_event.target_status}. Skipping."
                    )
                    return

                # Check if already at target status (idempotency)
                if game.status == transition_event.target_status:
                    logger.info(
                        f"Game {game_id} already at status {game.status}, skipping transition"
                    )
                    return

                current_status = game.status
                game.status = transition_event.target_status
                # updated_at handled automatically by SQLAlchemy onupdate
                await db.commit()

                logger.info(
                    f"✓ Transitioned game {game_id} from {current_status} to "
                    f"{transition_event.target_status}"
                )

            # Refresh Discord message to reflect new status
            await self._refresh_game_message(game_id)

        except Exception as e:
            logger.error(
                f"Failed to handle status transition for game {game_id}: {e}",
                exc_info=True,
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
            signup_instructions=game.signup_instructions,
            expected_duration_minutes=game.expected_duration_minutes,
            notify_role_ids=game.notify_role_ids or [],
            where=game.where,
            host_display_name=host_display_name,
            host_avatar_url=host_avatar_url,
            has_thumbnail=game.thumbnail_data is not None,
            has_image=game.image_data is not None,
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
        from uuid import UUID

        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(GameSession)
            .options(selectinload(GameSession.participants).selectinload(GameParticipant.user))
            .options(selectinload(GameSession.host))
            .options(selectinload(GameSession.channel))
            .options(selectinload(GameSession.guild))
            .where(GameSession.id == str(UUID(game_id)))
        )
        game = result.scalar_one_or_none()

        return game
