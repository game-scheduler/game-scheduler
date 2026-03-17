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


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_creates_new_guilds():
    """Test that sync_all_bot_guilds creates new guilds with channels and templates."""
    mock_db = create_mock_db_with_id_generation()
    mock_discord_client = AsyncMock()

    # Mock bot guilds from Discord API
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new_1", "name": "Test Guild 1"},
            {"id": "guild_new_2", "name": "Test Guild 2"},
        ]
    )

    # Mock existing guild IDs in database (none exist yet)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock channel data for new guilds
    mock_discord_client.get_guild_channels = AsyncMock(
        side_effect=[
            # Channels for guild_new_1
            [
                {"id": "channel_1_text", "type": 0, "name": "general"},
                {"id": "channel_1_voice", "type": 2, "name": "voice"},
                {"id": "channel_1_announce", "type": 5, "name": "announcements"},
            ],
            # Channels for guild_new_2
            [
                {"id": "channel_2_text", "type": 0, "name": "general"},
            ],
        ]
    )

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify result counts
    assert result["new_guilds"] == 2
    assert result["new_channels"] == 4  # 3 from guild 1 + 1 from guild 2

    # Verify Discord API was called with bot token
    mock_discord_client.get_guilds.assert_awaited_once_with(token="bot_token_123")

    # Verify database operations
    mock_db.execute.assert_awaited()
    assert mock_db.add.call_count >= 2  # At least 2 guilds added


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_skip_existing_guilds():
    """Test that sync_all_bot_guilds skips existing guilds and only creates new ones."""
    mock_db = create_mock_db_with_id_generation()
    mock_discord_client = AsyncMock()

    # Mock bot guilds from Discord API (mix of new and existing)
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_existing", "name": "Existing Guild"},
            {"id": "guild_new", "name": "New Guild"},
        ]
    )

    # Create existing guild object with proper attributes
    class MockGuild:
        def __init__(self, guild_id, db_id):
            self.guild_id = guild_id
            self.id = db_id

    existing_guild = MockGuild("guild_existing", str(uuid4()))

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        existing_guild
    ]  # For _get_existing_guild_ids

    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock channel data for new guild only
    mock_discord_client.get_guild_channels = AsyncMock(
        side_effect=[
            [{"id": "channel_new_text", "type": 0, "name": "general"}],
        ]
    )

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify only new guild was created; existing guild was skipped
    assert result["new_guilds"] == 1
    assert result["new_channels"] == 1

    # Verify get_guild_channels called once (only for new guild)
    assert mock_discord_client.get_guild_channels.await_count == 1
    mock_discord_client.get_guild_channels.assert_any_await("guild_new")


@pytest.mark.asyncio
@patch("services.bot.guild_sync.guild_queries.create_channel_config")
@patch("services.bot.guild_sync.guild_queries.get_channel_by_discord_id")
@patch("services.bot.guild_sync.guild_queries.create_default_template")
async def test_sync_all_bot_guilds_creates_default_template(
    mock_template_service_class,
    mock_get_channel,
    mock_create_channel,
):
    """Test that sync_all_bot_guilds creates default template for new guilds."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock bot guilds from Discord API
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new", "name": "Test Guild"},
        ]
    )

    # Mock no existing guilds in database
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock channel data
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "channel_text", "type": 0, "name": "general"},
        ]
    )

    # Mock channel creation and lookup to return consistent object
    mock_channel = MagicMock(spec=ChannelConfiguration)
    mock_channel.id = str(uuid4())
    mock_create_channel.return_value = AsyncMock()
    mock_get_channel.return_value = mock_channel

    # Mock template creation
    mock_template_service_class.return_value = AsyncMock()

    mock_db.add = Mock()
    mock_db.flush = AsyncMock()

    # Execute
    await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify template creation was called with correct arguments
    mock_template_service_class.assert_awaited_once()
    call_args = mock_template_service_class.call_args
    assert call_args is not None
    assert call_args[0][2] == mock_channel.id  # Third positional arg is channel_id


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_filters_channel_types():
    """Test that sync_all_bot_guilds only creates configs for text/voice/announcement channels."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new", "name": "Test Guild"},
        ]
    )

    # Mock no existing guilds
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock channels with various types
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {
                "id": "channel_text",
                "type": 0,
                "name": "general",
            },  # Text - should be created
            {
                "id": "channel_voice",
                "type": 2,
                "name": "voice",
            },  # Voice - should be created
            {
                "id": "channel_category",
                "type": 4,
                "name": "category",
            },  # Category - skip
            # Announcement - should be created
            {"id": "channel_announce", "type": 5, "name": "announce"},
            {"id": "channel_stage", "type": 13, "name": "stage"},  # Stage - skip
        ]
    )

    # Track created objects so we can set IDs on them
    def mock_add_side_effect(obj):
        if isinstance(obj, GuildConfiguration) and not obj.id:
            obj.id = str(uuid4())
        if isinstance(obj, ChannelConfiguration) and not obj.id:
            obj.id = str(uuid4())

    mock_db.add = Mock(side_effect=mock_add_side_effect)
    mock_db.flush = AsyncMock()

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify only 3 channels created (text, voice, announcement)
    assert result["new_channels"] == 3


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_empty_guild_list():
    """Test sync_all_bot_guilds handles empty guild list gracefully."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock empty bot guilds list
    mock_discord_client.get_guilds = AsyncMock(return_value=[])

    # Mock existing guilds query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify no operations performed
    assert result["new_guilds"] == 0
    assert result["new_channels"] == 0

    # Verify no channels were fetched
    mock_discord_client.get_guild_channels.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_sets_is_active_true():
    """Test that new guilds and channels are created with is_active=True."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new", "name": "Test Guild"},
        ]
    )

    # Mock no existing guilds
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock channels
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "channel_text", "type": 0, "name": "general"},
        ]
    )

    added_objects = []

    def track_add_with_ids(obj):
        if isinstance(obj, GuildConfiguration) and not obj.id:
            obj.id = str(uuid4())
        if isinstance(obj, ChannelConfiguration) and not obj.id:
            obj.id = str(uuid4())
        added_objects.append(obj)

    mock_db.add = Mock(side_effect=track_add_with_ids)
    mock_db.flush = AsyncMock()
    mock_db.flush = AsyncMock()

    # Execute
    await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify guild was created and channels have is_active=True
    guilds_added = [obj for obj in added_objects if isinstance(obj, GuildConfiguration)]
    channels_added = [obj for obj in added_objects if isinstance(obj, ChannelConfiguration)]

    assert len(guilds_added) >= 1

    assert len(channels_added) >= 1
    assert all(channel.is_active for channel in channels_added)


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_idempotency():
    """Test that running sync_all_bot_guilds multiple times is safe (idempotent)."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new", "name": "Test Guild"},
        ]
    )

    # First run: no existing guilds
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "channel_text", "type": 0, "name": "general"},
        ]
    )

    # Track created objects so we can set IDs on them
    created_objects = []

    def mock_add_side_effect(obj):
        if isinstance(obj, GuildConfiguration) and not obj.id:
            obj.id = str(uuid4())
        if isinstance(obj, ChannelConfiguration) and not obj.id:
            obj.id = str(uuid4())
        created_objects.append(obj)

    mock_db.add = Mock(side_effect=mock_add_side_effect)
    mock_db.flush = AsyncMock()

    # Execute first time
    result1 = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")
    assert result1["new_guilds"] == 1
    assert result1["new_channels"] == 1

    # Second run: guild now exists
    existing_guild = MagicMock(spec=GuildConfiguration)
    existing_guild.guild_id = "guild_new"
    mock_execute_result2 = MagicMock()
    mock_execute_result2.scalars.return_value.all.return_value = [existing_guild]
    mock_db.execute = AsyncMock(return_value=mock_execute_result2)

    # Execute second time
    result2 = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify no new guilds created on second run
    assert result2["new_guilds"] == 0
    assert result2["new_channels"] == 0


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_handles_discord_api_error_on_get_guilds():
    """Test that sync handles Discord API errors when fetching guilds."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock Discord API error
    mock_discord_client.get_guilds = AsyncMock(
        side_effect=Exception("Discord API rate limit exceeded")
    )

    # Execute and expect error to propagate
    with pytest.raises(Exception, match="Discord API rate limit exceeded"):
        await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_handles_discord_api_error_on_get_channels():
    """Test that sync handles Discord API errors when fetching channels."""
    mock_db = create_mock_db_with_id_generation()
    mock_discord_client = AsyncMock()

    # Mock bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_new", "name": "Test Guild"},
        ]
    )

    # Mock no existing guilds
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock error when fetching channels
    mock_discord_client.get_guild_channels = AsyncMock(
        side_effect=Exception("Discord API error on channels")
    )

    mock_db.add = Mock()
    mock_db.flush = AsyncMock()

    # Execute and expect error to propagate
    with pytest.raises(Exception, match="Discord API error on channels"):
        await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_verifies_existing_guilds_unchanged():
    """Test that sync does not modify existing guilds."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Mock bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_existing", "name": "Existing Guild"},
        ]
    )

    # Mock existing guild
    existing_guild = MagicMock(spec=GuildConfiguration)
    existing_guild.guild_id = "guild_existing"
    existing_guild.bot_manager_role_ids = ["role1", "role2"]

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [existing_guild]
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Track database operations
    mock_db.add = Mock()
    mock_db.flush = AsyncMock()

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify no new guilds created
    assert result["new_guilds"] == 0
    assert result["new_channels"] == 0

    # Verify existing guild properties unchanged
    assert existing_guild.bot_manager_role_ids == ["role1", "role2"]

    # Verify no database adds occurred
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_sync_all_bot_guilds_handles_multiple_new_guilds():
    """Test syncing multiple new guilds in a single operation."""
    mock_db = create_mock_db_with_id_generation()
    mock_discord_client = AsyncMock()

    # Mock multiple bot guilds
    mock_discord_client.get_guilds = AsyncMock(
        return_value=[
            {"id": "guild_1", "name": "Guild 1"},
            {"id": "guild_2", "name": "Guild 2"},
            {"id": "guild_3", "name": "Guild 3"},
        ]
    )

    # Mock no existing guilds
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    # Mock channels for each guild
    mock_discord_client.get_guild_channels = AsyncMock(
        side_effect=[
            [{"id": "ch1", "type": 0, "name": "general"}],
            [
                {"id": "ch2", "type": 0, "name": "general"},
                {"id": "ch3", "type": 2, "name": "voice"},
            ],
            [{"id": "ch4", "type": 0, "name": "general"}],
        ]
    )

    # Execute
    result = await guild_sync.sync_all_bot_guilds(mock_discord_client, mock_db, "bot_token_123")

    # Verify all guilds created
    assert result["new_guilds"] == 3
    assert result["new_channels"] == 4  # 1 + 2 + 1


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
    @patch("services.bot.guild_sync.guild_queries.create_default_template")
    @patch("services.bot.guild_sync.guild_queries.get_channel_by_discord_id")
    @patch("services.bot.guild_sync.guild_queries.create_channel_config")
    async def test_create_guild_with_channels_and_template_with_text_channels(
        self, mock_create_channel, mock_get_channel, mock_template_service_class
    ):
        """Test creating guild with text channels and template."""
        mock_db = AsyncMock()
        mock_db.add = Mock()

        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "general"},
                {"id": "channel_2", "type": 0, "name": "gaming"},
                {"id": "channel_3", "type": 2, "name": "voice"},
            ]
        )

        # Mock channel config retrieval for template creation
        mock_channel_config = MagicMock()
        mock_channel_config.id = "channel_config_uuid"
        mock_get_channel.return_value = mock_channel_config

        # Mock template creation
        mock_template_service_class.return_value = AsyncMock()

        (
            guilds_created,
            channels_created,
        ) = await guild_sync._create_guild_with_channels_and_template(
            mock_db, mock_discord_client, "guild_123"
        )

        # Verify results
        assert guilds_created == 1
        assert channels_created == 3

        # Verify guild was created
        mock_db.add.assert_called()

        # Verify channel configs were created
        assert mock_create_channel.call_count == 3

        # Verify template was created for first text channel
        mock_template_service_class.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_guild_with_channels_and_template_with_no_channels(self):
        """Test creating guild when no channels exist."""
        mock_db = AsyncMock()
        mock_db.add = Mock()

        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels = AsyncMock(return_value=[])

        (
            guilds_created,
            channels_created,
        ) = await guild_sync._create_guild_with_channels_and_template(
            mock_db, mock_discord_client, "guild_123"
        )

        # Verify results
        assert guilds_created == 1
        assert channels_created == 0

        # Verify guild was created
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    @patch("services.bot.guild_sync.guild_queries.create_channel_config")
    async def test_create_guild_with_channels_and_template_with_only_voice_channels(
        self, mock_create_channel
    ):
        """Test creating guild when only voice channels exist."""
        mock_db = AsyncMock()
        mock_db.add = Mock()

        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "voice_1", "type": 2, "name": "Voice 1"},
                {"id": "voice_2", "type": 2, "name": "Voice 2"},
            ]
        )

        (
            guilds_created,
            channels_created,
        ) = await guild_sync._create_guild_with_channels_and_template(
            mock_db, mock_discord_client, "guild_123"
        )

        # Verify results
        assert guilds_created == 1
        assert channels_created == 2

        # Verify channel creation was called for both voice channels
        assert mock_create_channel.call_count == 2


@pytest.mark.asyncio
async def test_update_guild_config_sets_fields():
    """update_guild_config() updates the fields on the guild config object."""
    guild_config = GuildConfiguration(guild_id="original_id")

    result = await guild_sync.update_guild_config(guild_config, guild_id="updated_id")

    assert result.guild_id == "updated_id"
    assert result is guild_config


@pytest.mark.asyncio
async def test_refresh_guild_channels_returns_zero_for_unknown_guild():
    """_refresh_guild_channels() returns 0 if guild not found in database."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_discord = AsyncMock()

    result = await guild_sync._refresh_guild_channels(mock_db, mock_discord, "unknown_guild")

    assert result == 0


@pytest.mark.asyncio
async def test_refresh_guild_channels_creates_new_channel():
    """_refresh_guild_channels() creates a DB record for a channel not yet in the database."""
    guild_id = str(uuid4())
    mock_db = AsyncMock()

    mock_guild = MagicMock()
    mock_guild.id = guild_id

    mock_guild_result = MagicMock()
    mock_guild_result.scalar_one_or_none.return_value = mock_guild

    mock_channels_result = MagicMock()
    mock_channels_result.fetchall.return_value = []

    mock_db.execute = AsyncMock(side_effect=[mock_guild_result, mock_channels_result])

    mock_discord = AsyncMock()
    mock_discord.get_guild_channels = AsyncMock(return_value=[{"id": "new_channel_1", "type": 0}])

    with patch(
        "services.bot.guild_sync.guild_queries.create_channel_config",
        new_callable=AsyncMock,
    ) as mock_create:
        result = await guild_sync._refresh_guild_channels(mock_db, mock_discord, "guild_discord_id")

    assert result == 1
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_guild_channels_reactivates_inactive_channel():
    """_refresh_guild_channels() sets is_active=true for channels back in Discord."""
    guild_id = str(uuid4())
    channel_db_id = str(uuid4())
    mock_db = AsyncMock()

    mock_guild = MagicMock()
    mock_guild.id = guild_id

    mock_guild_result = MagicMock()
    mock_guild_result.scalar_one_or_none.return_value = mock_guild

    mock_channels_result = MagicMock()
    mock_channels_result.fetchall.return_value = [
        (channel_db_id, "channel_discord_1", False),
    ]

    mock_db.execute = AsyncMock(side_effect=[mock_guild_result, mock_channels_result, AsyncMock()])

    mock_discord = AsyncMock()
    mock_discord.get_guild_channels = AsyncMock(
        return_value=[{"id": "channel_discord_1", "type": 0}]
    )

    result = await guild_sync._refresh_guild_channels(mock_db, mock_discord, "guild_discord_id")

    assert result == 1
    assert mock_db.execute.await_count == 3


@pytest.mark.asyncio
async def test_refresh_guild_channels_deactivates_missing_channel():
    """_refresh_guild_channels() sets is_active=false for channels removed from Discord."""
    guild_id = str(uuid4())
    channel_db_id = str(uuid4())
    mock_db = AsyncMock()

    mock_guild = MagicMock()
    mock_guild.id = guild_id

    mock_guild_result = MagicMock()
    mock_guild_result.scalar_one_or_none.return_value = mock_guild

    mock_channels_result = MagicMock()
    mock_channels_result.fetchall.return_value = [
        (channel_db_id, "channel_discord_1", True),
    ]

    mock_db.execute = AsyncMock(side_effect=[mock_guild_result, mock_channels_result, AsyncMock()])

    mock_discord = AsyncMock()
    mock_discord.get_guild_channels = AsyncMock(return_value=[])

    result = await guild_sync._refresh_guild_channels(mock_db, mock_discord, "guild_discord_id")

    assert result == 1
    assert mock_db.execute.await_count == 3
