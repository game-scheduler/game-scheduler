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


"""Unit tests for role checker service."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.auth.role_checker import RoleChecker
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


@pytest.fixture
def mock_bot():
    """Create mock Discord bot client."""
    bot = MagicMock(spec=discord.Client)
    return bot


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


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
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    role_checker.cache.set_user_roles = AsyncMock()

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == ["123", "789"]
    role_checker.cache.set_user_roles.assert_called_once_with("123", "456", ["123", "789"])


@pytest.mark.asyncio
async def test_get_user_role_ids_guild_not_found(role_checker, mock_bot):
    """Test handling guild not found."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=None)
    mock_bot.get_guild = MagicMock(return_value=None)

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == []


@pytest.mark.asyncio
async def test_get_user_role_ids_member_not_found(role_checker, mock_bot):
    """Test handling member not found."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=None)

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), ""))
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    result = await role_checker.get_user_role_ids("123", "456")

    assert result == []


@pytest.mark.asyncio
async def test_get_user_role_ids_force_refresh(role_checker, mock_bot):
    """Test forcing refresh bypasses cache."""
    role_checker.cache.get_user_roles = AsyncMock(return_value=["old_role"])

    mock_guild = MagicMock()
    mock_guild.id = 456

    mock_role = MagicMock()
    mock_role.id = 789

    mock_member = AsyncMock()
    mock_member.roles = [mock_role]

    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    role_checker.cache.set_user_roles = AsyncMock()

    result = await role_checker.get_user_role_ids("123", "456", force_refresh=True)

    assert result == ["789"]
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
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

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
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

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
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

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
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    result = await role_checker.check_administrator_permission("123", "456")

    assert result is True


@pytest.mark.asyncio
async def test_check_game_host_permission_with_channel_roles(role_checker, mock_db):
    """Test game host permission with channel-specific allowed roles."""
    role_checker.get_user_role_ids = AsyncMock(return_value=["role123", "role456"])

    # Mock channel config with allowed roles
    channel_config = ChannelConfiguration(
        id="ch1",
        guild_id="g1",
        channel_id="789",
        channel_name="test",
        allowed_host_role_ids=["role123"],
    )

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=channel_config)
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await role_checker.check_game_host_permission("user123", "guild456", "789")

    assert result is True


@pytest.mark.asyncio
async def test_check_game_host_permission_with_guild_roles(role_checker, mock_db):
    """Test game host permission with guild allowed roles."""
    role_checker.get_user_role_ids = AsyncMock(return_value=["role123", "role456"])

    # Mock no channel config
    mock_channel_result = AsyncMock()
    mock_channel_result.scalar_one_or_none = MagicMock(return_value=None)

    # Mock guild config with allowed roles
    guild_config = GuildConfiguration(
        id="g1",
        guild_id="456",
        guild_name="test",
        allowed_host_role_ids=["role456"],
    )

    mock_guild_result = AsyncMock()
    mock_guild_result.scalar_one_or_none = MagicMock(return_value=guild_config)

    mock_db.execute = AsyncMock(side_effect=[mock_channel_result, mock_guild_result])

    result = await role_checker.check_game_host_permission("user123", "456", "789")

    assert result is True


@pytest.mark.asyncio
async def test_check_game_host_permission_fallback_to_manage_guild(role_checker, mock_db):
    """Test game host permission falls back to MANAGE_GUILD."""
    role_checker.get_user_role_ids = AsyncMock(return_value=["role123"])

    # Mock no configs
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    role_checker.check_manage_guild_permission = AsyncMock(return_value=True)

    result = await role_checker.check_game_host_permission("user123", "guild456", "789")

    assert result is True
    role_checker.check_manage_guild_permission.assert_called_once_with("user123", "guild456")


@pytest.mark.asyncio
async def test_check_game_host_permission_no_match(role_checker, mock_db):
    """Test game host permission with no matching roles."""
    role_checker.get_user_role_ids = AsyncMock(return_value=["role999"])

    # Mock guild config with different allowed roles
    guild_config = GuildConfiguration(
        id="g1",
        guild_id="456",
        guild_name="test",
        allowed_host_role_ids=["role123", "role456"],
    )

    mock_guild_result = AsyncMock()
    mock_guild_result.scalar_one_or_none = MagicMock(return_value=guild_config)

    mock_channel_result = AsyncMock()
    mock_channel_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(side_effect=[mock_channel_result, mock_guild_result])

    result = await role_checker.check_game_host_permission("user123", "456", "789")

    assert result is False


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

    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    result = await role_checker.get_guild_roles("456")

    assert len(result) == 2
    assert result[0].id == 123
    assert result[1].id == 456
