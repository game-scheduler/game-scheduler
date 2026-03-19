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
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from opentelemetry import trace
from sqlalchemy import distinct, select

from services.bot.config import BotConfig
from services.bot.dependencies.discord_client import get_discord_client
from services.bot.guild_sync import sync_all_bot_guilds
from services.bot.message_refresh_listener import MessageRefreshListener
from shared.database import get_db_session
from shared.models.message_refresh_queue import MessageRefreshQueue

if TYPE_CHECKING:
    from services.bot.events.handlers import EventHandlers
    from services.bot.events.publisher import BotEventPublisher
    from services.bot.handlers import ButtonHandler

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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

        intents = discord.Intents(guilds=True)

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

            if not hasattr(self, "_refresh_listener_started"):
                self._refresh_listener_started = True
                self._refresh_listener_task = asyncio.create_task(
                    MessageRefreshListener(
                        self.config.database_url,
                        self._spawn_channel_worker,
                    ).start()
                )
                logger.info("Started message refresh listener task")

    async def on_disconnect(self) -> None:
        """Handle Gateway disconnection."""
        logger.warning("Bot disconnected from Gateway")

    async def on_resumed(self) -> None:
        """Handle Gateway reconnection after disconnect."""
        logger.info("Bot reconnected to Gateway")
        await self._recover_pending_workers()

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
