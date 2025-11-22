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
from shared.database import get_db_session
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType, NotificationSendDMEvent
from shared.models.game import GameSession
from shared.models.participant import GameParticipant

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
        }
        # Adaptive rate limiting for message refreshes
        self._pending_refreshes: set[str] = set()  # Track games with pending refreshes
        self._refresh_counts: dict[str, int] = {}  # Track consecutive updates per game
        self._last_update_time: dict[str, float] = {}  # Track last update time per game
        self._backoff_delays = [0.0, 1.0, 1.5, 1.5]  # Progressive delays (0s, 1s, 1.5s, 1.5s...)
        self._idle_reset_threshold = 5.0  # Reset counter after 5s of inactivity
        self._refresh_delay: float = 2.0  # seconds to wait before refreshing
        self._max_wait_time: float = 5.0  # maximum seconds to wait (prevents starvation)

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

        logger.info(f"Started consuming events from queue: {queue_name}")

        await self.consumer.start_consuming()

    async def stop_consuming(self) -> None:
        """Stop consuming events and close connection."""
        # Note: pending refresh tasks will complete naturally
        # No need to cancel since they're just sleep + refresh
        self._pending_refreshes.clear()
        self._refresh_counts.clear()
        self._last_update_time.clear()

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

                # Extract participant Discord IDs
                participant_ids = [
                    p.user.discord_id for p in game.participants if p.user_id and p.user
                ]

                embed, view = format_game_announcement(
                    game_id=str(game.id),
                    game_title=game.title,
                    description=game.description,
                    scheduled_at=game.scheduled_at,
                    host_id=game.host.discord_id,
                    participant_ids=participant_ids,
                    current_count=len([p for p in game.participants if p.user_id]),
                    max_players=game.max_players or 10,
                    status=game.status,
                    rules=game.rules,
                    signup_instructions=game.signup_instructions,
                )

                message = await channel.send(embed=embed, view=view)

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

        Handles all game state changes including participant additions/removals.
        Uses adaptive backoff: 0s (instant), 1s, 1.5s, 1.5s... to balance
        responsiveness and rate limiting.

        Args:
            data: Event payload with game_id and updated fields
        """
        game_id = data.get("game_id")

        if not game_id:
            logger.error("Missing game_id in game.updated event")
            return

        # Skip if refresh already scheduled for this game
        if game_id in self._pending_refreshes:
            logger.debug(f"Game {game_id} refresh already scheduled, skipping")
            return

        current_time = asyncio.get_event_loop().time()

        # Reset counter if game has been idle (no updates for threshold period)
        last_update = self._last_update_time.get(game_id, 0)
        if current_time - last_update > self._idle_reset_threshold:
            self._refresh_counts[game_id] = 0
            idle_time = current_time - last_update
            logger.debug(f"Game {game_id} idle for {idle_time:.1f}s, reset counter")

            # Clean up old entries that have been idle for extended period (3x threshold)
            cleanup_threshold = self._idle_reset_threshold * 3
            stale_games = [
                gid
                for gid, last_time in self._last_update_time.items()
                if current_time - last_time > cleanup_threshold
            ]
            for gid in stale_games:
                self._last_update_time.pop(gid, None)
                self._refresh_counts.pop(gid, None)
                logger.debug(f"Cleaned up stale tracking for game {gid}")

        # Track consecutive updates for adaptive backoff
        update_count = self._refresh_counts.get(game_id, 0)
        delay = self._backoff_delays[min(update_count, len(self._backoff_delays) - 1)]

        logger.debug(
            f"Game {game_id} updated (count={update_count}), scheduling refresh with {delay}s delay"
        )
        self._pending_refreshes.add(game_id)
        self._last_update_time[game_id] = current_time
        self._refresh_counts[game_id] = update_count + 1
        asyncio.create_task(self._delayed_refresh(game_id, delay))

    async def _delayed_refresh(self, game_id: str, delay: float) -> None:
        """
        Refresh message after adaptive delay to balance responsiveness and rate limiting.

        Adaptive backoff: 0s (instant), 1s, 1.5s, 1.5s... ensures:
        - First update: Instant (0s) for responsive UI
        - Subsequent updates: Progressive delays prevent rate limiting
        - Maximum rate: ~3 refreshes per 5s (under Discord's 5 edits/5s limit)

        Args:
            game_id: Game session UUID
            delay: Seconds to wait before refreshing (0 for instant)
        """
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            logger.info(f"Executing refresh for game {game_id} after {delay}s delay")
            await self._refresh_game_message(game_id)
        finally:
            self._pending_refreshes.discard(game_id)
            # Counter persists and only resets after idle period (see _handle_game_updated)

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

                # Extract participant Discord IDs
                participant_ids = [
                    p.user.discord_id for p in game.participants if p.user_id and p.user
                ]

                embed, view = format_game_announcement(
                    game_id=str(game.id),
                    game_title=game.title,
                    description=game.description,
                    scheduled_at=game.scheduled_at,
                    host_id=game.host.discord_id,
                    participant_ids=participant_ids,
                    current_count=len([p for p in game.participants if p.user_id]),
                    max_players=game.max_players or 10,
                    status=game.status,
                    rules=game.rules,
                    signup_instructions=game.signup_instructions,
                )

                await message.edit(embed=embed, view=view)

                logger.info(f"Refreshed game message: game={game_id}, message={game.message_id}")

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
