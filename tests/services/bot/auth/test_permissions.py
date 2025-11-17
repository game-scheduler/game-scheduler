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


"""Unit tests for Discord permission utilities."""

from services.bot.auth.permissions import (
    DiscordPermissions,
    has_all_permissions,
    has_any_permission,
    has_permission,
)


def test_has_permission_with_single_permission():
    """Test checking single permission in bitfield."""
    permissions = DiscordPermissions.MANAGE_GUILD.value
    assert has_permission(permissions, DiscordPermissions.MANAGE_GUILD)


def test_has_permission_without_permission():
    """Test checking permission not in bitfield."""
    permissions = DiscordPermissions.MANAGE_GUILD.value
    assert not has_permission(permissions, DiscordPermissions.ADMINISTRATOR)


def test_has_permission_with_multiple_permissions():
    """Test checking permission with multiple flags set."""
    permissions = DiscordPermissions.MANAGE_GUILD.value | DiscordPermissions.MANAGE_CHANNELS.value
    assert has_permission(permissions, DiscordPermissions.MANAGE_GUILD)
    assert has_permission(permissions, DiscordPermissions.MANAGE_CHANNELS)


def test_has_permission_administrator():
    """Test checking ADMINISTRATOR permission."""
    permissions = DiscordPermissions.ADMINISTRATOR.value
    assert has_permission(permissions, DiscordPermissions.ADMINISTRATOR)


def test_has_any_permission_with_match():
    """Test checking any of multiple permissions with match."""
    permissions = DiscordPermissions.MANAGE_GUILD.value
    assert has_any_permission(
        permissions,
        DiscordPermissions.MANAGE_GUILD,
        DiscordPermissions.ADMINISTRATOR,
    )


def test_has_any_permission_without_match():
    """Test checking any of multiple permissions without match."""
    permissions = DiscordPermissions.SEND_MESSAGES.value
    assert not has_any_permission(
        permissions,
        DiscordPermissions.MANAGE_GUILD,
        DiscordPermissions.ADMINISTRATOR,
    )


def test_has_any_permission_multiple_matches():
    """Test checking any of multiple permissions with multiple matches."""
    permissions = DiscordPermissions.MANAGE_GUILD.value | DiscordPermissions.ADMINISTRATOR.value
    assert has_any_permission(
        permissions,
        DiscordPermissions.MANAGE_GUILD,
        DiscordPermissions.ADMINISTRATOR,
    )


def test_has_all_permissions_with_all():
    """Test checking all permissions when all present."""
    permissions = DiscordPermissions.MANAGE_GUILD.value | DiscordPermissions.MANAGE_CHANNELS.value
    assert has_all_permissions(
        permissions,
        DiscordPermissions.MANAGE_GUILD,
        DiscordPermissions.MANAGE_CHANNELS,
    )


def test_has_all_permissions_without_all():
    """Test checking all permissions when some missing."""
    permissions = DiscordPermissions.MANAGE_GUILD.value
    assert not has_all_permissions(
        permissions,
        DiscordPermissions.MANAGE_GUILD,
        DiscordPermissions.ADMINISTRATOR,
    )


def test_permission_bitfield_values():
    """Test that permission values match Discord specification."""
    assert DiscordPermissions.ADMINISTRATOR.value == 1 << 3
    assert DiscordPermissions.MANAGE_GUILD.value == 1 << 5
    assert DiscordPermissions.MANAGE_CHANNELS.value == 1 << 4
    assert DiscordPermissions.SEND_MESSAGES.value == 1 << 11
