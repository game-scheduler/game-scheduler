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


"""Unit tests for role verification service."""

from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import discord_client, roles
from services.api.auth.roles import DiscordPermissions


@pytest.fixture
def role_service():
    """Create role verification service instance."""
    return roles.RoleVerificationService()


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    cache = AsyncMock()
    cache.get_json = AsyncMock()
    cache.set_json = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def mock_discord_client():
    """Mock Discord API client."""
    client = AsyncMock()
    client.get_guild_member = AsyncMock()
    client.get_user_guilds = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_get_user_role_ids_from_cache(role_service, mock_cache):
    """Test retrieving user roles from cache."""
    mock_cache.get_json.return_value = ["role1", "role2"]

    with patch.object(role_service, "_get_cache", return_value=mock_cache):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == ["role1", "role2"]
    mock_cache.get_json.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_from_api(role_service, mock_cache, mock_discord_client):
    """Test retrieving user roles from Discord API when not cached."""
    mock_cache.get_json.return_value = None
    mock_discord_client.get_guild_member.return_value = {"roles": ["role1", "role2", "role3"]}

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == ["role1", "role2", "role3"]
    mock_cache.get_json.assert_called_once()
    mock_discord_client.get_guild_member.assert_called_once_with("guild456", "user123")
    mock_cache.set_json.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_force_refresh(role_service, mock_cache, mock_discord_client):
    """Test force refresh skips cache."""
    mock_discord_client.get_guild_member.return_value = {"roles": ["role1"]}

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456", force_refresh=True)

    assert role_ids == ["role1"]
    mock_cache.get_json.assert_not_called()
    mock_discord_client.get_guild_member.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_api_error(role_service, mock_cache, mock_discord_client):
    """Test handling Discord API error."""
    mock_cache.get_json.return_value = None
    mock_discord_client.get_guild_member.side_effect = discord_client.DiscordAPIError(
        404, "Not found"
    )

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == []


@pytest.mark.asyncio
async def test_check_game_host_permission_with_manage_guild(role_service):
    """Test game host permission with MANAGE_GUILD permission."""
    mock_db = AsyncMock()
    mock_access_token = "test_token"

    with patch.object(role_service, "has_permissions", return_value=True) as mock_has_permissions:
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            access_token=mock_access_token,
        )

    assert has_perm is True
    mock_has_permissions.assert_called_once_with(
        "user123", "guild456", mock_access_token, DiscordPermissions.MANAGE_GUILD
    )


@pytest.mark.asyncio
async def test_check_game_host_permission_without_token(role_service):
    """Test game host permission without access token returns False."""
    mock_db = AsyncMock()

    has_perm = await role_service.check_game_host_permission(
        "user123",
        "guild456",
        mock_db,
        access_token=None,
    )

    assert has_perm is False


@pytest.mark.asyncio
async def test_check_game_host_permission_no_permission(role_service):
    """Test game host permission without MANAGE_GUILD returns False."""
    mock_db = AsyncMock()
    mock_access_token = "test_token"

    with patch.object(role_service, "has_permissions", return_value=False) as mock_has_permissions:
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            access_token=mock_access_token,
        )

    assert has_perm is False
    mock_has_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_user_roles(role_service, mock_cache):
    """Test invalidating cached user roles."""
    with patch.object(role_service, "_get_cache", return_value=mock_cache):
        await role_service.invalidate_user_roles("user123", "guild456")

    mock_cache.delete.assert_called_once()


def test_get_role_service_singleton():
    """Test role service singleton pattern."""
    service1 = roles.get_role_service()
    service2 = roles.get_role_service()

    assert service1 is service2
