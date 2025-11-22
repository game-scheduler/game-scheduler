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


"""Unit tests for guild configuration endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.api.routes import guilds
from shared.schemas import auth as auth_schemas
from shared.schemas import guild as guild_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    mock_user = MagicMock()
    mock_user.discord_id = "123456789"
    return auth_schemas.CurrentUser(
        user=mock_user,
        access_token="test_access_token",
        session_token="test-session-token",
    )


@pytest.fixture
def mock_guild_config():
    """Create mock guild configuration."""
    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.guild_id = "987654321"
    config.default_max_players = 10
    config.default_reminder_minutes = [60, 15]
    config.allowed_host_role_ids = ["role_123"]
    config.require_host_role = False
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
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test listing guilds with configurations."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config

            result = await guilds.list_guilds(current_user=mock_current_user, db=mock_db)

            assert len(result.guilds) == 2
            assert result.guilds[0].guild_id == "987654321"
            assert result.guilds[0].guild_name == "Test Guild"

    @pytest.mark.asyncio
    async def test_list_guilds_no_configs(self, mock_db, mock_current_user, mock_user_guilds):
        """Test listing guilds when no configurations exist."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None

            result = await guilds.list_guilds(current_user=mock_current_user, db=mock_db)

            assert len(result.guilds) == 0


class TestGetGuild:
    """Test get_guild endpoint."""

    @pytest.mark.asyncio
    async def test_get_guild_success(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild configuration by UUID."""
        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.guild_id == "987654321"
            assert result.guild_name == "Test Guild"
            assert result.default_max_players == 10

    @pytest.mark.asyncio
    async def test_get_guild_not_found(self, mock_db, mock_current_user):
        """Test retrieving non-existent guild configuration."""
        with patch("services.api.services.config.ConfigurationService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=str(uuid.uuid4()),
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_guild_not_member(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving guild where user is not a member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_guild_no_session(self, mock_db, mock_current_user, mock_guild_config):
        """Test retrieving guild when session is not found."""
        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_tokens.return_value = None

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 401


class TestCreateGuildConfig:
    """Test create_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_create_guild_success(self, mock_db, mock_current_user, mock_user_guilds):
        """Test creating new guild configuration."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None

            new_config = MagicMock()
            new_config.id = str(uuid.uuid4())
            new_config.guild_id = "987654321"
            new_config.default_max_players = 12
            new_config.default_reminder_minutes = [60, 15]
            new_config.allowed_host_role_ids = []
            new_config.require_host_role = False
            new_config.created_at = datetime.now()
            new_config.updated_at = datetime.now()

            mock_service.create_guild_config.return_value = new_config

            request = guild_schemas.GuildConfigCreateRequest(
                guild_id="987654321",
                default_max_players=12,
                default_reminder_minutes=[60, 15],
                allowed_host_role_ids=[],
                require_host_role=False,
            )

            result = await guilds.create_guild_config(
                request=request,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.guild_id == "987654321"
            assert result.default_max_players == 12
            mock_service.create_guild_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_guild_already_exists(self, mock_db, mock_current_user, mock_guild_config):
        """Test creating guild configuration that already exists."""
        with patch("services.api.services.config.ConfigurationService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config

            request = guild_schemas.GuildConfigCreateRequest(
                guild_id="987654321",
                default_max_players=12,
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.create_guild_config(
                    request=request,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 409


class TestUpdateGuildConfig:
    """Test update_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_guild_success(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test updating guild configuration."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config

            updated_config = MagicMock()
            updated_config.id = mock_guild_config.id
            updated_config.guild_id = "987654321"
            updated_config.default_max_players = 15
            updated_config.default_reminder_minutes = [60, 15]
            updated_config.allowed_host_role_ids = ["role_123"]
            updated_config.require_host_role = False
            updated_config.created_at = datetime.now()
            updated_config.updated_at = datetime.now()

            mock_service.update_guild_config.return_value = updated_config

            request = guild_schemas.GuildConfigUpdateRequest(
                default_max_players=15,
            )

            result = await guilds.update_guild_config(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.default_max_players == 15
            mock_service.update_guild_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_guild_not_found(self, mock_db, mock_current_user):
        """Test updating non-existent guild configuration."""
        with patch("services.api.services.config.ConfigurationService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = None

            request = guild_schemas.GuildConfigUpdateRequest(
                default_max_players=15,
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.update_guild_config(
                    guild_id=str(uuid.uuid4()),
                    request=request,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestListGuildChannels:
    """Test list_guild_channels endpoint."""

    @pytest.mark.asyncio
    async def test_list_channels_success(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels for a guild."""
        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_channel = MagicMock()
            mock_channel.id = str(uuid.uuid4())
            mock_channel.guild_id = mock_guild_config.id
            mock_channel.channel_id = "channel_123"
            mock_channel.channel_name = "Test Channel"
            mock_channel.is_active = True
            mock_channel.max_players = None
            mock_channel.reminder_minutes = None
            mock_channel.allowed_host_role_ids = None
            mock_channel.game_category = None
            mock_channel.created_at = datetime.now()
            mock_channel.updated_at = datetime.now()

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config
            mock_service.get_channels_by_guild.return_value = [mock_channel]

            result = await guilds.list_guild_channels(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].channel_id == "channel_123"
            assert result[0].channel_name == "Test Channel"

    @pytest.mark.asyncio
    async def test_list_channels_guild_not_found(self, mock_db, mock_current_user):
        """Test listing channels for non-existent guild."""
        with patch("services.api.services.config.ConfigurationService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_id=str(uuid.uuid4()),
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_channels_not_member(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels when user is not guild member."""
        # Set guild_id to one not in mock_user_guilds
        mock_guild_config.guild_id = "999999999"

        with (
            patch("services.api.auth.tokens.get_user_tokens") as mock_get_tokens,
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
            patch("services.api.services.config.ConfigurationService") as mock_service_class,
        ):
            mock_get_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_id.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_id=mock_guild_config.id,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
