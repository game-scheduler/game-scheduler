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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

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
    config.created_at = datetime(2024, 1, 1, 12, 0, 0)
    config.updated_at = datetime(2024, 1, 1, 12, 0, 0)
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
    async def test_list_guilds_success(
        self,
        mock_db,
        mock_current_user_unit,
        mock_guild_config,
        mock_user_guilds,
        mock_get_user_tokens,
    ):
        """Test listing guilds with configurations."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.get_guild_by_discord_id") as mock_get_guild,
        ):
            mock_get_guilds.return_value = mock_user_guilds
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.list_guilds(current_user=mock_current_user_unit, db=mock_db)

            assert len(result.guilds) == 2
            assert result.guilds[0].id == mock_guild_config.id
            assert result.guilds[0].guild_name == "Test Guild"

    @pytest.mark.asyncio
    async def test_list_guilds_no_configs(
        self, mock_db, mock_current_user_unit, mock_user_guilds, mock_get_user_tokens
    ):
        """Test listing guilds when no configurations exist."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.get_guild_by_discord_id") as mock_get_guild,
        ):
            mock_get_guilds.return_value = mock_user_guilds
            mock_get_guild.return_value = None

            result = await guilds.list_guilds(current_user=mock_current_user_unit, db=mock_db)

            assert len(result.guilds) == 0


class TestGetGuild:
    """Test get_guild endpoint."""

    @pytest.mark.asyncio
    async def test_get_guild_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild configuration by UUID."""
        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds
            mock_get_guild.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
            )

            assert result.id == mock_guild_config.id
            assert result.guild_name == "Test Guild"

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

    @pytest.mark.asyncio
    async def test_get_guild_not_member(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild where user is not a member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds
            mock_get_guild.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_guild_no_session(self, mock_db, mock_current_user_unit, mock_guild_config):
        """Test retrieving guild when session is not found."""
        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
        ):
            mock_get_tokens.return_value = None
            mock_get_guild.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 401


class TestCreateGuildConfig:
    """Test create_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_create_guild_success(self, mock_db, mock_current_user_unit, mock_user_guilds):
        """Test creating new guild configuration."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.get_guild_by_discord_id") as mock_get_guild,
            patch("services.api.services.guild_service.create_guild_config") as mock_create,
            patch(
                "services.api.dependencies.permissions.get_guild_name",
                return_value="Test Guild",
            ),
        ):
            mock_get_guilds.return_value = mock_user_guilds
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
            mock_create.assert_called_once()

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


class TestUpdateGuildConfig:
    """Test update_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_guild_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test updating guild configuration."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.services.guild_service.update_guild_config") as mock_update,
            patch(
                "services.api.dependencies.permissions.get_guild_name",
                return_value="Test Guild",
            ),
        ):
            mock_get_guilds.return_value = mock_user_guilds
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

            mock_update.assert_called_once()

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
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.database.queries.get_channels_by_guild") as mock_get_channels,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

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

    @pytest.mark.asyncio
    async def test_list_channels_not_member(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels when user is not guild member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds
            mock_get_guild.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=AsyncMock(),
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_channels_discord_api_error_falls_back_to_unknown(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_user_guilds
    ):
        """Test that a Discord API error falls back to 'Unknown Channel' names."""

        mock_discord_client = AsyncMock()
        mock_discord_client.get_guild_channels.side_effect = DiscordAPIError(403, "Missing Access")

        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.database.queries.get_channels_by_guild") as mock_get_channels,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds
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
            assert result.created_at == "2024-01-01T12:00:00"
            assert result.updated_at == "2024-01-01T12:00:00"

            mock_get_name.assert_called_once_with(
                mock_guild_config.guild_id, mock_current_user_unit, mock_db
            )

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

    @pytest.mark.asyncio
    async def test_build_response_timestamp_formatting(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test that timestamps are properly formatted using isoformat()."""
        mock_guild_config.created_at = datetime(2025, 12, 25, 15, 30, 45)
        mock_guild_config.updated_at = datetime(2025, 12, 26, 16, 31, 46)

        with patch("services.api.dependencies.permissions.get_guild_name") as mock_get_name:
            mock_get_name.return_value = "Test Guild"

            result = await guilds._build_guild_config_response(
                mock_guild_config, mock_current_user_unit, mock_db
            )

            assert result.created_at == "2025-12-25T15:30:45"
            assert result.updated_at == "2025-12-26T16:31:46"

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
            mock_get_name.assert_called_once_with(
                mock_guild_config.guild_id, mock_current_user_unit, mock_db
            )

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


class TestSyncGuilds:
    """Test sync_guilds endpoint."""

    @pytest.mark.asyncio
    async def test_sync_guilds_success(self, mock_db, mock_current_user_unit):
        """Test successful guild sync using sync_all_bot_guilds."""
        # Create a real Request object for slowapi
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/guilds/sync",
            "headers": [(b"host", b"testserver")],
            "query_string": b"",
            "client": ("127.0.0.1", 8000),
        }
        mock_request = Request(scope)

        mock_discord_client = AsyncMock()

        # Mock database execute to return empty result (no existing guilds)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("services.api.routes.guilds.get_discord_client") as mock_get_client,
            patch("services.api.routes.guilds.get_api_config") as mock_get_config,
            patch("services.api.routes.guilds.sync_all_bot_guilds") as mock_sync,
        ):
            mock_get_client.return_value = mock_discord_client
            mock_config = MagicMock()
            mock_config.discord_bot_token = "test_bot_token"
            mock_get_config.return_value = mock_config

            mock_sync.return_value = {
                "new_guilds": 2,
                "new_channels": 10,
            }

            result = await guilds.sync_guilds(
                request=mock_request,
                _current_user=mock_current_user_unit,
                db=mock_db,
            )

            mock_sync.assert_called_once_with(mock_discord_client, mock_db, "test_bot_token")
            mock_db.commit.assert_called_once()
            assert result.new_guilds == 2
            assert result.new_channels == 10

    @pytest.mark.asyncio
    async def test_sync_guilds_limiter_configured(self):
        """Test that rate limiter decorator is configured on sync endpoint."""
        from inspect import getsource  # noqa: PLC0415

        from services.api.routes.guilds import sync_guilds  # noqa: PLC0415

        # Verify that the function has been wrapped by slowapi limiter
        # The limiter decorator should be present in the function's closure or wrapper
        source = getsource(sync_guilds)
        assert "@limiter.limit" in source or "limiter" in str(sync_guilds)

    @pytest.mark.asyncio
    async def test_sync_guilds_empty_results(self, mock_db, mock_current_user_unit):
        """Test sync endpoint when no new guilds or channels are found."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/guilds/sync",
            "headers": [(b"host", b"testserver")],
            "query_string": b"",
            "client": ("127.0.0.2", 8000),
        }
        mock_request = Request(scope)
        mock_discord_client = AsyncMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("services.api.routes.guilds.get_discord_client") as mock_get_client,
            patch("services.api.routes.guilds.get_api_config") as mock_get_config,
            patch("services.api.routes.guilds.sync_all_bot_guilds") as mock_sync,
        ):
            mock_get_client.return_value = mock_discord_client
            mock_config = MagicMock()
            mock_config.discord_bot_token = "test_bot_token"
            mock_get_config.return_value = mock_config

            mock_sync.return_value = {
                "new_guilds": 0,
                "new_channels": 0,
            }

            result = await guilds.sync_guilds(
                request=mock_request,
                _current_user=mock_current_user_unit,
                db=mock_db,
            )

            assert result.new_guilds == 0
            assert result.new_channels == 0
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_guilds_sync_failure(self, mock_db, mock_current_user_unit):
        """Test sync endpoint when sync_all_bot_guilds raises an exception."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/guilds/sync",
            "headers": [(b"host", b"testserver")],
            "query_string": b"",
            "client": ("127.0.0.3", 8000),
        }
        mock_request = Request(scope)
        mock_discord_client = AsyncMock()

        with (
            patch("services.api.routes.guilds.get_discord_client") as mock_get_client,
            patch("services.api.routes.guilds.get_api_config") as mock_get_config,
            patch("services.api.routes.guilds.sync_all_bot_guilds") as mock_sync,
        ):
            mock_get_client.return_value = mock_discord_client
            mock_config = MagicMock()
            mock_config.discord_bot_token = "test_bot_token"
            mock_get_config.return_value = mock_config

            mock_sync.side_effect = Exception("Discord API error")

            with pytest.raises(Exception) as exc_info:
                await guilds.sync_guilds(
                    request=mock_request,
                    _current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert str(exc_info.value) == "Discord API error"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_guilds_commit_failure(self, mock_db, mock_current_user_unit):
        """Test sync endpoint when database commit fails."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/guilds/sync",
            "headers": [(b"host", b"testserver")],
            "query_string": b"",
            "client": ("127.0.0.4", 8000),
        }
        mock_request = Request(scope)
        mock_discord_client = AsyncMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(side_effect=Exception("Database commit failed"))

        with (
            patch("services.api.routes.guilds.get_discord_client") as mock_get_client,
            patch("services.api.routes.guilds.get_api_config") as mock_get_config,
            patch("services.api.routes.guilds.sync_all_bot_guilds") as mock_sync,
        ):
            mock_get_client.return_value = mock_discord_client
            mock_config = MagicMock()
            mock_config.discord_bot_token = "test_bot_token"
            mock_get_config.return_value = mock_config

            mock_sync.return_value = {
                "new_guilds": 1,
                "new_channels": 5,
            }

            with pytest.raises(Exception) as exc_info:
                await guilds.sync_guilds(
                    request=mock_request,
                    _current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert str(exc_info.value) == "Database commit failed"
