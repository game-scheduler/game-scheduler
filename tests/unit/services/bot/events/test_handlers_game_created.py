# Copyright 2026 Bret McKee
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


"""Unit tests for EventHandlers._handle_game_created and related helpers."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest


@pytest.mark.asyncio
async def test_handle_game_created_success(event_handlers, mock_bot, sample_game, sample_user):
    """Test game.created event handler processes without errors."""
    sample_game.host = sample_user
    sample_game.participants = []

    mock_guild = MagicMock()
    mock_guild.guild_id = sample_game.guild_id
    sample_game.guild = mock_guild

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = MagicMock()
    mock_message.id = 987654321
    mock_channel.send = AsyncMock(return_value=mock_message)

    with (
        patch("services.bot.events.handlers.get_db_session"),
        patch(
            "services.bot.events.handlers.EventHandlers._validate_discord_channel",
            return_value=True,
        ),
        patch(
            "services.bot.events.handlers.EventHandlers._get_bot_channel",
            return_value=mock_channel,
        ),
        patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ),
        patch(
            "services.bot.events.handlers.get_member_display_info",
            return_value=("Test User", "https://example.com/avatar.png"),
        ),
        patch("services.bot.events.handlers.discord.AllowedMentions") as mock_mentions,
    ):
        data = {
            "game_id": sample_game.id,
            "channel_id": sample_game.channel_id,
        }
        await event_handlers._handle_game_created(data)
        mock_mentions.assert_called_once_with(roles=True, everyone=True)


@pytest.mark.asyncio
async def test_handle_game_created_missing_data(event_handlers):
    """Test game.created event with missing data."""
    data = {"game_id": "123"}
    await event_handlers._handle_game_created(data)


@pytest.mark.asyncio
async def test_handle_game_created_invalid_channel(event_handlers, mock_bot):
    """Test game.created event with invalid channel."""
    mock_bot.get_channel.return_value = None

    data = {"game_id": str(uuid4()), "channel_id": "invalid"}
    await event_handlers._handle_game_created(data)


@pytest.mark.asyncio
async def test_validate_game_created_event_success(event_handlers):
    """Test successful validation of game.created event."""
    result = await event_handlers._validate_game_created_event("game123", "channel456")
    assert result == ("game123", "channel456")


@pytest.mark.asyncio
async def test_validate_game_created_event_missing_game_id(event_handlers):
    """Test validation fails with missing game_id."""
    result = await event_handlers._validate_game_created_event(None, "channel456")
    assert result is None


@pytest.mark.asyncio
async def test_validate_game_created_event_missing_channel_id(event_handlers):
    """Test validation fails with missing channel_id."""
    result = await event_handlers._validate_game_created_event("game123", None)
    assert result is None


@pytest.mark.asyncio
async def test_validate_discord_channel_success(event_handlers, mock_bot):
    """Test successful Discord channel validation."""
    mock_bot.get_channel.return_value = MagicMock(spec=discord.TextChannel)

    result = await event_handlers._validate_discord_channel("123")
    assert result is True


@pytest.mark.asyncio
async def test_validate_discord_channel_invalid(event_handlers, mock_bot):
    """Test Discord channel validation when channel is not in cache."""
    mock_bot.get_channel.return_value = None

    result = await event_handlers._validate_discord_channel("999")
    assert result is False


@pytest.mark.asyncio
async def test_get_bot_channel_success(event_handlers, mock_bot):
    """Test getting bot channel from gateway cache."""
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_bot.get_channel.return_value = mock_channel

    result = await event_handlers._get_bot_channel("123")

    assert result == mock_channel
    mock_bot.fetch_channel.assert_not_called()


@pytest.mark.asyncio
async def test_get_bot_channel_not_in_cache_returns_none(event_handlers, mock_bot):
    """Test get_bot_channel returns None when channel is absent from gateway cache."""
    mock_bot.get_channel.return_value = None

    result = await event_handlers._get_bot_channel("123")

    assert result is None
    mock_bot.fetch_channel.assert_not_called()


@pytest.mark.asyncio
async def test_get_bot_channel_invalid_type(event_handlers, mock_bot):
    """Test get_bot_channel returns None when channel is not a TextChannel."""
    mock_channel = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    result = await event_handlers._get_bot_channel("123")

    assert result is None
    mock_bot.fetch_channel.assert_not_called()
