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


"""Unit tests for channel resolver service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.services import channel_resolver as resolver_module
from shared.discord import client as discord_client_module


@pytest.fixture
def mock_discord_client():
    """Create mock Discord API client."""
    client = MagicMock(spec=discord_client_module.DiscordAPIClient)
    client.bot_token = "test_bot_token"
    return client


@pytest.fixture
def resolver(mock_discord_client):
    """Create channel resolver instance."""
    return resolver_module.ChannelResolver(mock_discord_client)


@pytest.mark.asyncio
async def test_resolve_single_channel_match(resolver, mock_discord_client):
    """Test #channel mention with single channel match."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
            {"id": "987654321", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_multiple_channel_matches(resolver, mock_discord_client):
    """Test #channel mention with multiple matching channels (disambiguation needed)."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "General", "type": 0},
            {"id": "333333333", "name": "GENERAL", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #general"
    assert len(errors) == 1
    assert errors[0]["type"] == "ambiguous"
    assert errors[0]["input"] == "#general"
    assert len(errors[0]["suggestions"]) == 3
    assert any(s["name"] == "general" for s in errors[0]["suggestions"])


@pytest.mark.asyncio
async def test_resolve_channel_not_found(resolver, mock_discord_client):
    """Test #channel mention when channel doesn't exist."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
            {"id": "987654321", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #nonexistent",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #nonexistent"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#nonexistent"
    assert "suggestions" in errors[0]


@pytest.mark.asyncio
async def test_resolve_channel_with_special_characters(resolver, mock_discord_client):
    """Test #channel mention with hyphens and underscores."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "game-planning", "type": 0},
            {"id": "987654321", "name": "off_topic", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #game-planning",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_mixed_content_with_channel(resolver, mock_discord_client):
    """Test location text with plain text and channel mention."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "voice-lobby", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Join #voice-lobby at 7pm EST",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Join <#123456789> at 7pm EST"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_empty_location_text(resolver, mock_discord_client):
    """Test empty location text returns unchanged."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="",
        guild_discord_id="guild123",
    )

    assert resolved_text == ""
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_plain_text_without_mentions(resolver, mock_discord_client):
    """Test plain text without channel mentions returns unchanged."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet at Discord voice channel 2",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet at Discord voice channel 2"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_multiple_mentions_in_one_location(resolver, mock_discord_client):
    """Test multiple #channel mentions in single location string."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "voice-lobby", "type": 0},
            {"id": "333333333", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Start in #general then move to #voice-lobby",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Start in <#111111111> then move to <#222222222>"


# ---------------------------------------------------------------------------
# Discord channel URL detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_discord_url_same_guild(resolver, mock_discord_client):
    """Valid same-guild discord.com channel URL is replaced with <#channel_id>."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/406583674453098496",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "<#406583674453098496>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_wrong_guild_passes_through(resolver, mock_discord_client):
    """discord.com URL from a different guild is left unchanged with no error."""
    url = "https://discord.com/channels/999999999999999999/406583674453098496"
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=url,
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == url
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_channel_not_found(resolver, mock_discord_client):
    """Same-guild discord.com URL for a non-existent text channel returns not_found error."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/999999999999999999",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "https://discord.com/channels/111222333444555666/999999999999999999"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert (
        errors[0]["input"] == "https://discord.com/channels/111222333444555666/999999999999999999"
    )
    assert errors[0]["reason"] == "This link is not a valid text channel in this server"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_discord_url_non_text_channel_not_found(resolver, mock_discord_client):
    """Same-guild discord.com URL for a non-text channel (type != 0) returns not_found."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
            {"id": "777777777777777777", "name": "voice-chat", "type": 2},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/777777777777777777",
        guild_discord_id="111222333444555666",
    )

    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_discord_url_coexisting_with_hash_mention(resolver, mock_discord_client):
    """discord.com URL and a #channel mention in the same string both resolve correctly."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "406583674453098496", "name": "voice-lobby", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=(
            "Start at #general then https://discord.com/channels/GUILD/406583674453098496"
        ).replace("GUILD", "999999999999999999"),
        guild_discord_id="999999999999999999",
    )

    assert resolved_text == "Start at <#111111111> then <#406583674453098496>"
    assert len(errors) == 0
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_channel_at_text_start(resolver, mock_discord_client):
    """Test #channel mention at start of location text."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="#general at 7pm",
        guild_discord_id="guild123",
    )

    assert resolved_text == "<#123456789> at 7pm"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_channel_at_text_end(resolver, mock_discord_client):
    """Test #channel mention at end of location text."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet at #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet at <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_adjacent_channel_mentions(resolver, mock_discord_client):
    """Test adjacent #channel mentions without separator."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="#general #announcements",
        guild_discord_id="guild123",
    )

    assert resolved_text == "<#111111111> <#222222222>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_with_empty_guild_channel_list(resolver, mock_discord_client):
    """Test handling when guild has no channels."""
    mock_discord_client.get_guild_channels = AsyncMock(return_value=[])

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #general"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#general"
    assert len(errors[0]["suggestions"]) == 0


@pytest.mark.asyncio
async def test_resolve_filters_non_text_channels(resolver, mock_discord_client):
    """Test that only text channels (type=0) are considered."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "General Voice", "type": 2},
            {"id": "333333333", "name": "general-category", "type": 4},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_case_insensitive_matching(resolver, mock_discord_client):
    """Test case-insensitive channel name matching."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "General", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #GENERAL",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_mixed_valid_and_invalid_channels(resolver, mock_discord_client):
    """Test location with both valid and invalid channel mentions."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Start in #general then #nonexistent",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Start in <#123456789> then #nonexistent"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#nonexistent"


# ---------------------------------------------------------------------------
# Bug fix regression tests (xfail until fixed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_emoji_unicode_channel_name(resolver, mock_discord_client):
    """Emoji-prefixed channel name like #🍻tavern-generalchat should resolve correctly."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "🍻tavern-generalchat", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #🍻tavern-generalchat",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#406497579061215235>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_snowflake_token_valid_id(resolver, mock_discord_client):
    """<#id> token with a valid guild channel ID should pass through silently with no errors."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "🍻tavern-generalchat", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#406497579061215235>",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#406497579061215235>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_snowflake_token_unknown_id(resolver, mock_discord_client):
    """<#id> token with an ID not in the guild should produce a not_found error."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#999999999999999999>",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#999999999999999999>"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "<#999999999999999999>"


def test_render_where_display_none_input():
    """render_where_display returns None when where is None."""
    result = resolver_module.render_where_display(None, [{"id": "123", "name": "general"}])
    assert result is None


def test_render_where_display_plain_text_returns_none():
    """render_where_display returns None for plain text with no channel tokens."""
    result = resolver_module.render_where_display("The Rusty Flagon, table 3", [])
    assert result is None


def test_render_where_display_replaces_tokens():
    """render_where_display replaces <#id> tokens with #name using provided channel list."""
    channels = [
        {"id": "123", "name": "foo", "type": 0},
        {"id": "456", "name": "bar", "type": 0},
    ]
    result = resolver_module.render_where_display("<#123> and <#456>", channels)
    assert result == "#foo and #bar"
