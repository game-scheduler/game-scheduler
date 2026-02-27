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
        discord_bot_client_id="123456789",
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

        with (
            patch("services.bot.commands.setup_commands", new_callable=AsyncMock),
            patch(
                "services.bot.events.publisher.BotEventPublisher",
                return_value=mock_publisher,
            ),
            patch("services.bot.handlers.ButtonHandler"),
        ):
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

        with (
            patch("services.bot.commands.setup_commands", new_callable=AsyncMock),
            patch(
                "services.bot.events.publisher.BotEventPublisher",
                return_value=mock_publisher,
            ),
            patch("services.bot.handlers.ButtonHandler"),
        ):
            with patch("services.bot.events.handlers.EventHandlers"):
                with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
                    await bot.setup_hook()

                    mock_sync.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_setup_hook_publisher_initialization_failure(self, bot_config: BotConfig) -> None:
        """Test setup_hook raises RuntimeError when event publisher fails to initialize."""
        bot = GameSchedulerBot(bot_config)

        with (
            patch("services.bot.commands.setup_commands", new_callable=AsyncMock),
            patch(
                "services.bot.events.publisher.BotEventPublisher",
                return_value=None,
            ),
            pytest.raises(RuntimeError, match="Failed to initialize event publisher"),
        ):
            await bot.setup_hook()

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
    async def test_setup_hook_guild_sync_success(self, bot_config: BotConfig) -> None:
        """Test setup_hook marks bot as ready when guild sync succeeds."""
        bot_config.environment = "production"
        bot = GameSchedulerBot(bot_config)

        mock_publisher = MagicMock()
        mock_publisher.connect = AsyncMock()

        mock_db = AsyncMock()
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("services.bot.commands.setup_commands", new_callable=AsyncMock),
            patch(
                "services.bot.events.publisher.BotEventPublisher",
                return_value=mock_publisher,
            ),
            patch("services.bot.handlers.ButtonHandler"),
            patch("services.bot.events.handlers.EventHandlers"),
            patch("services.bot.bot.get_discord_client"),
            patch("services.bot.bot.get_db_session", return_value=mock_db_ctx),
            patch(
                "services.bot.bot.sync_all_bot_guilds",
                new_callable=AsyncMock,
                return_value={"new_guilds": 1, "new_channels": 2},
            ),
            patch("services.bot.bot.Path") as mock_path,
            patch.object(bot.tree, "sync", new_callable=AsyncMock),
        ):
            await bot.setup_hook()

            mock_path.assert_called_once_with("/tmp/bot-ready")
            mock_path.return_value.touch.assert_called_once()

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

            mock_logger.error.assert_called_once_with("Error in event %s", "test_event")

    @pytest.mark.asyncio
    async def test_on_guild_join_event(self, bot_config: BotConfig) -> None:
        """Test on_guild_join event handler syncs guild to database."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db_session_cm = MagicMock()
        mock_db_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_discord_client = MagicMock()
        mock_sync_results = {"new_guilds": 1, "new_channels": 5}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch("services.bot.bot.get_discord_client", return_value=mock_discord_client),
            patch(
                "services.bot.bot.sync_all_bot_guilds",
                new_callable=AsyncMock,
                return_value=mock_sync_results,
            ) as mock_sync,
        ):
            await bot.on_guild_join(mock_guild)

            mock_logger.info.assert_any_call(
                "Bot added to guild: %s (ID: %s)", "Test Guild", 987654321
            )
            mock_sync.assert_awaited_once_with(
                mock_discord_client, mock_db, bot_config.discord_bot_token
            )
            mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_guild_join_sync_failure(self, bot_config: BotConfig) -> None:
        """Test on_guild_join handles sync failures gracefully."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321

        mock_db = AsyncMock()
        mock_db_session_cm = MagicMock()
        mock_db_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_discord_client = MagicMock()

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch("services.bot.bot.get_discord_client", return_value=mock_discord_client),
            patch(
                "services.bot.bot.sync_all_bot_guilds",
                new_callable=AsyncMock,
                side_effect=Exception("Sync failed"),
            ),
        ):
            await bot.on_guild_join(mock_guild)

            mock_logger.error.assert_called_once()
            assert "failed" in mock_logger.error.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_on_guild_join_commit_failure(self, bot_config: BotConfig) -> None:
        """Test on_guild_join handles database commit failures gracefully."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock(side_effect=Exception("Commit failed"))
        mock_db_session_cm = MagicMock()
        mock_db_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_discord_client = MagicMock()
        mock_sync_results = {"new_guilds": 1, "new_channels": 5}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch("services.bot.bot.get_discord_client", return_value=mock_discord_client),
            patch(
                "services.bot.bot.sync_all_bot_guilds",
                new_callable=AsyncMock,
                return_value=mock_sync_results,
            ),
        ):
            await bot.on_guild_join(mock_guild)

            mock_logger.error.assert_called_once()
            assert "failed" in mock_logger.error.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_on_guild_join_empty_results(self, bot_config: BotConfig) -> None:
        """Test on_guild_join handles empty sync results (guild already exists)."""
        bot = GameSchedulerBot(bot_config)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Existing Guild"
        mock_guild.id = 111222333

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db_session_cm = MagicMock()
        mock_db_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_discord_client = MagicMock()
        mock_sync_results = {"new_guilds": 0, "new_channels": 0}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch("services.bot.bot.get_discord_client", return_value=mock_discord_client),
            patch(
                "services.bot.bot.sync_all_bot_guilds",
                new_callable=AsyncMock,
                return_value=mock_sync_results,
            ) as mock_sync,
        ):
            await bot.on_guild_join(mock_guild)

            mock_sync.assert_awaited_once_with(
                mock_discord_client, mock_db, bot_config.discord_bot_token
            )
            mock_db.commit.assert_awaited_once()
            mock_logger.error.assert_not_called()

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
                "Bot removed from guild: %s (ID: %s)", "Test Guild", 987654321
            )

    @pytest.mark.asyncio
    async def test_close(self, bot_config: BotConfig) -> None:
        """Test close method logs shutdown and calls parent close."""
        bot = GameSchedulerBot(bot_config)

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("discord.ext.commands.Bot.close", new_callable=AsyncMock) as mock_close,
        ):
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
            discord_bot_client_id="111",
            environment="development",
        )
        config2 = BotConfig(
            discord_bot_token="token2",
            discord_bot_client_id="222",
            environment="production",
        )

        bot1 = await create_bot(config1)
        bot2 = await create_bot(config2)

        assert bot1.config.discord_bot_client_id == "111"
        assert bot2.config.discord_bot_client_id == "222"
        assert bot1 is not bot2
