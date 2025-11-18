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


"""Unit tests for permission check dependencies."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from services.api.auth import roles as roles_module
from services.api.dependencies import permissions
from shared.schemas import auth as auth_schemas


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    return auth_schemas.CurrentUser(discord_id="user123", access_token="test_token")


@pytest.fixture
def mock_role_service():
    """Create mock role verification service."""
    service = AsyncMock()
    service.check_manage_guild_permission = AsyncMock()
    service.check_manage_channels_permission = AsyncMock()
    service.check_administrator_permission = AsyncMock()
    service.check_game_host_permission = AsyncMock()
    return service


@pytest.fixture
def mock_tokens():
    """Mock token functions."""
    return {
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_at": 9999999999,
    }


@pytest.mark.asyncio
async def test_get_role_service():
    """Test getting role service."""
    service = await permissions.get_role_service()
    assert isinstance(service, roles_module.RoleVerificationService)


@pytest.mark.asyncio
async def test_require_manage_guild_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_manage_guild with permission."""
    mock_role_service.check_manage_guild_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_manage_guild(
            "guild456",
            mock_current_user,
            mock_role_service,
        )

    assert result == mock_current_user
    mock_role_service.check_manage_guild_permission.assert_called_once()


@pytest.mark.asyncio
async def test_require_manage_guild_no_session(mock_current_user, mock_role_service):
    """Test require_manage_guild with no session."""
    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_guild(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_manage_guild_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_manage_guild without permission."""
    mock_role_service.check_manage_guild_permission.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_guild(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 403
    assert "MANAGE_GUILD" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_manage_channels_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_manage_channels with permission."""
    mock_role_service.check_manage_channels_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_manage_channels(
            "guild456",
            mock_current_user,
            mock_role_service,
        )

    assert result == mock_current_user
    mock_role_service.check_manage_channels_permission.assert_called_once()


@pytest.mark.asyncio
async def test_require_manage_channels_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_manage_channels without permission."""
    mock_role_service.check_manage_channels_permission.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_channels(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 403
    assert "MANAGE_CHANNELS" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_game_host_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host with permission."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_game_host(
            "guild456",
            "channel789",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.check_game_host_permission.assert_called_once_with(
        "user123",
        "guild456",
        mock_db,
        channel_id="channel789",
        access_token="test_token",
    )


@pytest.mark.asyncio
async def test_require_game_host_no_permission(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host without permission."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_game_host(
                "guild456",
                "channel789",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "host games" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_game_host_no_channel(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host without channel ID."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_game_host(
            "guild456",
            None,
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.check_game_host_permission.assert_called_once_with(
        "user123",
        "guild456",
        mock_db,
        channel_id=None,
        access_token="test_token",
    )


@pytest.mark.asyncio
async def test_require_administrator_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_administrator with permission."""
    mock_role_service.check_administrator_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_administrator(
            "guild456",
            mock_current_user,
            mock_role_service,
        )

    assert result == mock_current_user
    mock_role_service.check_administrator_permission.assert_called_once()


@pytest.mark.asyncio
async def test_require_administrator_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_administrator without permission."""
    mock_role_service.check_administrator_permission.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_administrator(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 403
    assert "ADMINISTRATOR" in exc_info.value.detail
