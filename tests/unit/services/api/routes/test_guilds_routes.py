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


"""Unit tests for guild configuration endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.api.routes import guilds
from shared.discord.client import DiscordAPIError
from shared.schemas import guild as guild_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_guild_config():
    """Create mock guild configuration."""
    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.guild_id = "987654321"
    config.bot_manager_role_ids = None
    config.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    config.updated_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    return config


@pytest.fixture
def mock_user_guilds():
    """Create mock Discord user guilds data."""
    return [
        {
            "id": "987654321",
            "name": "Test Guild",
            "icon": "icon_hash",
            "owner": False,
            "permissions": "2147483647",
        },
        {
            "id": "111222333",
            "name": "Another Guild",
            "icon": "icon_hash_2",
            "owner": True,
            "permissions": "2147483647",
        },
    ]


class TestListGuilds:
    """Test list_guilds endpoint."""

    @pytest.mark.asyncio
    async def test_list_guilds_uses_projection_not_oauth(
        self,
        mock_db,
        mock_current_user_unit,
        mock_guild_config,
    ):
        """list_guilds must read guild IDs from projection, not oauth2.get_user_guilds."""
        mock_redis = AsyncMock()
        with (
            patch(
                "services.api.routes.guilds.cache_client.get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.api.routes.guilds.member_projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ) as mock_proj_guilds,
            patch(
                "services.api.routes.guilds.member_projection.get_guild_name",
                new_callable=AsyncMock,
                return_value="Test Guild",
            ),
            patch(
                "services.api.database.queries.get_guild_by_discord_id",
                new_callable=AsyncMock,
                return_value=mock_guild_config,
            ),
        ):
            result = await guilds.list_guilds(current_user=mock_current_user_unit, db=mock_db)

            mock_proj_guilds.assert_awaited_once_with(
                mock_current_user_unit.user.discord_id, redis=mock_redis
            )
            assert len(result.guilds) == 1

    @pytest.mark.asyncio
    async def test_list_guilds_success(
        self,
        mock_db,
        mock_current_user_unit,
        mock_guild_config,
    ):
        """Test listing guilds with configurations."""
        mock_redis = AsyncMock()
        with (
            patch(
                "services.api.routes.guilds.cache_client.get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.api.routes.guilds.member_projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
            patch(
                "services.api.routes.guilds.member_projection.get_guild_name",
                new_callable=AsyncMock,
                return_value="Test Guild",
            ),
            patch(
                "services.api.database.queries.get_guild_by_discord_id",
                new_callable=AsyncMock,
                return_value=mock_guild_config,
            ),
        ):
            result = await guilds.list_guilds(current_user=mock_current_user_unit, db=mock_db)

            assert len(result.guilds) == 1
            assert result.guilds[0].id == mock_guild_config.id
            assert result.guilds[0].guild_name == "Test Guild"

    @pytest.mark.asyncio
    async def test_list_guilds_no_configs(self, mock_db, mock_current_user_unit):
        """Test listing guilds when no configurations exist."""
        mock_redis = AsyncMock()
        with (
            patch(
                "services.api.routes.guilds.cache_client.get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.api.routes.guilds.member_projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
            patch(
                "services.api.routes.guilds.member_projection.get_guild_name",
                new_callable=AsyncMock,
                return_value="Test Guild",
            ),
            patch(
                "services.api.database.queries.get_guild_by_discord_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await guilds.list_guilds(current_user=mock_current_user_unit, db=mock_db)

            assert len(result.guilds) == 0


class TestGetGuild:
    """Test get_guild endpoint."""

    @pytest.mark.asyncio
    async def test_get_guild_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild configuration by UUID."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

            assert result.id == mock_guild_config.id
            assert result.guild_name == "Test Guild"
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_get_guild_not_found(self, mock_db, mock_current_user_unit):
        """Test retrieving non-existent guild configuration."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.side_effect = HTTPException(
                status_code=404, detail="Guild configuration not found"
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=str(uuid.uuid4()),
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_called_once_with(
                mock_db, ANY, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_get_guild_not_member(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild where user is not a member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_get_guild_no_session(self, mock_db, mock_current_user_unit, mock_guild_config):
        """Test retrieving guild when session token lookup returns None (endpoint still works)."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

            assert result.id == mock_guild_config.id
            assert result.guild_name == "Test Guild"
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )


class TestCreateGuildConfig:
    """Test create_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_create_guild_success(self, mock_db, mock_current_user_unit, mock_user_guilds):
        """Test creating new guild configuration."""
        with (
            patch("services.api.database.queries.get_guild_by_discord_id") as mock_get_guild,
            patch("services.api.services.guild_service.create_guild_config") as mock_create,
            patch(
                "services.api.dependencies.permissions.get_guild_name",
                return_value="Test Guild",
            ),
        ):
            mock_get_guild.return_value = None

            new_config = MagicMock()
            new_config.id = str(uuid.uuid4())
            new_config.guild_id = "987654321"
            new_config.created_at = datetime.now(tz=UTC)
            new_config.updated_at = datetime.now(tz=UTC)

            mock_create.return_value = new_config

            request = guild_schemas.GuildConfigCreateRequest(
                guild_id="987654321",
            )

            result = await guilds.create_guild_config(
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

            assert result.id == new_config.id
            mock_get_guild.assert_called_once_with(mock_db, "987654321")
            mock_create.assert_called_once_with(mock_db, guild_discord_id="987654321")

    @pytest.mark.asyncio
    async def test_create_guild_already_exists(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test creating guild configuration that already exists."""
        with patch("services.api.database.queries.get_guild_by_discord_id") as mock_get_guild:
            mock_get_guild.return_value = mock_guild_config

            request = guild_schemas.GuildConfigCreateRequest(
                guild_id="987654321",
                default_max_players=12,
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.create_guild_config(
                    request=request,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 409
            mock_get_guild.assert_called_once_with(mock_db, "987654321")


class TestUpdateGuildConfig:
    """Test update_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_guild_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test updating guild configuration."""
        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.services.guild_service.update_guild_config") as mock_update,
            patch(
                "services.api.dependencies.permissions.get_guild_name",
                return_value="Test Guild",
            ),
        ):
            mock_get_guild.return_value = mock_guild_config

            updated_config = MagicMock()
            updated_config.id = mock_guild_config.id
            updated_config.guild_id = "987654321"
            updated_config.created_at = datetime.now(tz=UTC)
            updated_config.updated_at = datetime.now(tz=UTC)

            mock_update.return_value = updated_config

            request = guild_schemas.GuildConfigUpdateRequest()

            await guilds.update_guild_config(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

            mock_update.assert_called_once_with(mock_guild_config)
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_update_guild_not_found(self, mock_db, mock_current_user_unit):
        """Test updating non-existent guild configuration."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.side_effect = HTTPException(
                status_code=404, detail="Guild configuration not found"
            )

            request = guild_schemas.GuildConfigUpdateRequest(
                default_max_players=15,
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.update_guild_config(
                    guild_id=str(uuid.uuid4()),
                    request=request,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_called_once_with(
                mock_db, ANY, mock_current_user_unit.user.discord_id
            )


class TestListGuildChannels:
    """Test list_guild_channels endpoint."""

    @pytest.mark.asyncio
    async def test_list_channels_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels for a guild."""
        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels.return_value = [
            {"id": "channel_123", "name": "Test Channel", "type": 0}
        ]

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.database.queries.get_channels_by_guild") as mock_get_channels,
        ):
            mock_channel = MagicMock()
            mock_channel.id = str(uuid.uuid4())
            mock_channel.guild_id = mock_guild_config.id
            mock_channel.channel_id = "channel_123"
            mock_channel.is_active = True
            mock_channel.created_at = datetime.now(tz=UTC)
            mock_channel.updated_at = datetime.now(tz=UTC)

            mock_get_guild.return_value = mock_guild_config
            mock_get_channels.return_value = [mock_channel]

            result = await guilds.list_guild_channels(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert len(result) == 1
            assert result[0].channel_id == "channel_123"
            assert result[0].channel_name == "Test Channel"
            mock_discord_client.get_guild_channels.assert_awaited_once_with(
                mock_guild_config.guild_id
            )
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_channels.assert_called_once_with(mock_db, mock_guild_config.id)

    @pytest.mark.asyncio
    async def test_list_channels_guild_not_found(self, mock_db, mock_current_user_unit):
        """Test listing channels for non-existent guild."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.side_effect = HTTPException(
                status_code=404, detail="Guild configuration not found"
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_id=str(uuid.uuid4()),
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=AsyncMock(),
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_called_once_with(
                mock_db, ANY, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_list_channels_not_member(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels when user is not guild member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=AsyncMock(),
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )

    @pytest.mark.asyncio
    async def test_list_channels_discord_api_error_falls_back_to_unknown(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test that a Discord API error falls back to 'Unknown Channel' names."""

        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels.side_effect = DiscordAPIError(403, "Missing Access")

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.database.queries.get_channels_by_guild") as mock_get_channels,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_channel = MagicMock()
            mock_channel.id = str(uuid.uuid4())
            mock_channel.guild_id = mock_guild_config.id
            mock_channel.channel_id = "channel_123"
            mock_channel.is_active = True
            mock_channel.created_at = datetime.now(tz=UTC)
            mock_channel.updated_at = datetime.now(tz=UTC)
            mock_get_channels.return_value = [mock_channel]

            result = await guilds.list_guild_channels(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert len(result) == 1
            assert result[0].channel_name == "Unknown Channel"
            mock_get_guild.assert_called_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_channels.assert_called_once_with(mock_db, mock_guild_config.id)

    """Test _build_guild_config_response helper function."""

    @pytest.mark.asyncio
    async def test_build_response_with_all_fields(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test building response with all fields populated."""
        mock_guild_config.bot_manager_role_ids = ["role1", "role2"]

        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = "Test Guild"

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert result.id == mock_guild_config.id
            assert result.guild_name == "Test Guild"
            assert result.bot_manager_role_ids == ["role1", "role2"]
            assert result.created_at == "2024-01-01T12:00:00+00:00"
            assert result.updated_at == "2024-01-01T12:00:00+00:00"

            mock_get_name.assert_called_once_with(mock_guild_config.guild_id, mock_db)

    @pytest.mark.asyncio
    async def test_build_response_with_none_bot_manager_roles(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test building response when bot_manager_role_ids is None."""
        mock_guild_config.bot_manager_role_ids = None

        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = "Test Guild"

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert result.bot_manager_role_ids is None
            mock_get_name.assert_called_once_with(mock_guild_config.guild_id, mock_db)

    @pytest.mark.asyncio
    async def test_build_response_timestamp_formatting(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test that timestamps are properly formatted using isoformat()."""
        mock_guild_config.created_at = datetime(2025, 12, 25, 15, 30, 45, tzinfo=UTC)
        mock_guild_config.updated_at = datetime(2025, 12, 26, 16, 31, 46, tzinfo=UTC)

        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = "Test Guild"

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert result.created_at == "2025-12-25T15:30:45+00:00"
            assert result.updated_at == "2025-12-26T16:31:46+00:00"
            mock_get_name.assert_called_once_with(mock_guild_config.guild_id, mock_db)

    @pytest.mark.asyncio
    async def test_build_response_guild_name_resolution(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test that guild_name is fetched using permissions.get_guild_name()."""
        expected_guild_name = "My Custom Guild Name"

        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = expected_guild_name

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert result.guild_name == expected_guild_name
            mock_get_name.assert_called_once_with(mock_guild_config.guild_id, mock_db)

    @pytest.mark.asyncio
    async def test_build_response_returns_correct_schema_type(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test that response is of correct schema type."""
        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = "Test Guild"

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert isinstance(result, guild_schemas.GuildConfigResponse)
            mock_get_name.assert_called_once_with(mock_guild_config.guild_id, mock_db)


class TestSyncEndpointRemoved:
    """Verify that the /sync endpoint has been removed from the router."""

    def test_sync_guilds_handler_not_registered(self):
        """POST /api/v1/guilds/sync must not exist on the guilds router."""
        assert not hasattr(guilds, "sync_guilds"), (
            "sync_guilds handler should have been removed from guilds.py"
        )


class TestListGuildRoles:
    """Test list_guild_roles endpoint."""

    @pytest.mark.asyncio
    async def test_roles_sorted_case_insensitive(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Roles are returned sorted alphabetically, case-insensitive."""
        mock_discord_client = AsyncMock()
        mock_discord_client.fetch_guild_roles.return_value = [
            {"id": "1", "name": "Zebra Team", "color": 0, "position": 3, "managed": False},
            {"id": "2", "name": "alpha Squad", "color": 0, "position": 1, "managed": False},
            {"id": "3", "name": "Beta Group", "color": 0, "position": 2, "managed": False},
        ]

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch(
                "services.api.dependencies.permissions.verify_guild_membership",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.list_guild_roles(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

        assert [r["name"] for r in result] == ["@alpha Squad", "@Beta Group", "@Zebra Team"]
        mock_get_guild.assert_called_once_with(
            mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
        )

    @pytest.mark.asyncio
    async def test_managed_roles_excluded(self, mock_db, mock_current_user_unit, mock_guild_config):
        """Managed roles are not included in the response."""
        mock_discord_client = AsyncMock()
        mock_discord_client.fetch_guild_roles.return_value = [
            {"id": "1", "name": "Player", "color": 0, "position": 2, "managed": False},
            {"id": "2", "name": "BotRole", "color": 0, "position": 1, "managed": True},
        ]

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch(
                "services.api.dependencies.permissions.verify_guild_membership",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.list_guild_roles(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

        assert len(result) == 1
        assert result[0]["name"] == "@Player"
        mock_get_guild.assert_called_once_with(
            mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
        )


class TestGetGuildConfig:
    """Test get_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_get_guild_config_success(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test retrieving guild config with manage guild permission."""
        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch(
                "services.api.dependencies.permissions.get_guild_name",
                new_callable=AsyncMock,
                return_value="Test Guild",
            ),
        ):
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.get_guild_config(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

        mock_get_guild.assert_called_once_with(
            mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
        )
        assert result.id == mock_guild_config.id


class TestValidateMention:
    """Test validate_mention endpoint."""

    @pytest.mark.asyncio
    async def test_validate_mention_non_at_mention(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test that non-@ strings are always valid (they are placeholders)."""
        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch(
                "services.api.dependencies.permissions.verify_guild_membership",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_guild.return_value = mock_guild_config
            request = guild_schemas.ValidateMentionRequest(mention="placeholder-text")

            result = await guilds.validate_mention(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

        mock_get_guild.assert_called_once_with(
            mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
        )
        assert result.valid is True
        assert result.error is None
