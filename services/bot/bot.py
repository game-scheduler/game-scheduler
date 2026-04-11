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


"""Discord bot implementation with Gateway connection."""

import asyncio
import contextlib
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp.web
import discord
from discord.ext import commands
from opentelemetry import metrics, trace
from sqlalchemy import distinct, select
from sqlalchemy.orm import joinedload

from services.bot.config import BotConfig
from services.bot.dependencies.discord_client import get_discord_client
from services.bot.guild_sync import sync_all_bot_guilds
from services.bot.message_refresh_listener import MessageRefreshListener
from shared.cache.client import RedisClient, get_redis_client
from shared.database import get_bypass_db_session, get_db_session
from shared.models.game import GameSession
from shared.models.message_refresh_queue import MessageRefreshQueue
from shared.utils.status_transitions import GameStatus

if TYPE_CHECKING:
    from services.bot.events.handlers import EventHandlers
    from services.bot.events.publisher import BotEventPublisher
    from services.bot.handlers import ButtonHandler

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

sweep_started_counter = meter.create_counter(
    name="bot.sweep.started",
    description="Number of embed deletion sweeps started",
    unit="1",
)
sweep_interrupted_counter = meter.create_counter(
    name="bot.sweep.interrupted",
    description="Number of sweeps cancelled because a new sweep was triggered",
    unit="1",
)
sweep_messages_checked_counter = meter.create_counter(
    name="bot.sweep.messages_checked",
    description="Total Discord messages fetched during sweeps",
    unit="1",
)
sweep_deletions_detected_counter = meter.create_counter(
    name="bot.sweep.deletions_detected",
    description="Total EMBED_DELETED events published by sweeps",
    unit="1",
)
sweep_duration_histogram = meter.create_histogram(
    name="bot.sweep.duration",
    description="Duration of completed embed deletion sweeps in seconds",
    unit="s",
)


# Forward declarations to avoid circular imports
if False:  # TYPE_CHECKING equivalent
    pass


class GameSchedulerBot(commands.Bot):
    """
    Discord bot for game scheduling with Gateway connection and auto-reconnect.

    Attributes:
        config: Bot configuration with Discord credentials and service URLs
        button_handler: Handler for button interactions
        event_handlers: Handler for RabbitMQ events
        event_publisher: Publisher for bot events
    """

    def __init__(self, config: BotConfig) -> None:
        """
        Initialize bot with required intents and configuration.

        Args:
            config: Bot configuration with Discord credentials
        """
        self.config = config
        self.button_handler: ButtonHandler | None = None
        self.event_handlers: EventHandlers | None = None
        self.event_publisher: BotEventPublisher | None = None
        self.api_cache = None
        self._sweep_task: asyncio.Task[None] | None = None

        intents = discord.Intents(guilds=True, guild_messages=True)

        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=int(config.discord_bot_client_id),
        )

    async def setup_hook(self) -> None:
        """Initialize bot components before connecting to Gateway."""
        logger.info("Running bot setup hook")

        from services.bot.commands import setup_commands  # noqa: PLC0415 - lazy load
        from services.bot.events.handlers import EventHandlers  # noqa: PLC0415
        from services.bot.events.publisher import BotEventPublisher  # noqa: PLC0415
        from services.bot.handlers import ButtonHandler  # noqa: PLC0415

        await setup_commands(self)
        logger.info("Commands registered successfully")

        # Initialize event publisher
        self.event_publisher = BotEventPublisher()
        if self.event_publisher is None:
            msg = "Failed to initialize event publisher"
            raise RuntimeError(msg)
        await self.event_publisher.connect()
        logger.info("Event publisher connected")

        # Initialize button handler with publisher
        self.button_handler = ButtonHandler(self.event_publisher)
        logger.info("Button handler initialized")

        # Sync all bot guilds on startup (automatic guild sync)
        try:
            discord_client = get_discord_client()
            async with get_db_session() as db:
                sync_results = await sync_all_bot_guilds(
                    discord_client, db, self.config.discord_bot_token
                )
                await db.commit()
                logger.info(
                    "Guild sync on startup: %d new guilds, %d new channels",
                    sync_results["new_guilds"],
                    sync_results["new_channels"],
                )
                # Mark bot as ready after successful sync
                Path("/tmp/bot-ready").touch()  # noqa: S108, ASYNC240, RUF100
                logger.info("Bot marked as healthy")
        except Exception as e:
            logger.exception("Failed to sync guilds on startup: %s", e)

        # Initialize event handlers for consuming messages
        self.event_handlers = EventHandlers(self)
        logger.info("Event handlers initialized")

        if self.config.environment == "development":
            logger.info("Syncing commands in development mode")
            await self.tree.sync()

    async def on_ready(self) -> None:
        """Handle bot ready event after successful Gateway connection."""
        with tracer.start_as_current_span(
            "discord.on_ready",
            attributes={
                "discord.bot_id": str(self.user.id) if self.user else None,
                "discord.bot_name": str(self.user) if self.user else None,
                "discord.guild_count": len(self.guilds),
            },
        ):
            logger.info("Bot connected as %s (ID: %s)", self.user, self.user.id)
            logger.info("Connected to %s guilds", len(self.guilds))
            logger.info("Bot is ready to receive events")

            if self.event_handlers and not hasattr(self, "_event_consumer_started"):
                self._event_consumer_started = True
                self.loop.create_task(self.event_handlers.start_consuming())
                logger.info("Started event consumer task")

            await self._recover_pending_workers()
            await self._trigger_sweep()

            if not hasattr(self, "_refresh_listener_started"):
                self._refresh_listener_started = True
                self._refresh_listener_task = asyncio.create_task(
                    MessageRefreshListener(
                        self.config.database_url,
                        self._spawn_channel_worker,
                    ).start()
                )
                logger.info("Started message refresh listener task")

            if os.getenv("PYTEST_RUNNING"):
                self._test_server_task = asyncio.create_task(self._start_test_server())

    async def on_disconnect(self) -> None:
        """Handle Gateway disconnection."""
        logger.warning("Bot disconnected from Gateway")

    async def on_resumed(self) -> None:
        """Handle Gateway reconnection after disconnect."""
        logger.info("Bot reconnected to Gateway")
        await self._recover_pending_workers()
        await self._trigger_sweep()

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """Handle raw message delete event to detect embed deletions.

        Looks up the deleted message in game_sessions. If a game embed is found,
        publishes EMBED_DELETED to RabbitMQ for the API service to cancel the game.
        """
        message_id = str(payload.message_id)
        try:
            async with get_bypass_db_session() as db:
                result = await db.execute(
                    select(GameSession).where(GameSession.message_id == message_id)
                )
                game = result.scalar_one_or_none()

            if game is None:
                logger.debug("Message %s deleted but not a game embed, ignoring", message_id)
                return

            if self.event_publisher:
                await self.event_publisher.publish_embed_deleted(
                    game_id=str(game.id),
                    channel_id=str(payload.channel_id),
                    message_id=message_id,
                )
        except Exception as e:
            logger.exception("Error handling message delete for message %s: %s", message_id, e)

    async def _trigger_sweep(self) -> None:
        """Cancel any in-progress sweep and start a fresh one.

        If a sweep is already running, cancels it and waits for it to finish
        before launching a new one. Back-to-back on_resumed events therefore
        never run two concurrent sweeps.
        """
        if self._sweep_task and not self._sweep_task.done():
            logger.warning("Embed deletion sweep interrupted: new sweep triggered")
            sweep_interrupted_counter.add(1)
            self._sweep_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sweep_task
        self._sweep_task = asyncio.create_task(self._sweep_deleted_embeds())

    async def _start_test_server(self) -> None:
        """Start the aiohttp test server on port 8089 for e2e sweep triggering."""
        app = aiohttp.web.Application()
        app.router.add_post("/admin/sweep", self._handle_sweep_request)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, None, 8089)
        await site.start()
        logger.info("Test server started on port 8089")

    async def _handle_sweep_request(self, _request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handle POST /admin/sweep: trigger sweep and wait for completion."""
        await self._trigger_sweep()
        if self._sweep_task:
            await self._sweep_task
        return aiohttp.web.Response(status=200)

    async def _recover_pending_workers(self) -> None:
        """Spawn channel workers for any pending message_refresh_queue rows.

        Queries the DB for channels with un-processed queue rows and spawns a
        worker for each channel that does not already have an active one.
        Runs on startup (on_ready) and after reconnect (on_resumed) to recover
        from crashes or disconnects.
        """
        if not self.event_handlers:
            return
        try:
            async with get_db_session() as db:
                result = await db.execute(select(distinct(MessageRefreshQueue.channel_id)))
                channel_ids = [row[0] for row in result.fetchall()]

            workers = self.event_handlers._channel_workers
            for channel_id in channel_ids:
                if channel_id not in workers or workers[channel_id].done():
                    task = asyncio.create_task(self.event_handlers._channel_worker(channel_id))
                    workers[channel_id] = task
                    logger.info("Recovery: spawned worker for channel %s", channel_id)
        except Exception as e:
            logger.exception("Failed to recover pending channel workers: %s", e)

    def _spawn_channel_worker(self, channel_id: str) -> "asyncio.Task[Any]":
        """Spawn a channel worker task, reusing any existing active task."""
        workers = self.event_handlers._channel_workers
        if channel_id not in workers or workers[channel_id].done():
            task = asyncio.create_task(self.event_handlers._channel_worker(channel_id))
            workers[channel_id] = task
            logger.info("Listener: spawned worker for channel %s", channel_id)
            return task
        return workers[channel_id]

    async def _sweep_deleted_embeds(self) -> None:
        """Check for embed posts deleted while the bot was offline.

        Queries all game sessions with a message_id, then fetches each Discord
        message to see if it still exists. For each 404, publishes EMBED_DELETED
        so the API service cancels the game automatically.

        ~60 concurrent workers keep the global rate-limit bucket saturated while
        individual per-channel sleeps avoid per-channel bursts.
        """
        if not self.event_publisher:
            logger.warning("Skipping embed deletion sweep: no event publisher")
            return

        sweep_started_counter.add(1)
        start_time = time.time()

        try:
            async with get_bypass_db_session() as db:
                result = await db.execute(
                    select(GameSession)
                    .options(joinedload(GameSession.channel))
                    .where(GameSession.message_id.is_not(None))
                    .where(
                        GameSession.status.not_in([
                            GameStatus.COMPLETED,
                            GameStatus.CANCELLED,
                            GameStatus.ARCHIVED,
                        ])
                    )
                    .order_by(GameSession.scheduled_at.asc())
                )
                games = result.scalars().all()
        except Exception as e:
            logger.exception("Failed to query games for embed deletion sweep: %s", e)
            return

        if not games:
            logger.info("Embed deletion sweep: no games with message_id to check")
            return

        logger.info("Embed deletion sweep: checking %d games", len(games))

        queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        for game in games:
            await queue.put((
                game.scheduled_at,
                str(game.id),
                str(game.channel.channel_id),
                game.message_id,
            ))

        redis = await get_redis_client()
        num_workers = min(60, queue.qsize())
        workers = [
            self._run_sweep_worker(queue, redis, self.event_publisher) for _ in range(num_workers)
        ]
        await asyncio.gather(*workers)
        sweep_duration_histogram.record(time.time() - start_time)
        logger.info("Embed deletion sweep complete")

    async def _run_sweep_worker(
        self,
        queue: "asyncio.PriorityQueue[tuple]",
        redis: RedisClient,
        publisher: "BotEventPublisher",
    ) -> None:
        """Process one worker loop for the embed deletion sweep.

        Claims rate-limit slots, fetches Discord messages, and publishes
        EMBED_DELETED for any message that returns 404.
        """
        while True:
            try:
                scheduled_at, game_id, channel_id, message_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            wait_ms = await redis.claim_global_and_channel_slot(channel_id)
            if wait_ms > 0:
                await asyncio.sleep(wait_ms / 1000)
                await queue.put((scheduled_at, game_id, channel_id, message_id))
                continue

            try:
                channel = self.get_channel(int(channel_id))
                if channel is None:
                    channel = await self.fetch_channel(int(channel_id))
                if not isinstance(channel, discord.TextChannel):
                    logger.warning("Sweep: channel %s is not a text channel, skipping", channel_id)
                    continue
                await channel.fetch_message(int(message_id))
                sweep_messages_checked_counter.add(1)
            except discord.NotFound:
                sweep_deletions_detected_counter.add(1)
                await publisher.publish_embed_deleted(
                    game_id=game_id,
                    channel_id=channel_id,
                    message_id=message_id,
                )
            except Exception:
                logger.exception(
                    "Sweep: error checking message %s for game %s",
                    message_id,
                    game_id,
                )

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """
        Handle button and other interactions.

        Args:
            interaction: Discord interaction event
        """
        with tracer.start_as_current_span(
            "discord.on_interaction",
            attributes={
                "discord.interaction_type": interaction.type.name,
                "discord.user_id": str(interaction.user.id),
                "discord.channel_id": (
                    str(interaction.channel_id) if interaction.channel_id else None
                ),
                "discord.guild_id": (str(interaction.guild_id) if interaction.guild_id else None),
            },
        ):
            if interaction.type == discord.InteractionType.component and self.button_handler:
                await self.button_handler.handle_interaction(interaction)

    async def on_error(
        self,
        event_method: str,
        /,
        *_args: Any,  # noqa: ANN401
        **_kwargs: Any,  # noqa: ANN401
    ) -> None:
        """
        Handle errors during event processing.

        Args:
            event_method: Name of the event method that raised the error
            _args: Event arguments (unused, required by discord.py)
            _kwargs: Event keyword arguments (unused, required by discord.py)
        """
        logger.error("Error in event %s", event_method)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        Handle bot being added to a new guild.

        Automatically syncs the new guild to the database using sync_all_bot_guilds.

        Args:
            guild: The guild that was joined
        """
        with tracer.start_as_current_span(
            "discord.on_guild_join",
            attributes={
                "discord.guild_id": str(guild.id),
                "discord.guild_name": guild.name,
            },
        ):
            logger.info("Bot added to guild: %s (ID: %s)", guild.name, guild.id)

            try:
                async with get_db_session() as db:
                    discord_client = get_discord_client()
                    results = await sync_all_bot_guilds(
                        discord_client, db, self.config.discord_bot_token
                    )
                    await db.commit()

                logger.info(
                    "Successfully synced guild %s (ID: %s): %d new guilds, %d new channels",
                    guild.name,
                    guild.id,
                    results["new_guilds"],
                    results["new_channels"],
                )
            except Exception as e:
                logger.error("Failed to sync guild %s (ID: %s): %s", guild.name, guild.id, e)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
        Handle bot being removed from a guild.

        Args:
            guild: The guild that was left
        """
        with tracer.start_as_current_span(
            "discord.on_guild_remove",
            attributes={
                "discord.guild_id": str(guild.id),
                "discord.guild_name": guild.name,
            },
        ):
            logger.info("Bot removed from guild: %s (ID: %s)", guild.name, guild.id)

    async def close(self) -> None:
        """Cleanup resources before bot shutdown."""
        logger.info("Shutting down bot")

        if self.event_handlers:
            await self.event_handlers.stop_consuming()

        if self.event_publisher:
            await self.event_publisher.disconnect()

        await super().close()


async def create_bot(config: BotConfig) -> GameSchedulerBot:
    """
    Create and configure bot instance.

    Args:
        config: Bot configuration

    Returns:
        Configured bot instance ready to start
    """
    return GameSchedulerBot(config)
