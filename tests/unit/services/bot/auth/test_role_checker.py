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


"""Unit tests for role checker service."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.auth.role_checker import RoleChecker


@pytest.fixture
def mock_bot():
    """Create mock Discord bot client."""
    return MagicMock(spec=discord.Client)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def role_checker(mock_bot, mock_db):
    """Create RoleChecker with mocks."""
    return RoleChecker(mock_bot, mock_db)


@pytest.mark.asyncio
async def test_get_user_role_ids_from_cache(role_checker):
    """Test getting user role IDs from cache."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=["123", "456"])

    result = await role_checker.get_user_role_ids("user123", "guild456")

    assert result == ["123", "456"]
    role_checker.cache.get_user_roles.assert_called_once_with("user123", "guild456")


@pytest.mark.asyncio
async def test_get_user_role_ids_from_discord(role_checker, mock_bot):
    """Test getting user role IDs from Discord API."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=None)

    # Mock guild and member
    mock_guild = MagicMock()
    mock_guild.id = 456

    mock_role1 = MagicMock()
    mock_role1.id = 123

    mock_role2 = MagicMock()
    mock_role2.id = 789

    mock_member = AsyncMock()
    mock_member.roles = [mock_role1, mock_role2]

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    role_checker.cache.set_user_roles = AsyncMock()

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == ["123", "789"]
    role_checker.cache.set_user_roles.assert_called_once_with("123", "456", ["123", "789"])


@pytest.mark.asyncio
async def test_get_user_role_ids_guild_not_found(role_checker, mock_bot):
    """Test handling guild not found."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=None)
    mock_bot.fetch_guild = AsyncMock(return_value=None)

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == []


@pytest.mark.asyncio
async def test_get_user_role_ids_member_not_found(role_checker, mock_bot):
    """Test handling member not found."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=None)

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), ""))
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == []


@pytest.mark.asyncio
async def test_get_user_role_ids_force_refresh(role_checker, mock_bot):
    """Test forcing refresh bypasses cache."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=["cached"])

    mock_guild = MagicMock()
    mock_guild.id = 456

    mock_role1 = MagicMock()
    mock_role1.id = 123

    mock_member = AsyncMock()
    mock_member.roles = [mock_role1]

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    role_checker.cache.set_user_roles = AsyncMock()

    result = await role_checker.get_user_role_ids("123", "456", force_refresh=True)

    assert result == ["123"]
    role_checker.cache.get_user_roles.assert_not_called()


@pytest.mark.asyncio
async def test_check_manage_guild_permission_true(role_checker, mock_bot):
    """Test user has MANAGE_GUILD permission."""
    mock_guild = MagicMock()

    mock_permissions = MagicMock()
    mock_permissions.manage_guild = True

    mock_member = AsyncMock()
    mock_member.guild_permissions = mock_permissions

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.check_manage_guild_permission("123", "456")

    assert result is True


@pytest.mark.asyncio
async def test_check_manage_guild_permission_false(role_checker, mock_bot):
    """Test user lacks MANAGE_GUILD permission."""
    mock_guild = MagicMock()

    mock_permissions = MagicMock()
    mock_permissions.manage_guild = False

    mock_member = AsyncMock()
    mock_member.guild_permissions = mock_permissions

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.check_manage_guild_permission("123", "456")

    assert result is False


@pytest.mark.asyncio
async def test_check_manage_channels_permission_true(role_checker, mock_bot):
    """Test user has MANAGE_CHANNELS permission."""
    mock_guild = MagicMock()

    mock_permissions = MagicMock()
    mock_permissions.manage_channels = True

    mock_member = AsyncMock()
    mock_member.guild_permissions = mock_permissions

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.check_manage_channels_permission("123", "456")

    assert result is True


@pytest.mark.asyncio
async def test_check_administrator_permission_true(role_checker, mock_bot):
    """Test user has ADMINISTRATOR permission."""
    mock_guild = MagicMock()

    mock_permissions = MagicMock()
    mock_permissions.administrator = True

    mock_member = AsyncMock()
    mock_member.guild_permissions = mock_permissions

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.check_administrator_permission("123", "456")

    assert result is True


@pytest.mark.asyncio
async def test_check_game_host_permission_with_manage_guild(role_checker, mock_db):
    """Test game host permission with MANAGE_GUILD permission."""
    role_checker.check_manage_guild_permission = AsyncMock(return_value=True)

    result = await role_checker.check_game_host_permission("user123", "guild456", "789")

    assert result is True
    role_checker.check_manage_guild_permission.assert_called_once_with("user123", "guild456")


@pytest.mark.asyncio
async def test_check_game_host_permission_without_manage_guild(role_checker, mock_db):
    """Test game host permission without MANAGE_GUILD permission."""
    role_checker.check_manage_guild_permission = AsyncMock(return_value=False)

    result = await role_checker.check_game_host_permission("user123", "456", "789")

    assert result is False
    role_checker.check_manage_guild_permission.assert_called_once_with("user123", "456")


@pytest.mark.asyncio
async def test_check_game_host_permission_fallback_to_manage_guild(role_checker, mock_db):
    """Test game host permission falls back to MANAGE_GUILD."""

    role_checker.check_manage_guild_permission = AsyncMock(return_value=True)

    result = await role_checker.check_game_host_permission("user123", "guild456", "789")

    assert result is True
    role_checker.check_manage_guild_permission.assert_called_once_with("user123", "guild456")


@pytest.mark.asyncio
async def test_invalidate_user_roles(role_checker):
    """Test invalidating cached user roles."""
    role_checker.cache.invalidate_user_roles = AsyncMock()

    await role_checker.invalidate_user_roles("user123", "guild456")

    role_checker.cache.invalidate_user_roles.assert_called_once_with("user123", "guild456")


@pytest.mark.asyncio
async def test_get_guild_roles(role_checker, mock_bot):
    """Test getting guild roles."""
    mock_role1 = MagicMock()
    mock_role1.id = 123
    mock_role1.name = "Admin"

    mock_role2 = MagicMock()
    mock_role2.id = 456
    mock_role2.name = "Member"

    mock_guild = MagicMock()
    mock_guild.roles = [mock_role1, mock_role2]

    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

    result = await role_checker.get_guild_roles("456")

    assert len(result) == 2
    assert result[0].id == 123
    assert result[1].id == 456
