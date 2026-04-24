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

import asyncio
from datetime import UTC, datetime
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

        # Bot uses guilds intent to receive guild join/remove events
        assert bot.intents.guilds is True
        assert bot.intents.guild_messages is True
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

        mock_redis = AsyncMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[])
        mock_redis._client = MagicMock()
        mock_redis._client.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_redis._client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis._client.scan = AsyncMock(return_value=(0, []))
        mock_redis._client.delete = AsyncMock()

        with patch("services.bot.bot.logger") as mock_logger:
            with patch.object(type(bot), "user", new_callable=lambda: mock_user):
                with patch.object(type(bot), "guilds", new_callable=lambda: mock_guilds):
                    with (
                        patch.object(bot, "_start_test_server", new_callable=AsyncMock),
                        patch.object(bot, "_rebuild_redis_from_gateway", new_callable=AsyncMock),
                        patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock),
                        patch.object(bot, "_trigger_sweep", new_callable=AsyncMock),
                        patch(
                            "services.bot.bot.get_redis_client",
                            new_callable=AsyncMock,
                            return_value=mock_redis,
                        ),
                        patch("services.bot.bot.Path") as mock_path,
                    ):
                        await bot.on_ready()

                    assert mock_logger.info.call_count >= 2
                    mock_path.assert_called_once_with("/tmp/bot-ready")
                    mock_path.return_value.touch.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_guild_sync_success(self, bot_config: BotConfig) -> None:
        """Test setup_hook completes without error."""
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
            patch("services.bot.events.handlers.EventHandlers"),
            patch.object(bot.tree, "sync", new_callable=AsyncMock),
        ):
            await bot.setup_hook()

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

        mock_sync_results = {"new_guilds": 1, "new_channels": 5}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch(
                "services.bot.bot.sync_single_guild_from_gateway",
                new_callable=AsyncMock,
                return_value=mock_sync_results,
            ) as mock_sync,
        ):
            await bot.on_guild_join(mock_guild)

            mock_logger.info.assert_any_call(
                "Bot added to guild: %s (ID: %s)", "Test Guild", 987654321
            )
            mock_sync.assert_awaited_once_with(guild=mock_guild, db=mock_db)
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

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch(
                "services.bot.bot.sync_single_guild_from_gateway",
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

        mock_sync_results = {"new_guilds": 1, "new_channels": 5}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch(
                "services.bot.bot.sync_single_guild_from_gateway",
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

        mock_sync_results = {"new_guilds": 0, "new_channels": 0}

        with (
            patch("services.bot.bot.logger") as mock_logger,
            patch("services.bot.bot.get_db_session", return_value=mock_db_session_cm),
            patch(
                "services.bot.bot.sync_single_guild_from_gateway",
                new_callable=AsyncMock,
                return_value=mock_sync_results,
            ) as mock_sync,
        ):
            await bot.on_guild_join(mock_guild)

            mock_sync.assert_awaited_once_with(guild=mock_guild, db=mock_db)
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

    @pytest.mark.asyncio
    async def test_recover_pending_workers_spawns_workers(self, bot_config: BotConfig) -> None:
        """Workers are spawned for all channels with pending queue rows."""
        bot = GameSchedulerBot(bot_config)
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {}
        mock_handlers._channel_worker = MagicMock()
        bot.event_handlers = mock_handlers

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("111222333",), ("444555666",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("services.bot.bot.get_db_session", return_value=mock_db_ctx),
            patch("services.bot.bot.asyncio.create_task") as mock_create_task,
        ):
            mock_create_task.return_value = MagicMock()
            await bot._recover_pending_workers()

        assert mock_create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_recover_pending_workers_skips_active_workers(
        self, bot_config: BotConfig
    ) -> None:
        """Channels with an active (not done) worker are not given a new task."""
        bot = GameSchedulerBot(bot_config)
        active_task = MagicMock()
        active_task.done.return_value = False
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {"111222333": active_task}
        mock_handlers._channel_worker = MagicMock()
        bot.event_handlers = mock_handlers

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("111222333",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("services.bot.bot.get_db_session", return_value=mock_db_ctx),
            patch("services.bot.bot.asyncio.create_task") as mock_create_task,
        ):
            await bot._recover_pending_workers()

        mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_recover_pending_workers_db_exception_logged(self, bot_config: BotConfig) -> None:
        """A DB error during recovery is caught and logged; the method does not raise."""
        bot = GameSchedulerBot(bot_config)
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {}
        bot.event_handlers = mock_handlers

        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot.get_db_session", return_value=mock_db_ctx):
            await bot._recover_pending_workers()  # must not raise

    def test_spawn_channel_worker_creates_new_task(self, bot_config: BotConfig) -> None:
        """_spawn_channel_worker creates a task when no worker exists for the channel."""
        bot = GameSchedulerBot(bot_config)
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {}
        bot.event_handlers = mock_handlers

        mock_task = MagicMock()
        with patch("services.bot.bot.asyncio.create_task", return_value=mock_task) as mock_ct:
            result = bot._spawn_channel_worker("channel-1")

        mock_ct.assert_called_once()
        assert result is mock_task
        assert mock_handlers._channel_workers["channel-1"] is mock_task

    def test_spawn_channel_worker_reuses_active_task(self, bot_config: BotConfig) -> None:
        """_spawn_channel_worker returns the existing task when it is still running."""
        bot = GameSchedulerBot(bot_config)
        active_task = MagicMock()
        active_task.done.return_value = False
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {"channel-1": active_task}
        bot.event_handlers = mock_handlers

        with patch("services.bot.bot.asyncio.create_task") as mock_ct:
            result = bot._spawn_channel_worker("channel-1")

        mock_ct.assert_not_called()
        assert result is active_task

    def test_spawn_channel_worker_replaces_finished_task(self, bot_config: BotConfig) -> None:
        """_spawn_channel_worker creates a new task when the existing one is done."""
        bot = GameSchedulerBot(bot_config)
        done_task = MagicMock()
        done_task.done.return_value = True
        mock_handlers = MagicMock()
        mock_handlers._channel_workers = {"channel-1": done_task}
        bot.event_handlers = mock_handlers

        new_task = MagicMock()
        with patch("services.bot.bot.asyncio.create_task", return_value=new_task) as mock_ct:
            result = bot._spawn_channel_worker("channel-1")

        mock_ct.assert_called_once()
        assert result is new_task
        assert mock_handlers._channel_workers["channel-1"] is new_task

    @pytest.mark.asyncio
    async def test_on_raw_message_delete_game_found_publishes(self, bot_config: BotConfig) -> None:
        """When deleted message matches a game embed, EMBED_DELETED is published."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_game = MagicMock()
        mock_game.id = "550e8400-e29b-41d4-a716-446655440000"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_game
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        payload = MagicMock(spec=discord.RawMessageDeleteEvent)
        payload.message_id = 123456789
        payload.channel_id = 987654321
        payload.guild_id = 111222333

        with patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx):
            await bot.on_raw_message_delete(payload)

        mock_publisher.publish_embed_deleted.assert_awaited_once_with(
            game_id=str(mock_game.id),
            channel_id="987654321",
            message_id="123456789",
        )

    @pytest.mark.asyncio
    async def test_on_raw_message_delete_no_game_no_publish(self, bot_config: BotConfig) -> None:
        """When deleted message matches no game embed, no event is published."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        payload = MagicMock(spec=discord.RawMessageDeleteEvent)
        payload.message_id = 123456789
        payload.channel_id = 987654321
        payload.guild_id = 111222333

        with patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx):
            await bot.on_raw_message_delete(payload)

        mock_publisher.publish_embed_deleted.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sweep_deleted_embeds_publishes_for_missing_messages(
        self, bot_config: BotConfig
    ) -> None:
        """Games whose embed posts return 404 generate an EMBED_DELETED event."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_game = MagicMock()
        mock_game.id = "550e8400-e29b-41d4-a716-446655440001"
        mock_game.channel.channel_id = "111"
        mock_game.message_id = "999"
        mock_game.scheduled_at = datetime(2026, 1, 1, tzinfo=UTC)

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_game]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_redis = AsyncMock()
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock()
        mock_channel.__class__ = discord.TextChannel
        mock_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(MagicMock(), ""))

        with (
            patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx),
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
        ):
            bot.get_channel = MagicMock(return_value=mock_channel)
            await bot._sweep_deleted_embeds()

        mock_publisher.publish_embed_deleted.assert_awaited_once_with(
            game_id=str(mock_game.id),
            channel_id=mock_game.channel.channel_id,
            message_id=mock_game.message_id,
        )

    @pytest.mark.asyncio
    async def test_sweep_deleted_embeds_skips_existing_messages(
        self, bot_config: BotConfig
    ) -> None:
        """Games whose embed posts still exist do not generate an EMBED_DELETED event."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_game = MagicMock()
        mock_game.id = "550e8400-e29b-41d4-a716-446655440002"
        mock_game.channel.channel_id = "222"
        mock_game.message_id = "888"
        mock_game.scheduled_at = datetime(2026, 1, 2, tzinfo=UTC)

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_game]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_redis = AsyncMock()
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)

        mock_message = MagicMock()
        mock_channel = AsyncMock()
        mock_channel.__class__ = discord.TextChannel
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        with (
            patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx),
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
        ):
            bot.get_channel = MagicMock(return_value=mock_channel)
            await bot._sweep_deleted_embeds()

        mock_publisher.publish_embed_deleted.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sweep_deleted_embeds_no_games(self, bot_config: BotConfig) -> None:
        """When no games have a message_id, the sweep completes without Discord calls."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx):
            await bot._sweep_deleted_embeds()

        mock_publisher.publish_embed_deleted.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sweep_deleted_embeds_no_publisher_skips(self, bot_config: BotConfig) -> None:
        """Sweep exits early when no event publisher is configured."""
        bot = GameSchedulerBot(bot_config)
        bot.event_publisher = None

        with patch("services.bot.bot.get_bypass_db_session") as mock_db:
            await bot._sweep_deleted_embeds()

        mock_db.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_message_delete_exception_is_caught(self, bot_config: BotConfig) -> None:
        """Exceptions inside on_raw_message_delete are caught and not propagated."""
        bot = GameSchedulerBot(bot_config)

        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db error"))
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        payload = MagicMock(spec=discord.RawMessageDeleteEvent)
        payload.message_id = 999
        payload.channel_id = 111
        payload.guild_id = 222

        with patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx):
            await bot.on_raw_message_delete(payload)  # must not raise

    @pytest.mark.asyncio
    async def test_sweep_deleted_embeds_db_exception_is_caught(self, bot_config: BotConfig) -> None:
        """A DB error during the sweep query is caught; the sweep exits without raising."""
        bot = GameSchedulerBot(bot_config)
        mock_publisher = AsyncMock()
        bot.event_publisher = mock_publisher

        mock_db_ctx = MagicMock()
        mock_db_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        mock_db_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot.get_bypass_db_session", return_value=mock_db_ctx):
            await bot._sweep_deleted_embeds()  # must not raise

    @pytest.mark.asyncio
    async def test_run_sweep_worker_skips_channel_when_not_in_gateway_cache(
        self, bot_config: BotConfig
    ) -> None:
        """Worker skips and logs warning when get_channel returns None."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)

        queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        await queue.put((datetime(2026, 1, 1, tzinfo=UTC), "game-1", "111222333", "999888777"))

        bot.get_channel = MagicMock(return_value=None)
        bot.fetch_channel = AsyncMock()

        await bot._run_sweep_worker(queue, mock_redis, mock_publisher)

        bot.fetch_channel.assert_not_awaited()
        mock_publisher.publish_embed_deleted.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_sweep_worker_non_text_channel_skips(self, bot_config: BotConfig) -> None:
        """Worker skips and does not publish when the channel is not a TextChannel."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)

        non_text_channel = MagicMock(spec=discord.CategoryChannel)

        queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        await queue.put((datetime(2026, 1, 1, tzinfo=UTC), "game-2", "111222444", "999888666"))

        bot.get_channel = MagicMock(return_value=non_text_channel)

        await bot._run_sweep_worker(queue, mock_redis, mock_publisher)

        mock_publisher.publish_embed_deleted.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_sweep_worker_general_exception_is_caught(
        self, bot_config: BotConfig
    ) -> None:
        """A non-NotFound exception from fetch_message is caught and logged."""
        bot = GameSchedulerBot(bot_config)

        mock_publisher = AsyncMock()
        mock_publisher.publish_embed_deleted = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock()
        mock_channel.__class__ = discord.TextChannel
        mock_channel.fetch_message = AsyncMock(side_effect=RuntimeError("network error"))

        queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        await queue.put((datetime(2026, 1, 1, tzinfo=UTC), "game-3", "111222555", "999888555"))

        bot.get_channel = MagicMock(return_value=mock_channel)

        await bot._run_sweep_worker(queue, mock_redis, mock_publisher)  # must not raise

        mock_publisher.publish_embed_deleted.assert_not_awaited()


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
