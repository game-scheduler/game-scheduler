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

from services.bot.formatters.game_message import format_game_announcement
from shared.cache.client import get_redis_client
from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL
from shared.database import get_db_session
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType, NotificationSendDMEvent
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.utils import participant_sorting

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
            EventType.NOTIFICATION_SEND_DM: self._handle_send_notification,
            EventType.GAME_CREATED: self._handle_game_created,
            EventType.PLAYER_REMOVED: self._handle_player_removed,
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
            EventType.NOTIFICATION_SEND_DM,
            lambda e: self._handle_send_notification(e.data),
        )
        self.consumer.register_handler(
            EventType.GAME_CREATED, lambda e: self._handle_game_created(e.data)
        )
        self.consumer.register_handler(
            EventType.PLAYER_REMOVED, lambda e: self._handle_player_removed(e.data)
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
            channel = await self.bot.fetch_channel(int(channel_id))

            if not channel or not isinstance(channel, discord.TextChannel):
                logger.error(f"Invalid or inaccessible channel: {channel_id}")
                return

            async with get_db_session() as db:
                game = await self._get_game_with_participants(db, game_id)
                if not game:
                    logger.error(f"Game not found: {game_id}")
                    return

                all_participants = [p for p in game.participants if p.user_id and p.user]
                sorted_participants = participant_sorting.sort_participants(all_participants)

                max_players = game.max_players or 10
                confirmed_participants = sorted_participants[:max_players]
                overflow_participants = sorted_participants[max_players:]

                # Extract Discord IDs for display
                confirmed_ids = [p.user.discord_id for p in confirmed_participants]
                overflow_ids = [p.user.discord_id for p in overflow_participants]

                content, embed, view = format_game_announcement(
                    game_id=str(game.id),
                    game_title=game.title,
                    description=game.description,
                    scheduled_at=game.scheduled_at,
                    host_id=game.host.discord_id,
                    participant_ids=confirmed_ids,
                    overflow_ids=overflow_ids,
                    current_count=len(confirmed_participants),
                    max_players=max_players,
                    status=game.status,
                    signup_instructions=game.signup_instructions,
                    expected_duration_minutes=game.expected_duration_minutes,
                    notify_role_ids=game.notify_role_ids,
                )

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

                channel = await self.bot.fetch_channel(int(game.channel.channel_id))

                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid channel: {game.channel.channel_id}")
                    return

                try:
                    message = await channel.fetch_message(int(game.message_id))
                except discord.NotFound:
                    logger.warning(f"Message not found: {game.message_id}")
                    return

                all_participants = [p for p in game.participants if p.user_id and p.user]
                sorted_participants = participant_sorting.sort_participants(all_participants)

                max_players = game.max_players or 10
                confirmed_participants = sorted_participants[:max_players]
                overflow_participants = sorted_participants[max_players:]

                # Extract Discord IDs for display
                confirmed_ids = [p.user.discord_id for p in confirmed_participants]
                overflow_ids = [p.user.discord_id for p in overflow_participants]

                content, embed, view = format_game_announcement(
                    game_id=str(game.id),
                    game_title=game.title,
                    description=game.description,
                    scheduled_at=game.scheduled_at,
                    host_id=game.host.discord_id,
                    participant_ids=confirmed_ids,
                    overflow_ids=overflow_ids,
                    current_count=len(confirmed_participants),
                    max_players=max_players,
                    status=game.status,
                    signup_instructions=game.signup_instructions,
                    expected_duration_minutes=game.expected_duration_minutes,
                    notify_role_ids=game.notify_role_ids,
                )

                await message.edit(content=content, embed=embed, view=view)

                logger.info(f"Refreshed game message: game={game_id}, message={game.message_id}")

                # Set throttle key to prevent immediate subsequent updates
                redis = await get_redis_client()
                cache_key = CacheKeys.message_update_throttle(game_id)
                await redis.set(cache_key, "1", ttl=CacheTTL.MESSAGE_UPDATE_THROTTLE)

        except Exception as e:
            logger.error(f"Failed to refresh game message: {e}", exc_info=True)

    async def _handle_send_notification(self, data: dict[str, Any]) -> None:
        """
        Handle notification.send_dm event by sending DM to user.

        Args:
            data: Event payload with notification details
        """
        try:
            notification = NotificationSendDMEvent(**data)
        except Exception as e:
            logger.error(f"Invalid notification event data: {e}")
            return

        try:
            user = await self.bot.fetch_user(int(notification.user_id))

            if not user:
                logger.error(f"User not found: {notification.user_id}")
                return

            await user.send(notification.message)

            logger.info(
                f"Sent notification DM: user={notification.user_id}, "
                f"game={notification.game_id}, type={notification.notification_type}"
            )

        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {notification.user_id}: DMs disabled")
        except Exception as e:
            logger.error(
                f"Failed to send notification to {notification.user_id}: {e}",
                exc_info=True,
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

                channel = await self.bot.fetch_channel(int(channel_id))
                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Invalid or inaccessible channel: {channel_id}")
                    return

                try:
                    message = await channel.fetch_message(int(message_id))

                    all_participants = [p for p in game.participants if p.user_id and p.user]
                    sorted_participants = participant_sorting.sort_participants(all_participants)

                    max_players = game.max_players or 10
                    confirmed_participants = sorted_participants[:max_players]
                    overflow_participants = sorted_participants[max_players:]

                    confirmed_ids = [p.user.discord_id for p in confirmed_participants]
                    overflow_ids = [p.user.discord_id for p in overflow_participants]

                    embed, view = format_game_announcement(
                        game_id=game_id,
                        title=game.title,
                        description=game.description,
                        signup_instructions=game.signup_instructions,
                        scheduled_at_unix=int(game.scheduled_at.timestamp()),
                        max_players=max_players,
                        min_players=game.min_players or 1,
                        confirmed_participant_ids=confirmed_ids,
                        overflow_participant_ids=overflow_ids,
                        channel_name=game.channel.channel_name if game.channel else None,
                        host_discord_id=game.host.discord_id,
                        notify_role_ids=game.notify_role_ids or [],
                    )

                    await message.edit(embed=embed, view=view)
                    logger.info(f"Updated game message after participant removal: {message_id}")

                except discord.NotFound:
                    logger.warning(f"Game message not found: {message_id}")
                except Exception as e:
                    logger.error(f"Failed to update game message: {e}", exc_info=True)

            # Send DM to removed user
            if discord_id:
                try:
                    user = await self.bot.fetch_user(int(discord_id))
                    if user:
                        dm_message = f"❌ You were removed from **{game_title}**"
                        if game_scheduled_at:
                            dm_message += (
                                f" scheduled for <t:{int(game.scheduled_at.timestamp())}:F>"
                            )

                        await user.send(dm_message)
                        logger.info(f"Sent removal DM to user {discord_id}")
                    else:
                        logger.warning(f"User not found for DM: {discord_id}")
                except discord.Forbidden:
                    logger.warning(f"Cannot send DM to user {discord_id}: DMs disabled")
                except Exception as e:
                    logger.error(f"Failed to send removal DM to {discord_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to handle participant removal: {e}", exc_info=True)

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
            .where(GameSession.id == str(UUID(game_id)))
        )
        game = result.scalar_one_or_none()

        return game
