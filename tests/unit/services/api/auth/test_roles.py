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


"""Unit tests for role verification service."""

from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import roles
from shared.discord import client as discord_client
from shared.utils.discord import DiscordPermissions


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
    client.get_guilds = AsyncMock()
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

    assert role_ids == ["role1", "role2", "role3", "guild456"]
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

    assert role_ids == ["role1", "guild456"]
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

    with patch.object(
        role_service, "check_bot_manager_permission", return_value=True
    ) as mock_check_manager:
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            allowed_host_role_ids=["role1", "role2"],
            access_token=mock_access_token,
        )

    assert has_perm is True
    mock_check_manager.assert_called_once_with("user123", "guild456", mock_db, mock_access_token)


@pytest.mark.asyncio
async def test_check_game_host_permission_without_token(role_service):
    """Test game host permission without access token returns False."""
    mock_db = AsyncMock()

    with (
        patch.object(
            role_service, "check_bot_manager_permission", return_value=False
        ) as mock_check_manager,
        patch.object(role_service, "get_user_role_ids", return_value=["role2"]),
    ):
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            allowed_host_role_ids=["role1"],
            access_token=None,
        )

    assert has_perm is False
    mock_check_manager.assert_called_once()


@pytest.mark.asyncio
async def test_check_game_host_permission_no_permission(role_service):
    """Test game host permission without MANAGE_GUILD returns False."""
    mock_db = AsyncMock()
    mock_access_token = "test_token"

    with (
        patch.object(
            role_service, "check_bot_manager_permission", return_value=False
        ) as mock_check_manager,
        patch.object(role_service, "get_user_role_ids", return_value=["role2"]),
    ):
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            allowed_host_role_ids=["role1"],
            access_token=mock_access_token,
        )

    assert has_perm is False
    mock_check_manager.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_user_roles(role_service, mock_cache):
    """Test invalidating cached user roles."""
    with patch.object(role_service, "_get_cache", return_value=mock_cache):
        await role_service.invalidate_user_roles("user123", "guild456")

    mock_cache.delete.assert_called_once()


@pytest.mark.asyncio
async def test_has_any_role_user_has_role(role_service):
    """Test has_any_role returns True when user has at least one required role."""
    with patch.object(role_service, "get_user_role_ids", return_value=["role1", "role2", "role3"]):
        has_role = await role_service.has_any_role("user123", "guild456", ["role2", "role4"])

    assert has_role is True


@pytest.mark.asyncio
async def test_has_any_role_user_missing_roles(role_service):
    """Test has_any_role returns False when user has none of the required roles."""
    with patch.object(role_service, "get_user_role_ids", return_value=["role1", "role2"]):
        has_role = await role_service.has_any_role("user123", "guild456", ["role3", "role4"])

    assert has_role is False


@pytest.mark.asyncio
async def test_has_any_role_empty_role_list(role_service):
    """Test has_any_role returns False when given empty role list."""
    has_role = await role_service.has_any_role("user123", "guild456", [])

    assert has_role is False


@pytest.mark.asyncio
async def test_has_any_role_with_everyone_role(role_service):
    """Test has_any_role matches @everyone role (guild_id)."""
    with patch.object(role_service, "get_user_role_ids", return_value=["guild456", "role1"]):
        has_role = await role_service.has_any_role("user123", "guild456", ["guild456"])

    assert has_role is True


@pytest.mark.asyncio
async def test_has_any_role_multiple_matches(role_service):
    """Test has_any_role returns True when user has multiple matching roles."""
    with patch.object(role_service, "get_user_role_ids", return_value=["role1", "role2", "role3"]):
        has_role = await role_service.has_any_role("user123", "guild456", ["role1", "role2"])

    assert has_role is True


class TestHasPermissionsHelpers:
    """Unit tests for has_permissions extracted helper methods."""

    def test_find_guild_data_found(self, role_service):
        """Test _find_guild_data returns guild when found."""
        guilds = [
            {"id": "guild1", "name": "Guild 1"},
            {"id": "guild2", "name": "Guild 2"},
            {"id": "guild3", "name": "Guild 3"},
        ]

        result = role_service._find_guild_data(guilds, "guild2")

        assert result == {"id": "guild2", "name": "Guild 2"}

    def test_find_guild_data_not_found(self, role_service):
        """Test _find_guild_data returns None when guild not found."""
        guilds = [
            {"id": "guild1", "name": "Guild 1"},
            {"id": "guild2", "name": "Guild 2"},
        ]

        result = role_service._find_guild_data(guilds, "guild999")

        assert result is None

    def test_find_guild_data_empty_list(self, role_service):
        """Test _find_guild_data returns None for empty guild list."""
        result = role_service._find_guild_data([], "guild1")

        assert result is None

    def test_has_administrator_permission_true(self, role_service):
        """Test _has_administrator_permission returns True for admin."""
        permissions = DiscordPermissions.ADMINISTRATOR

        result = role_service._has_administrator_permission(permissions)

        assert result is True

    def test_has_administrator_permission_with_other_permissions(self, role_service):
        """Test _has_administrator_permission with combined permissions."""
        permissions = DiscordPermissions.ADMINISTRATOR | DiscordPermissions.MANAGE_GUILD

        result = role_service._has_administrator_permission(permissions)

        assert result is True

    def test_has_administrator_permission_false(self, role_service):
        """Test _has_administrator_permission returns False without admin."""
        permissions = DiscordPermissions.MANAGE_GUILD | DiscordPermissions.MANAGE_CHANNELS

        result = role_service._has_administrator_permission(permissions)

        assert result is False

    def test_has_administrator_permission_zero(self, role_service):
        """Test _has_administrator_permission returns False for zero permissions."""
        result = role_service._has_administrator_permission(0)

        assert result is False

    def test_has_any_requested_permission_single_match(self, role_service):
        """Test _has_any_requested_permission with single matching permission."""
        user_permissions = DiscordPermissions.MANAGE_GUILD
        requested_permissions = (DiscordPermissions.MANAGE_GUILD,)

        result = role_service._has_any_requested_permission(user_permissions, requested_permissions)

        assert result is True

    def test_has_any_requested_permission_multiple_match(self, role_service):
        """Test _has_any_requested_permission with multiple matching permissions."""
        user_permissions = (
            DiscordPermissions.MANAGE_GUILD
            | DiscordPermissions.MANAGE_CHANNELS
            | DiscordPermissions.MANAGE_ROLES
        )
        requested_permissions = (
            DiscordPermissions.MANAGE_GUILD,
            DiscordPermissions.MANAGE_ROLES,
        )

        result = role_service._has_any_requested_permission(user_permissions, requested_permissions)

        assert result is True

    def test_has_any_requested_permission_no_match(self, role_service):
        """Test _has_any_requested_permission with no matching permissions."""
        user_permissions = DiscordPermissions.SEND_MESSAGES | DiscordPermissions.ADD_REACTIONS
        requested_permissions = (
            DiscordPermissions.MANAGE_GUILD,
            DiscordPermissions.MANAGE_ROLES,
        )

        result = role_service._has_any_requested_permission(user_permissions, requested_permissions)

        assert result is False

    def test_has_any_requested_permission_empty_requested(self, role_service):
        """Test _has_any_requested_permission with empty permissions tuple."""
        user_permissions = DiscordPermissions.MANAGE_GUILD

        result = role_service._has_any_requested_permission(user_permissions, ())

        assert result is False

    def test_has_any_requested_permission_zero_user_permissions(self, role_service):
        """Test _has_any_requested_permission with zero user permissions."""
        requested_permissions = (DiscordPermissions.MANAGE_GUILD,)

        result = role_service._has_any_requested_permission(0, requested_permissions)

        assert result is False


def test_get_role_service_singleton():
    """Test role service singleton pattern."""
    service1 = roles.get_role_service()
    service2 = roles.get_role_service()

    assert service1 is service2
