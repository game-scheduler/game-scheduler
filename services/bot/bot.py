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

from services.bot.config import BotConfig

logger = logging.getLogger(__name__)


class GameSchedulerBot(commands.Bot):
    """
    Discord bot for game scheduling with Gateway connection and auto-reconnect.

    Attributes:
        config: Bot configuration with Discord credentials and service URLs
    """

    def __init__(self, config: BotConfig) -> None:
        """
        Initialize bot with required intents and configuration.

        Args:
            config: Bot configuration with Discord credentials
        """
        self.config = config

        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=config.discord_client_id,
        )

    async def setup_hook(self) -> None:
        """Initialize bot components before connecting to Gateway."""
        logger.info("Running bot setup hook")

        from services.bot.commands import setup_commands

        await setup_commands(self)
        logger.info("Commands registered successfully")

        if self.config.environment == "development":
            logger.info("Syncing commands in development mode")
            await self.tree.sync()

    async def on_ready(self) -> None:
        """Handle bot ready event after successful Gateway connection."""
        logger.info(f"Bot connected as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info("Bot is ready to receive events")

    async def on_disconnect(self) -> None:
        """Handle Gateway disconnection."""
        logger.warning("Bot disconnected from Gateway")

    async def on_resumed(self) -> None:
        """Handle Gateway reconnection after disconnect."""
        logger.info("Bot reconnected to Gateway")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
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
        logger.info(f"Bot added to guild: {guild.name} (ID: {guild.id})")

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
        Handle bot being removed from a guild.

        Args:
            guild: The guild that was left
        """
        logger.info(f"Bot removed from guild: {guild.name} (ID: {guild.id})")

    async def close(self) -> None:
        """Cleanup resources before bot shutdown."""
        logger.info("Shutting down bot")
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
