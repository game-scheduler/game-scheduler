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
