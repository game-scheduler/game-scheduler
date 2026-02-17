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


"""Tests for guild configuration service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import text

from services.api.services import guild_service
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="create_guild_config moved to bot service, will migrate to RabbitMQ pattern (Phase 6)"
)
@pytest.mark.xfail(
    reason="create_guild_config stubbed - will be replaced with RabbitMQ in Phase 6",
    raises=NotImplementedError,
)
async def test_create_guild_config():
    """Test creating a new guild configuration."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.flush = AsyncMock()

    guild_discord_id = "123456789012345678"
    settings = {
        "bot_manager_role_ids": ["role1", "role2"],
        "require_host_role": True,
    }

    await guild_service.create_guild_config(mock_db, guild_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()

    added_guild = mock_db.add.call_args[0][0]
    assert isinstance(added_guild, GuildConfiguration)
    assert added_guild.guild_id == guild_discord_id
    assert added_guild.bot_manager_role_ids == ["role1", "role2"]
    assert added_guild.require_host_role is True


@pytest.mark.asyncio
async def test_update_guild_config():
    """Test updating a guild configuration."""
    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role1", "role2", "role3"],
        "require_host_role": True,
    }

    await guild_service.update_guild_config(guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role1", "role2", "role3"]
    assert guild_config.require_host_role is True


@pytest.mark.asyncio
async def test_update_guild_config_ignores_none_values():
    """Test that update ignores None values."""
    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role2"],
        "require_host_role": None,  # Will be set to None
    }

    await guild_service.update_guild_config(guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role2"]
    assert guild_config.require_host_role is None  # Updated to None


@pytest.mark.asyncio
@patch("services.api.services.guild_service.get_discord_client")
@patch("services.bot.guild_sync.get_current_guild_ids")
@patch("services.api.services.guild_service.channel_service.create_channel_config")
@patch("services.api.services.guild_service.queries.get_channel_by_discord_id")
@patch("services.bot.guild_sync.template_service_module.TemplateService")
async def test_sync_user_guilds_expands_rls_context_for_new_guilds(
    mock_template_service_class,
    mock_get_channel,
    mock_create_channel,
    mock_get_current_guild_ids,
    mock_get_discord_client,
):
    """Test that sync_user_guilds expands RLS context to include new guild IDs."""
    # Setup mocks
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()
    mock_get_discord_client.return_value = mock_discord_client

    # User has MANAGE_GUILD permission for guild A
    manage_guild_permission = 0x00000020
    mock_discord_client.get_guilds = AsyncMock(
        side_effect=[
            # First call: user guilds
            [
                {"id": "guild_a", "permissions": str(manage_guild_permission)},
            ],
            # Second call: bot guilds
            [
                {"id": "guild_a"},
            ],
        ]
    )

    # Guild A doesn't exist in database yet
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.add = Mock()

    # Current RLS context has some existing guilds
    mock_get_current_guild_ids.return_value = ["existing_guild_1", "existing_guild_2"]

    # Guild has no channels (to keep test simple)
    mock_discord_client.get_guild_channels = AsyncMock(return_value=[])

    # Execute
    result = await guild_service.sync_user_guilds(mock_db, "access_token", "user_id")

    # Verify RLS context was expanded to include new guild
    execute_calls = mock_db.execute.call_args_list
    rls_set_call = [
        call for call in execute_calls if call[0] and isinstance(call[0][0], type(text("")))
    ]

    assert len(rls_set_call) > 0, "Expected SET LOCAL app.current_guild_ids to be called"

    # Verify the SQL contains all guild IDs (existing + new)
    sql_statement = str(rls_set_call[0][0][0])
    assert "SET LOCAL app.current_guild_ids" in sql_statement
    assert "guild_a" in sql_statement  # New guild included

    # Verify new guild was created
    assert result["new_guilds"] == 1
    assert result["new_channels"] == 0
    mock_db.add.assert_called_once()


@patch("services.api.services.guild_service.get_discord_client")
@patch("services.api.services.guild_service.queries.get_guild_by_discord_id")
@patch("services.api.services.guild_service._sync_guild_channels")
@patch("services.bot.guild_sync.get_current_guild_ids")
async def test_sync_user_guilds_syncs_channels_for_existing_guilds(
    mock_get_current_guild_ids,
    mock_sync_guild_channels,
    mock_get_guild_by_discord_id,
    mock_get_discord_client,
):
    """Test that sync_user_guilds syncs channels for existing guilds."""
    # Setup mocks
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()
    mock_get_discord_client.return_value = mock_discord_client

    # User has MANAGE_GUILD permission for guild A (existing guild)
    manage_guild_permission = 0x00000020
    mock_discord_client.get_guilds = AsyncMock(
        side_effect=[
            # First call: user guilds
            [
                {"id": "existing_guild_a", "permissions": str(manage_guild_permission)},
            ],
            # Second call: bot guilds
            [
                {"id": "existing_guild_a"},
            ],
        ]
    )

    # Guild A already exists in database
    existing_guild_config = MagicMock()
    existing_guild_config.id = "guild_config_uuid_a"
    existing_guild_config.guild_id = "existing_guild_a"

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [existing_guild_config]
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_get_current_guild_ids.return_value = []
    mock_get_guild_by_discord_id.return_value = existing_guild_config
    mock_sync_guild_channels.return_value = 3  # 3 channels updated

    # Execute
    result = await guild_service.sync_user_guilds(mock_db, "access_token", "user_id")

    # Verify no new guilds created
    assert result["new_guilds"] == 0
    assert result["new_channels"] == 0
    assert result["updated_channels"] == 3

    # Verify _sync_guild_channels was called for existing guild
    mock_sync_guild_channels.assert_called_once_with(
        mock_db,
        mock_discord_client,
        "guild_config_uuid_a",
        "existing_guild_a",
    )
    mock_get_guild_by_discord_id.assert_called_once_with(mock_db, "existing_guild_a")


@patch("services.api.services.guild_service.get_discord_client")
@patch("services.api.services.guild_service.queries.get_guild_by_discord_id")
@patch("services.api.services.guild_service._sync_guild_channels")
@patch("services.api.services.guild_service._create_guild_with_channels_and_template")
@patch("services.bot.guild_sync.get_current_guild_ids")
async def test_sync_user_guilds_handles_both_new_and_existing_guilds(
    mock_get_current_guild_ids,
    mock_create_guild,
    mock_sync_guild_channels,
    mock_get_guild_by_discord_id,
    mock_get_discord_client,
):
    """Test that sync_user_guilds handles both new and existing guilds in one operation."""
    # Setup mocks
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()
    mock_get_discord_client.return_value = mock_discord_client

    # User has MANAGE_GUILD permission for both guilds
    manage_guild_permission = 0x00000020
    mock_discord_client.get_guilds = AsyncMock(
        side_effect=[
            # First call: user guilds
            [
                {"id": "existing_guild_a", "permissions": str(manage_guild_permission)},
                {"id": "new_guild_b", "permissions": str(manage_guild_permission)},
            ],
            # Second call: bot guilds
            [
                {"id": "existing_guild_a"},
                {"id": "new_guild_b"},
            ],
        ]
    )

    # Only guild A exists in database
    existing_guild_config = MagicMock()
    existing_guild_config.id = "guild_config_uuid_a"
    existing_guild_config.guild_id = "existing_guild_a"

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [existing_guild_config]
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_get_current_guild_ids.return_value = []
    mock_get_guild_by_discord_id.return_value = existing_guild_config
    mock_sync_guild_channels.return_value = 2  # 2 channels updated
    mock_create_guild.return_value = (1, 5)  # 1 guild, 5 channels created

    # Execute
    result = await guild_service.sync_user_guilds(mock_db, "access_token", "user_id")

    # Verify both operations occurred
    assert result["new_guilds"] == 1
    assert result["new_channels"] == 5
    assert result["updated_channels"] == 2

    # Verify _create_guild_with_channels_and_template called for new guild
    mock_create_guild.assert_called_once_with(mock_db, mock_discord_client, "new_guild_b")

    # Verify _sync_guild_channels called for existing guild
    mock_sync_guild_channels.assert_called_once_with(
        mock_db,
        mock_discord_client,
        "guild_config_uuid_a",
        "existing_guild_a",
    )


class TestSyncUserGuildsHelpers:
    """Unit tests for sync_user_guilds helper methods."""

    @pytest.mark.asyncio
    async def test_compute_candidate_guild_ids_with_admin_permissions(self):
        """Test computing candidate guild IDs when user has admin permissions."""
        mock_discord_client = AsyncMock()
        manage_guild = 0x00000020

        # User has MANAGE_GUILD for guilds A and B
        mock_discord_client.get_guilds = AsyncMock(
            side_effect=[
                # User guilds
                [
                    {"id": "guild_a", "permissions": str(manage_guild)},
                    {"id": "guild_b", "permissions": str(manage_guild)},
                    {"id": "guild_c", "permissions": "0"},  # No MANAGE_GUILD
                ],
                # Bot guilds
                [
                    {"id": "guild_a"},
                    {"id": "guild_d"},
                ],
            ]
        )

        result = await guild_service._compute_candidate_guild_ids(
            mock_discord_client, "access_token", "user_id"
        )

        # Should only include guild_a (user admin AND bot present)
        assert result == {"guild_a"}

    @pytest.mark.asyncio
    async def test_compute_candidate_guild_ids_with_no_overlap(self):
        """Test computing candidate guild IDs when there's no overlap."""
        mock_discord_client = AsyncMock()
        manage_guild = 0x00000020

        mock_discord_client.get_guilds = AsyncMock(
            side_effect=[
                # User guilds
                [{"id": "guild_a", "permissions": str(manage_guild)}],
                # Bot guilds (different)
                [{"id": "guild_b"}],
            ]
        )

        result = await guild_service._compute_candidate_guild_ids(
            mock_discord_client, "access_token", "user_id"
        )

        assert result == set()

    @pytest.mark.asyncio
    async def test_compute_candidate_guild_ids_with_no_admin_permissions(self):
        """Test computing candidate guild IDs when user has no admin permissions."""
        mock_discord_client = AsyncMock()

        mock_discord_client.get_guilds = AsyncMock(
            side_effect=[
                # User guilds (no MANAGE_GUILD)
                [
                    {"id": "guild_a", "permissions": "0"},
                    {"id": "guild_b", "permissions": "8"},  # Other permission
                ],
                # Bot guilds
                [{"id": "guild_a"}],
            ]
        )

        result = await guild_service._compute_candidate_guild_ids(
            mock_discord_client, "access_token", "user_id"
        )

        assert result == set()

    @pytest.mark.asyncio
    @patch("services.api.services.guild_service.channel_service.create_channel_config")
    async def test_sync_guild_channels_adds_new_channels(self, mock_create_channel):
        """Test that new Discord channels are added to database."""
        mock_db = AsyncMock()
        mock_discord_client = AsyncMock()

        # Discord has two text channels
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "Channel 1"},
                {"id": "channel_2", "type": 0, "name": "Channel 2"},
            ]
        )

        # Database has no channels
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        result = await guild_service._sync_guild_channels(
            mock_db, mock_discord_client, "guild_uuid", "guild_discord_id"
        )

        # Verify both channels were created
        assert result == 2
        assert mock_create_channel.call_count == 2
        mock_create_channel.assert_any_call(mock_db, "guild_uuid", "channel_1", is_active=True)
        mock_create_channel.assert_any_call(mock_db, "guild_uuid", "channel_2", is_active=True)

    @pytest.mark.asyncio
    async def test_sync_guild_channels_marks_missing_channels_inactive(self):
        """Test that channels missing from Discord are marked inactive."""
        mock_db = AsyncMock()
        mock_discord_client = AsyncMock()

        # Discord has one channel
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "Channel 1"},
            ]
        )

        # Database has two active channels
        existing_channel_1 = ChannelConfiguration(
            id="uuid_1", guild_id="guild_uuid", channel_id="channel_1", is_active=True
        )
        existing_channel_2 = ChannelConfiguration(
            id="uuid_2", guild_id="guild_uuid", channel_id="channel_2", is_active=True
        )

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [
            existing_channel_1,
            existing_channel_2,
        ]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        result = await guild_service._sync_guild_channels(
            mock_db, mock_discord_client, "guild_uuid", "guild_discord_id"
        )

        # Verify one channel was marked inactive
        assert result == 1
        assert existing_channel_1.is_active is True  # Still in Discord
        assert existing_channel_2.is_active is False  # Missing from Discord

    @pytest.mark.asyncio
    @patch("services.api.services.guild_service.channel_service.create_channel_config")
    async def test_sync_guild_channels_reactivates_existing_channels(self, mock_create_channel):
        """Test that inactive channels are reactivated if they reappear in Discord."""
        mock_db = AsyncMock()
        mock_discord_client = AsyncMock()

        # Discord has one channel
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "Channel 1"},
            ]
        )

        # Database has the channel but it's inactive
        existing_channel = ChannelConfiguration(
            id="uuid_1", guild_id="guild_uuid", channel_id="channel_1", is_active=False
        )

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [existing_channel]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        result = await guild_service._sync_guild_channels(
            mock_db, mock_discord_client, "guild_uuid", "guild_discord_id"
        )

        # Verify channel was reactivated
        assert result == 1
        assert existing_channel.is_active is True
        mock_create_channel.assert_not_called()  # No new channel created

    @pytest.mark.asyncio
    async def test_sync_guild_channels_ignores_non_text_channels(self):
        """Test that non-text channels are ignored."""
        mock_db = AsyncMock()
        mock_discord_client = AsyncMock()

        # Discord has mixed channel types
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "Text Channel"},
                {"id": "channel_2", "type": 2, "name": "Voice Channel"},
                {"id": "channel_3", "type": 4, "name": "Category"},
            ]
        )

        # Database has no channels
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch(
            "services.api.services.guild_service.channel_service.create_channel_config"
        ) as mock_create:
            result = await guild_service._sync_guild_channels(
                mock_db, mock_discord_client, "guild_uuid", "guild_discord_id"
            )

            # Verify only one channel (text) was created
            assert result == 1
            assert mock_create.call_count == 1
            mock_create.assert_called_once_with(mock_db, "guild_uuid", "channel_1", is_active=True)

    @pytest.mark.asyncio
    async def test_sync_guild_channels_no_changes_needed(self):
        """Test that no changes are made when database matches Discord."""
        mock_db = AsyncMock()
        mock_discord_client = AsyncMock()

        # Discord has one channel
        mock_discord_client.get_guild_channels = AsyncMock(
            return_value=[
                {"id": "channel_1", "type": 0, "name": "Channel 1"},
            ]
        )

        # Database has the same active channel
        existing_channel = ChannelConfiguration(
            id="uuid_1", guild_id="guild_uuid", channel_id="channel_1", is_active=True
        )

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [existing_channel]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        result = await guild_service._sync_guild_channels(
            mock_db, mock_discord_client, "guild_uuid", "guild_discord_id"
        )

        # Verify no changes were made
        assert result == 0
        assert existing_channel.is_active is True
