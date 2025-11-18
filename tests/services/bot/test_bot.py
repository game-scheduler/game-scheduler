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


"""Tests for Discord bot implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.bot import GameSchedulerBot, create_bot
from services.bot.config import BotConfig


@pytest.fixture
def bot_config() -> BotConfig:
    """Create a test bot configuration."""
    return BotConfig(
        discord_bot_token="test_token",
        discord_client_id="123456789",
        log_level="DEBUG",
        environment="development",
    )


@pytest.fixture
def mock_discord_client() -> MagicMock:
    """Create a mock Discord client."""
    mock = MagicMock()
    mock.user = MagicMock()
    mock.user.id = 123456789
    mock.user.name = "TestBot"
    return mock


class TestGameSchedulerBot:
    """Test suite for GameSchedulerBot class."""

    def test_bot_initialization(self, bot_config: BotConfig) -> None:
        """Test bot initializes with correct configuration."""
        bot = GameSchedulerBot(bot_config)

        assert bot.config == bot_config
        assert bot.command_prefix == "!"
        assert bot.application_id == 123456789

    def test_bot_intents_configuration(self, bot_config: BotConfig) -> None:
        """Test that bot has correct intents enabled."""
        bot = GameSchedulerBot(bot_config)

        # Bot uses minimal intents (none) as it only responds to interactions
        assert bot.intents.value == 0
        assert bot.intents.guilds is False
        assert bot.intents.guild_messages is False
        assert bot.intents.message_content is False

    @pytest.mark.asyncio
    async def test_setup_hook_development(self, bot_config: BotConfig) -> None:
        """Test setup_hook syncs commands in development mode."""
        bot_config.environment = "development"
        bot = GameSchedulerBot(bot_config)

        mock_publisher = MagicMock()
        mock_publisher.connect = AsyncMock()

        with patch("services.bot.commands.setup_commands", new_callable=AsyncMock):
            with patch(
                "services.bot.events.publisher.BotEventPublisher", return_value=mock_publisher
            ):
                with patch("services.bot.handlers.ButtonHandler"):
                    with patch("services.bot.events.handlers.EventHandlers"):
                        with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
                            await bot.setup_hook()

                            mock_sync.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_setup_hook_production(self, bot_config: BotConfig) -> None:
        """Test setup_hook does not sync commands in production mode."""
        bot_config.environment = "production"
        bot = GameSchedulerBot(bot_config)

        mock_publisher = MagicMock()
        mock_publisher.connect = AsyncMock()

        with patch("services.bot.commands.setup_commands", new_callable=AsyncMock):
            with patch(
                "services.bot.events.publisher.BotEventPublisher", return_value=mock_publisher
            ):
                with patch("services.bot.handlers.ButtonHandler"):
                    with patch("services.bot.events.handlers.EventHandlers"):
                        with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
                            await bot.setup_hook()

                            mock_sync.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_on_ready_event(self, bot_config: BotConfig) -> None:
        """Test on_ready event handler logs correct information."""
        bot = GameSchedulerBot(bot_config)
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_guilds = [MagicMock(), MagicMock()]

        with patch("services.bot.bot.logger") as mock_logger:
            with patch.object(type(bot), "user", new_callable=lambda: mock_user):
                with patch.object(type(bot), "guilds", new_callable=lambda: mock_guilds):
                    await bot.on_ready()

                    assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    async def test_on_disconnect_event(self, bot_config: BotConfig) -> None:
        """Test on_disconnect event handler logs warning."""
        bot = GameSchedulerBot(bot_config)

        with patch("services.bot.bot.logger") as mock_logger:
            await bot.on_disconnect()

            mock_logger.warning.assert_called_once_with("Bot disconnected from Gateway")

    @pytest.mark.asyncio
    async def test_on_resumed_event(self, bot_config: BotConfig) -> None:
        """Test on_resumed event handler logs reconnection."""
        bot = GameSchedulerBot(bot_config)

        with patch("services.bot.bot.logger") as mock_logger:
            await bot.on_resumed()

            mock_logger.info.assert_called_once_with("Bot reconnected to Gateway")

    @pytest.mark.asyncio
    async def test_on_error_event(self, bot_config: BotConfig) -> None:
        """Test on_error event handler logs exceptions."""
        bot = GameSchedulerBot(bot_config)

        with patch("services.bot.bot.logger") as mock_logger:
            await bot.on_error("test_event")

            mock_logger.exception.assert_called_once_with("Error in event test_event")

    @pytest.mark.asyncio
    async def test_on_guild_join_event(self, bot_config: BotConfig) -> None:
        """Test on_guild_join event handler logs guild information."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321

        with patch("services.bot.bot.logger") as mock_logger:
            await bot.on_guild_join(mock_guild)

            mock_logger.info.assert_called_once_with(
                "Bot added to guild: Test Guild (ID: 987654321)"
            )

    @pytest.mark.asyncio
    async def test_on_guild_remove_event(self, bot_config: BotConfig) -> None:
        """Test on_guild_remove event handler logs guild information."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321

        with patch("services.bot.bot.logger") as mock_logger:
            await bot.on_guild_remove(mock_guild)

            mock_logger.info.assert_called_once_with(
                "Bot removed from guild: Test Guild (ID: 987654321)"
            )

    @pytest.mark.asyncio
    async def test_close(self, bot_config: BotConfig) -> None:
        """Test close method logs shutdown and calls parent close."""
        bot = GameSchedulerBot(bot_config)

        with patch("services.bot.bot.logger") as mock_logger:
            with patch("discord.ext.commands.Bot.close", new_callable=AsyncMock) as mock_close:
                await bot.close()

                mock_logger.info.assert_called_once_with("Shutting down bot")
                mock_close.assert_awaited_once()


class TestCreateBot:
    """Test suite for create_bot function."""

    @pytest.mark.asyncio
    async def test_create_bot_returns_instance(self, bot_config: BotConfig) -> None:
        """Test create_bot returns a GameSchedulerBot instance."""
        bot = await create_bot(bot_config)

        assert isinstance(bot, GameSchedulerBot)
        assert bot.config == bot_config

    @pytest.mark.asyncio
    async def test_create_bot_with_different_configs(self) -> None:
        """Test create_bot works with different configurations."""
        config1 = BotConfig(
            discord_bot_token="token1",
            discord_client_id="111",
            environment="development",
        )
        config2 = BotConfig(
            discord_bot_token="token2",
            discord_client_id="222",
            environment="production",
        )

        bot1 = await create_bot(config1)
        bot2 = await create_bot(config2)

        assert bot1.config.discord_client_id == "111"
        assert bot2.config.discord_client_id == "222"
        assert bot1 is not bot2
