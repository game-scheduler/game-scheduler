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


"""Unit tests for EventHandlers game cancelled methods."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest


class TestHandleGameCancelledHelpers:
    """Tests for _handle_game_cancelled extracted helper methods."""

    def test_validate_cancellation_event_data_success(self, event_handlers):
        """Test successful validation of cancellation event data."""
        data = {
            "game_id": str(uuid4()),
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is not None
        game_id, message_id, channel_id = result
        assert game_id == data["game_id"]
        assert message_id == data["message_id"]
        assert channel_id == data["channel_id"]

    def test_validate_cancellation_event_data_missing_game_id(self, event_handlers):
        """Test validation fails when game_id is missing."""
        data = {
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_missing_message_id(self, event_handlers):
        """Test validation fails when message_id is missing."""
        data = {
            "game_id": str(uuid4()),
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_missing_channel_id(self, event_handlers):
        """Test validation fails when channel_id is missing."""
        data = {
            "game_id": str(uuid4()),
            "message_id": "123456789",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_empty_values(self, event_handlers):
        """Test validation fails when values are empty strings."""
        data = {
            "game_id": "",
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None


@pytest.mark.asyncio
async def test_handle_game_cancelled_success(event_handlers):
    """Test successful handling of game.cancelled event deletes the Discord message."""
    game_id = str(uuid4())
    message_id = "123456789"
    channel_id = "987654321"

    data = {
        "game_id": game_id,
        "message_id": message_id,
        "channel_id": channel_id,
    }

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_message.delete = AsyncMock()

    with patch.object(
        event_handlers,
        "_get_channel_and_partial_message",
        return_value=(mock_channel, mock_message),
    ):
        await event_handlers._handle_game_cancelled(data)

        mock_message.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_game_cancelled_invalid_data(event_handlers):
    """Test handling of invalid event data."""
    data = {"message_id": "123456789"}

    with patch.object(
        event_handlers,
        "_get_game_with_participants",
        new=AsyncMock(),
    ) as mock_get_game:
        await event_handlers._handle_game_cancelled(data)

        mock_get_game.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_channel_not_found(event_handlers):
    """Test handling when channel/message cannot be fetched."""
    game_id = str(uuid4())
    data = {
        "game_id": game_id,
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    with patch.object(
        event_handlers,
        "_get_channel_and_partial_message",
        return_value=None,
    ) as mock_fetch:
        await event_handlers._handle_game_cancelled(data)

        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_handle_game_cancelled_channel_invalid(event_handlers):
    """Test handling when channel/message is invalid or inaccessible."""
    game_id = str(uuid4())
    data = {
        "game_id": game_id,
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    with patch.object(
        event_handlers,
        "_get_channel_and_partial_message",
        return_value=None,
    ):
        await event_handlers._handle_game_cancelled(data)


@pytest.mark.asyncio
async def test_handle_game_cancelled_handles_exception(event_handlers):
    """Test handling of exceptions during cancellation processing."""
    data = {
        "game_id": str(uuid4()),
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    with patch.object(
        event_handlers,
        "_get_channel_and_partial_message",
        side_effect=Exception("Network error"),
    ):
        await event_handlers._handle_game_cancelled(data)


@pytest.mark.asyncio
async def test_handle_game_cancelled_calls_message_delete(event_handlers):
    """_handle_game_cancelled() calls message.delete() instead of message.edit()."""
    game_id = str(uuid4())
    message_id = "123456789"
    channel_id = "987654321"

    data = {
        "game_id": game_id,
        "message_id": message_id,
        "channel_id": channel_id,
    }

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_message.delete = AsyncMock()
    mock_message.edit = AsyncMock()

    with (
        patch.object(
            event_handlers,
            "_get_channel_and_partial_message",
            return_value=(mock_channel, mock_message),
        ),
    ):
        await event_handlers._handle_game_cancelled(data)

    mock_message.delete.assert_awaited_once()
    mock_message.edit.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_does_not_fetch_game_from_db(event_handlers):
    """_handle_game_cancelled() does not query the database for the game row."""
    game_id = str(uuid4())
    data = {
        "game_id": game_id,
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_message.delete = AsyncMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db_session,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(),
        ) as mock_get_game,
        patch.object(
            event_handlers,
            "_get_channel_and_partial_message",
            return_value=(mock_channel, mock_message),
        ),
    ):
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db_session.return_value.__aexit__ = AsyncMock()

        await event_handlers._handle_game_cancelled(data)

    mock_get_game.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_not_found_handled_gracefully(event_handlers):
    """_handle_game_cancelled() handles discord.NotFound without raising."""
    data = {
        "game_id": str(uuid4()),
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_message.delete = AsyncMock(side_effect=discord.NotFound(MagicMock(), MagicMock()))

    with patch.object(
        event_handlers,
        "_get_channel_and_partial_message",
        return_value=(mock_channel, mock_message),
    ):
        await event_handlers._handle_game_cancelled(data)

    mock_message.delete.assert_awaited_once()
