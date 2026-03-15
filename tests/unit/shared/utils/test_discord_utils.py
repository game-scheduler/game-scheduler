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


"""Tests for Discord utility functions."""

from shared.utils.discord import (
    DiscordPermissions,
    build_oauth_url,
    format_channel_mention,
    format_discord_timestamp,
    format_role_mention,
    format_user_mention,
    has_permission,
    parse_mention,
)


def test_format_discord_timestamp_default():
    """Test Discord timestamp formatting with default format."""
    timestamp = 1731700800
    result = format_discord_timestamp(timestamp)

    assert result == "<t:1731700800:F>"


def test_format_discord_timestamp_relative():
    """Test Discord timestamp formatting with relative format."""
    timestamp = 1731700800
    result = format_discord_timestamp(timestamp, "R")

    assert result == "<t:1731700800:R>"


def test_format_discord_timestamp_date():
    """Test Discord timestamp formatting with date format."""
    timestamp = 1731700800
    result = format_discord_timestamp(timestamp, "D")

    assert result == "<t:1731700800:D>"


def test_format_user_mention():
    """Test Discord user mention formatting."""
    user_id = "123456789012345678"
    result = format_user_mention(user_id)

    assert result == "<@123456789012345678>"


def test_format_channel_mention():
    """Test Discord channel mention formatting."""
    channel_id = "987654321098765432"
    result = format_channel_mention(channel_id)

    assert result == "<#987654321098765432>"


def test_format_role_mention():
    """Test Discord role mention formatting."""
    role_id = "555444333222111000"
    result = format_role_mention(role_id)

    assert result == "<@&555444333222111000>"


def test_parse_mention_valid():
    """Test parsing valid user mention."""
    mention = "<@123456789012345678>"
    result = parse_mention(mention)

    assert result == "123456789012345678"


def test_parse_mention_valid_with_exclamation():
    """Test parsing valid user mention with ! prefix (nickname format)."""
    mention = "<@!123456789012345678>"
    result = parse_mention(mention)

    assert result == "123456789012345678"


def test_parse_mention_invalid_format():
    """Test parsing invalid mention format."""
    mention = "123456789012345678"
    result = parse_mention(mention)

    assert result is None


def test_parse_mention_invalid_content():
    """Test parsing mention with non-numeric content."""
    mention = "<@notanumber>"
    result = parse_mention(mention)

    assert result is None


def test_has_permission_true():
    """Test permission check when permission is granted."""
    permissions = 0x00000028  # ADMINISTRATOR | MANAGE_GUILD
    result = has_permission(permissions, DiscordPermissions.MANAGE_GUILD)

    assert result is True


def test_has_permission_false():
    """Test permission check when permission is not granted."""
    permissions = 0x00000020  # Only MANAGE_GUILD
    result = has_permission(permissions, DiscordPermissions.ADMINISTRATOR)

    assert result is False


def test_has_permission_administrator():
    """Test ADMINISTRATOR permission check."""
    permissions = 0x00000008
    result = has_permission(permissions, DiscordPermissions.ADMINISTRATOR)

    assert result is True


def test_discord_permissions_constants():
    """Test Discord permission constant values."""
    assert DiscordPermissions.ADMINISTRATOR == 0x00000008
    assert DiscordPermissions.MANAGE_GUILD == 0x00000020
    assert DiscordPermissions.MANAGE_CHANNELS == 0x00000010
    assert DiscordPermissions.SEND_MESSAGES == 0x00000800


def test_build_oauth_url():
    """Test building Discord OAuth2 authorization URL."""
    client_id = "123456789"
    redirect_uri = "https://example.com/callback"
    scopes = ["identify", "guilds"]
    state = "random_state_token"

    result = build_oauth_url(client_id, redirect_uri, scopes, state)

    assert "https://discord.com/api/oauth2/authorize" in result
    assert "client_id=123456789" in result
    assert "redirect_uri=https://example.com/callback" in result
    assert "response_type=code" in result
    assert "scope=identify guilds" in result
    assert "state=random_state_token" in result


def test_build_oauth_url_single_scope():
    """Test building OAuth2 URL with single scope."""
    client_id = "123456789"
    redirect_uri = "https://example.com/callback"
    scopes = ["identify"]
    state = "state123"

    result = build_oauth_url(client_id, redirect_uri, scopes, state)

    assert "scope=identify" in result


def test_build_oauth_url_multiple_scopes():
    """Test building OAuth2 URL with multiple scopes."""
    client_id = "123456789"
    redirect_uri = "https://example.com/callback"
    scopes = ["identify", "guilds", "guilds.members.read"]
    state = "state123"

    result = build_oauth_url(client_id, redirect_uri, scopes, state)

    assert "scope=identify guilds guilds.members.read" in result
