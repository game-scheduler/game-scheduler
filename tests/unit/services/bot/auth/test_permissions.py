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
