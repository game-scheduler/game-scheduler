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

from datetime import datetime
from unittest.mock import AsyncMock, patch

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
    return auth_schemas.CurrentUser(
        discord_id="123456789",
        username="testuser",
        discriminator="0001",
        avatar="avatar_hash",
        access_token="test_access_token",
    )


@pytest.fixture
def mock_guild_config():
    """Create mock guild configuration."""
    config = AsyncMock()
    config.id = 1
    config.guild_id = "987654321"
    config.guild_name = "Test Guild"
    config.default_max_players = 10
    config.default_reminder_minutes = [60, 15]
    config.default_rules = "Be respectful"
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


class TestGetGuild:
    """Test get_guild endpoint."""

    @pytest.mark.asyncio
    async def test_get_guild_existing_config(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test retrieving existing guild configuration."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
            patch(
                "services.api.routes.guilds.config_service.ConfigurationService"
            ) as mock_service_class,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_discord_id="987654321",
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.guild_id == "987654321"
            assert result.guild_name == "Test Guild"
            assert result.default_max_players == 10
            assert result.default_reminder_minutes == [60, 15]
            mock_service.get_guild_by_discord_id.assert_called_once_with("987654321")

    @pytest.mark.asyncio
    async def test_get_guild_auto_creation(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test auto-creation of guild configuration on first access."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
            patch(
                "services.api.routes.guilds.config_service.ConfigurationService"
            ) as mock_service_class,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None
            mock_service.create_guild_config.return_value = mock_guild_config

            result = await guilds.get_guild(
                guild_discord_id="987654321",
                current_user=mock_current_user,
                db=mock_db,
            )

            mock_service.create_guild_config.assert_called_once_with(
                guild_discord_id="987654321",
                guild_name="Test Guild",
                default_max_players=10,
                default_reminder_minutes=[60, 15],
                default_rules=None,
                allowed_host_role_ids=[],
                require_host_role=False,
            )
            assert result.guild_id == "987654321"

    @pytest.mark.asyncio
    async def test_get_guild_rate_limit_error(self, mock_db, mock_current_user):
        """Test handling of Discord API rate limiting."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.side_effect = Exception(
                "Discord API error 429: You are being rate limited"
            )

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_discord_id="987654321",
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 503
            assert "Unable to verify guild membership" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_guild_not_member(self, mock_db, mock_current_user, mock_user_guilds):
        """Test error when user is not a member of the guild."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_discord_id="999999999",
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "not a member of this guild" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_guild_no_session(self, mock_db, mock_current_user):
        """Test error when user session is not found."""
        with patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens:
            mock_tokens.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await guilds.get_guild(
                    guild_discord_id="987654321",
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 401
            assert "No session found" in exc_info.value.detail


class TestListGuildChannels:
    """Test list_guild_channels endpoint."""

    @pytest.mark.asyncio
    async def test_list_channels_with_existing_guild(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test listing channels when guild configuration exists."""
        mock_channel = AsyncMock()
        mock_channel.id = 1
        mock_channel.guild_id = 1
        mock_channel.channel_id = "channel_123"
        mock_channel.channel_name = "game-events"
        mock_channel.is_active = True
        mock_channel.max_players = None
        mock_channel.reminder_minutes = None
        mock_channel.default_rules = None
        mock_channel.allowed_host_role_ids = None
        mock_channel.game_category = "RPG"
        mock_channel.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_channel.updated_at = datetime(2024, 1, 1, 12, 0, 0)

        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
            patch(
                "services.api.routes.guilds.config_service.ConfigurationService"
            ) as mock_service_class,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config
            mock_service.get_channels_by_guild.return_value = [mock_channel]

            result = await guilds.list_guild_channels(
                guild_discord_id="987654321",
                current_user=mock_current_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].channel_id == "channel_123"
            assert result[0].channel_name == "game-events"
            assert result[0].game_category == "RPG"

    @pytest.mark.asyncio
    async def test_list_channels_auto_create_guild(
        self, mock_db, mock_current_user, mock_guild_config, mock_user_guilds
    ):
        """Test auto-creation of guild configuration when listing channels."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
            patch(
                "services.api.routes.guilds.config_service.ConfigurationService"
            ) as mock_service_class,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None
            mock_service.create_guild_config.return_value = mock_guild_config
            mock_service.get_channels_by_guild.return_value = []

            result = await guilds.list_guild_channels(
                guild_discord_id="987654321",
                current_user=mock_current_user,
                db=mock_db,
            )

            mock_service.create_guild_config.assert_called_once()
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_channels_rate_limit_error(self, mock_db, mock_current_user):
        """Test handling of Discord API rate limiting when listing channels."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.side_effect = Exception("Rate limited")

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_discord_id="987654321",
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_list_channels_not_member(self, mock_db, mock_current_user, mock_user_guilds):
        """Test error when user is not a member of the guild."""
        with (
            patch("services.api.routes.guilds.tokens.get_user_tokens") as mock_tokens,
            patch("services.api.routes.guilds.oauth2.get_user_guilds") as mock_get_guilds,
        ):
            mock_tokens.return_value = {"access_token": "test_token"}
            mock_get_guilds.return_value = mock_user_guilds

            with pytest.raises(HTTPException) as exc_info:
                await guilds.list_guild_channels(
                    guild_discord_id="999999999",
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403


class TestCreateGuildConfig:
    """Test create_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_create_guild_success(self, mock_db, mock_current_user, mock_guild_config):
        """Test successful guild configuration creation."""
        create_request = guild_schemas.GuildConfigCreateRequest(
            guild_id="987654321",
            guild_name="Test Guild",
            default_max_players=10,
            default_reminder_minutes=[60, 15],
            default_rules="Be respectful",
            allowed_host_role_ids=["role_123"],
            require_host_role=False,
        )

        with patch(
            "services.api.routes.guilds.config_service.ConfigurationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None
            mock_service.create_guild_config.return_value = mock_guild_config

            result = await guilds.create_guild_config(
                request=create_request,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.guild_id == "987654321"
            mock_service.create_guild_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_guild_already_exists(self, mock_db, mock_current_user, mock_guild_config):
        """Test error when guild configuration already exists."""
        create_request = guild_schemas.GuildConfigCreateRequest(
            guild_id="987654321",
            guild_name="Test Guild",
            default_max_players=10,
            default_reminder_minutes=[60, 15],
            default_rules=None,
            allowed_host_role_ids=None,
        )

        with patch(
            "services.api.routes.guilds.config_service.ConfigurationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config

            with pytest.raises(HTTPException) as exc_info:
                await guilds.create_guild_config(
                    request=create_request,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 409
            assert "already exists" in exc_info.value.detail


class TestUpdateGuildConfig:
    """Test update_guild_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_guild_success(self, mock_db, mock_current_user, mock_guild_config):
        """Test successful guild configuration update."""
        update_request = guild_schemas.GuildConfigUpdateRequest(
            default_max_players=12,
            default_reminder_minutes=[120, 30, 5],
        )

        with patch(
            "services.api.routes.guilds.config_service.ConfigurationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = mock_guild_config
            mock_service.update_guild_config.return_value = mock_guild_config

            result = await guilds.update_guild_config(
                guild_discord_id="987654321",
                request=update_request,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.guild_id == "987654321"
            mock_service.update_guild_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_guild_not_found(self, mock_db, mock_current_user):
        """Test error when guild configuration doesn't exist."""
        update_request = guild_schemas.GuildConfigUpdateRequest(
            default_max_players=12,
        )

        with patch(
            "services.api.routes.guilds.config_service.ConfigurationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_guild_by_discord_id.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await guilds.update_guild_config(
                    guild_discord_id="987654321",
                    request=update_request,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail
