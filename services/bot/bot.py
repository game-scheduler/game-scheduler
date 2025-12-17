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


"""Discord bot implementation with Gateway connection."""

import logging

import discord
from discord.ext import commands
from opentelemetry import trace

from services.bot.config import BotConfig

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Forward declarations to avoid circular imports
if False:  # TYPE_CHECKING equivalent
    from services.bot.events.handlers import EventHandlers
    from services.bot.events.publisher import BotEventPublisher
    from services.bot.handlers import ButtonHandler


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

        intents = discord.Intents.none()

        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=int(config.discord_client_id),
        )

    async def setup_hook(self) -> None:
        """Initialize bot components before connecting to Gateway."""
        logger.info("Running bot setup hook")

        from services.bot.commands import setup_commands
        from services.bot.events.handlers import EventHandlers
        from services.bot.events.publisher import BotEventPublisher
        from services.bot.handlers import ButtonHandler

        await setup_commands(self)
        logger.info("Commands registered successfully")

        # Initialize event publisher
        self.event_publisher = BotEventPublisher()
        assert self.event_publisher is not None
        await self.event_publisher.connect()
        logger.info("Event publisher connected")

        # Initialize button handler with publisher
        self.button_handler = ButtonHandler(self.event_publisher)
        logger.info("Button handler initialized")

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
            logger.info(f"Bot connected as {self.user} (ID: {self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")
            logger.info("Bot is ready to receive events")

            if self.event_handlers and not hasattr(self, "_event_consumer_started"):
                self._event_consumer_started = True
                self.loop.create_task(self.event_handlers.start_consuming())
                logger.info("Started event consumer task")

    async def on_disconnect(self) -> None:
        """Handle Gateway disconnection."""
        logger.warning("Bot disconnected from Gateway")

    async def on_resumed(self) -> None:
        """Handle Gateway reconnection after disconnect."""
        logger.info("Bot reconnected to Gateway")

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
                "discord.guild_id": (
                    str(interaction.guild_id) if interaction.guild_id else None
                ),
            },
        ):
            if interaction.type == discord.InteractionType.component:
                if self.button_handler:
                    await self.button_handler.handle_interaction(interaction)

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        """
        Handle errors during event processing.

        Args:
            event_method: Name of the event method that raised the error
        """
        logger.exception(f"Error in event {event_method}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        Handle bot being added to a new guild.

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
            logger.info(f"Bot added to guild: {guild.name} (ID: {guild.id})")

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
            logger.info(f"Bot removed from guild: {guild.name} (ID: {guild.id})")

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
