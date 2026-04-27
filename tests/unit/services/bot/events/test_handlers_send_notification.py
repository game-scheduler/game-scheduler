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


"""Unit tests for EventHandlers._handle_send_notification and _get_game_with_participants."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest


@pytest.mark.asyncio
async def test_handle_send_notification_success(event_handlers, mock_bot):
    """Test successful handling of notification.send_dm event."""
    mock_user = MagicMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Game starts in 1 hour!",
    }

    await event_handlers._handle_send_notification(data)

    mock_bot.fetch_user.assert_not_called()
    mock_user.send.assert_awaited_once_with("Game starts in 1 hour!")


@pytest.mark.asyncio
async def test_handle_send_notification_dm_disabled(event_handlers, mock_bot):
    """Test notification when user has DMs disabled."""
    mock_user = MagicMock()
    mock_user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), MagicMock()))
    mock_bot.get_user.return_value = mock_user

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Test message",
    }

    await event_handlers._handle_send_notification(data)

    assert True  # no exception raised when user has DMs disabled


@pytest.mark.asyncio
async def test_handle_send_notification_user_not_in_cache(event_handlers, mock_bot):
    """Test notification skipped when user is absent from gateway cache."""
    mock_bot.get_user.return_value = None

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Test message",
    }

    result = await event_handlers._handle_send_notification(data)

    mock_bot.fetch_user.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_handle_send_notification_invalid_data(event_handlers):
    """Test notification with invalid data."""
    data = {"user_id": "123"}

    await event_handlers._handle_send_notification(data)

    assert True  # no exception raised for invalid/incomplete data


@pytest.mark.asyncio
async def test_get_game_with_participants(event_handlers, sample_game, sample_user):
    """Test fetching game with participants."""
    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        result = await event_handlers._get_game_with_participants(mock_db, sample_game.id)

        assert result == sample_game
        mock_db.execute.assert_awaited_once()
        mock_db_session.assert_not_called()


@pytest.mark.asyncio
async def test_get_game_with_participants_not_found(event_handlers):
    """Test fetching non-existent game."""
    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        result = await event_handlers._get_game_with_participants(mock_db, str(uuid4()))

        assert result is None
        mock_db_session.assert_not_called()
