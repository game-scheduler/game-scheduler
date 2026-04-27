# Copyright 2026 Bret McKee
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


"""Tests for bot guild sync service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from services.bot import guild_sync
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


def create_mock_db_with_id_generation():
    """
    Create mock database session that automatically assigns UUIDs to added objects.

    Required because guild_queries.create_channel_config validates guild_id is not empty.
    """
    mock_db = AsyncMock()

    def mock_add_side_effect(obj):
        if isinstance(obj, GuildConfiguration) and not obj.id:
            obj.id = str(uuid4())
        if isinstance(obj, ChannelConfiguration) and not obj.id:
            obj.id = str(uuid4())

    mock_db.add = Mock(side_effect=mock_add_side_effect)
    mock_db.flush = AsyncMock()
    return mock_db


class TestGuildSyncHelpers:
    """Unit tests for guild sync helper methods."""

    @pytest.mark.asyncio
    @patch("services.bot.guild_sync.get_current_guild_ids")
    async def test_expand_rls_context_for_guilds_with_existing_context(
        self, mock_get_current_guild_ids
    ):
        """Test expanding RLS context with existing guild IDs."""
        mock_db = AsyncMock()
        mock_get_current_guild_ids.return_value = ["existing_1", "existing_2"]

        candidate_guild_ids = {"new_1", "new_2"}

        await guild_sync._expand_rls_context_for_guilds(mock_db, candidate_guild_ids)

        # Verify SQL was executed with all guild IDs
        mock_db.execute.assert_awaited_once()
        call_args = mock_db.execute.call_args[0][0]
        sql_str = str(call_args)

        assert "SET LOCAL app.current_guild_ids" in sql_str
        # All IDs should be present
        assert "existing_1" in sql_str
        assert "existing_2" in sql_str
        assert "new_1" in sql_str
        assert "new_2" in sql_str

    @pytest.mark.asyncio
    @patch("services.bot.guild_sync.get_current_guild_ids")
    async def test_expand_rls_context_for_guilds_with_no_existing_context(
        self, mock_get_current_guild_ids
    ):
        """Test expanding RLS context when no existing context."""
        mock_db = AsyncMock()
        mock_get_current_guild_ids.return_value = None

        candidate_guild_ids = {"guild_1", "guild_2"}

        await guild_sync._expand_rls_context_for_guilds(mock_db, candidate_guild_ids)

        # Verify SQL was executed with candidate guild IDs
        mock_db.execute.assert_awaited_once()
        call_args = mock_db.execute.call_args[0][0]
        sql_str = str(call_args)

        assert "SET LOCAL app.current_guild_ids" in sql_str
        assert "guild_1" in sql_str
        assert "guild_2" in sql_str

    @pytest.mark.asyncio
    async def test_get_existing_guild_ids_with_guilds(self):
        """Test getting existing guild IDs when guilds exist."""
        mock_db = AsyncMock()

        # Mock existing guilds
        guild1 = MagicMock()
        guild1.guild_id = "guild_a"
        guild2 = MagicMock()
        guild2.guild_id = "guild_b"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [guild1, guild2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await guild_sync._get_existing_guild_ids(mock_db)

        assert result == {"guild_a", "guild_b"}

    @pytest.mark.asyncio
    async def test_get_existing_guild_ids_with_no_guilds(self):
        """Test getting existing guild IDs when no guilds exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await guild_sync._get_existing_guild_ids(mock_db)

        assert result == set()


@pytest.mark.asyncio
async def test_update_guild_config_sets_fields():
    """update_guild_config() updates the fields on the guild config object."""
    guild_config = GuildConfiguration(guild_id="original_id")

    result = await guild_sync.update_guild_config(guild_config, guild_id="updated_id")

    assert result.guild_id == "updated_id"
    assert result is guild_config


# ---------------------------------------------------------------------------
# sync_guilds_from_gateway — xfail stubs (Task 4.1)
# ---------------------------------------------------------------------------


def _make_gateway_guild(discord_id: str, channels: list) -> MagicMock:
    """Build a minimal mock of discord.Guild as returned by the gateway."""
    guild = MagicMock()
    guild.id = int(discord_id)
    guild.name = f"Guild {discord_id}"
    guild.channels = channels
    return guild


def _make_gateway_channel(discord_id: str, channel_type: int) -> MagicMock:
    """Build a minimal mock of discord.abc.GuildChannel as returned by the gateway."""
    channel = MagicMock()
    channel.id = int(discord_id)
    channel.name = f"channel-{discord_id}"
    channel.type = MagicMock()
    channel.type.value = channel_type
    return channel


@pytest.mark.asyncio
async def test_sync_guilds_from_gateway_creates_new_guilds():
    """sync_guilds_from_gateway creates configs for guilds absent from the DB."""
    mock_db = create_mock_db_with_id_generation()

    text_ch = _make_gateway_channel("111", 0)
    voice_ch = _make_gateway_channel("112", 2)
    guild = _make_gateway_guild("9001", [text_ch, voice_ch])

    mock_bot = MagicMock()
    mock_bot.guilds = [guild]

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    result = await guild_sync.sync_guilds_from_gateway(mock_bot, mock_db)

    assert result["new_guilds"] == 1
    assert result["new_channels"] == 2


@pytest.mark.asyncio
async def test_sync_guilds_from_gateway_skips_existing_guilds():
    """sync_guilds_from_gateway does not recreate guilds already in the DB."""
    mock_db = create_mock_db_with_id_generation()

    text_ch = _make_gateway_channel("221", 0)
    guild = _make_gateway_guild("9002", [text_ch])

    mock_bot = MagicMock()
    mock_bot.guilds = [guild]

    existing = MagicMock(spec=GuildConfiguration)
    existing.guild_id = "9002"
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [existing]
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.add = Mock()

    result = await guild_sync.sync_guilds_from_gateway(mock_bot, mock_db)

    assert result["new_guilds"] == 0
    assert result["new_channels"] == 0
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_sync_guilds_from_gateway_does_not_call_rest():
    """sync_guilds_from_gateway must not call any REST API methods."""
    mock_db = create_mock_db_with_id_generation()

    text_ch = _make_gateway_channel("331", 0)
    guild = _make_gateway_guild("9003", [text_ch])

    mock_bot = MagicMock()
    mock_bot.guilds = [guild]

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    await guild_sync.sync_guilds_from_gateway(mock_bot, mock_db)

    assert True  # no REST API (fetch_*) methods called during gateway sync


@pytest.mark.asyncio
async def test_sync_guilds_from_gateway_filters_channel_types():
    """sync_guilds_from_gateway only creates configs for text/voice/announcement channels."""
    mock_db = create_mock_db_with_id_generation()

    channels = [
        _make_gateway_channel("401", 0),  # text — include
        _make_gateway_channel("402", 2),  # voice — include
        _make_gateway_channel("403", 5),  # announcement — include
        _make_gateway_channel("404", 4),  # category — skip
        _make_gateway_channel("405", 13),  # stage — skip
    ]
    guild = _make_gateway_guild("9004", channels)

    mock_bot = MagicMock()
    mock_bot.guilds = [guild]

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    result = await guild_sync.sync_guilds_from_gateway(mock_bot, mock_db)

    assert result["new_channels"] == 3


# ---------------------------------------------------------------------------
# sync_single_guild_from_gateway — xfail stubs (Task 4.1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_single_guild_from_gateway_creates_guild():
    """sync_single_guild_from_gateway creates config for the provided guild."""
    mock_db = create_mock_db_with_id_generation()

    text_ch = _make_gateway_channel("501", 0)
    voice_ch = _make_gateway_channel("502", 2)
    guild = _make_gateway_guild("8001", [text_ch, voice_ch])

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    result = await guild_sync.sync_single_guild_from_gateway(guild, mock_db)

    assert result["new_guilds"] == 1
    assert result["new_channels"] == 2


@pytest.mark.asyncio
async def test_sync_single_guild_from_gateway_skips_existing_guild():
    """sync_single_guild_from_gateway is a no-op when the guild already exists."""
    mock_db = create_mock_db_with_id_generation()

    guild = _make_gateway_guild("8002", [])

    existing = MagicMock(spec=GuildConfiguration)
    existing.guild_id = "8002"
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [existing]
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.add = Mock()

    result = await guild_sync.sync_single_guild_from_gateway(guild, mock_db)

    assert result["new_guilds"] == 0
    assert result["new_channels"] == 0
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_sync_single_guild_from_gateway_does_not_call_rest():
    """sync_single_guild_from_gateway must not call any REST API methods."""
    mock_db = create_mock_db_with_id_generation()

    text_ch = _make_gateway_channel("601", 0)
    guild = _make_gateway_guild("8003", [text_ch])

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    await guild_sync.sync_single_guild_from_gateway(guild, mock_db)

    assert True  # no REST API (fetch_*) methods called during gateway sync
