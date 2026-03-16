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


"""Unit tests for EventHandlers game event error paths.

Covers _process_event, _handle_game_created, _handle_game_updated,
and _delayed_refresh error and branch paths.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import Event, EventType


@pytest.fixture
def bot():
    return MagicMock(spec=discord.Client)


@pytest.fixture
def handlers(bot):
    return EventHandlers(bot)


def _db_ctx(mock_db=None):
    if mock_db is None:
        mock_db = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_db, ctx


# ---------------------------------------------------------------------------
# _process_event
# ---------------------------------------------------------------------------


async def test_process_event_no_handler_registered(handlers):
    """Unknown event type logs warning and returns without raising."""
    event = MagicMock(spec=Event)
    event.event_type = EventType.GAME_STARTED  # not in _handlers
    await handlers._process_event(event)


async def test_process_event_dispatches_to_handler(handlers):
    """Registered handler is invoked with event data."""
    mock_handler = AsyncMock()
    handlers._handlers[EventType.GAME_CREATED] = mock_handler
    event = MagicMock(spec=Event)
    event.event_type = EventType.GAME_CREATED
    event.data = {"game_id": str(uuid4())}
    await handlers._process_event(event)
    mock_handler.assert_called_once_with(event.data)


async def test_process_event_handler_exception_is_reraised(handlers):
    """Exception raised by handler is logged and propagated."""
    handlers._handlers[EventType.GAME_CREATED] = AsyncMock(side_effect=RuntimeError("boom"))
    event = MagicMock(spec=Event)
    event.event_type = EventType.GAME_CREATED
    event.data = {}
    with pytest.raises(RuntimeError):
        await handlers._process_event(event)


# ---------------------------------------------------------------------------
# _handle_game_created
# ---------------------------------------------------------------------------


async def test_handle_game_created_channel_validation_fails(handlers):
    """Returns early when Discord channel cannot be validated."""
    data = {"game_id": str(uuid4()), "channel_id": "111222333444555666"}
    _, ctx = _db_ctx()
    with (
        patch.object(handlers, "_validate_discord_channel", new=AsyncMock(return_value=False)),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_created(data)


async def test_handle_game_created_game_not_found(handlers):
    """Returns early when game is not found in the database."""
    data = {"game_id": str(uuid4()), "channel_id": "111222333444555666"}
    _, ctx = _db_ctx()
    with (
        patch.object(handlers, "_validate_discord_channel", new=AsyncMock(return_value=True)),
        patch.object(handlers, "_get_game_with_participants", new=AsyncMock(return_value=None)),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_created(data)


async def test_handle_game_created_bot_channel_not_accessible(handlers):
    """Returns early when the bot cannot access the Discord channel."""
    data = {"game_id": str(uuid4()), "channel_id": "111222333444555666"}
    mock_game = MagicMock()
    _, ctx = _db_ctx()
    with (
        patch.object(handlers, "_validate_discord_channel", new=AsyncMock(return_value=True)),
        patch.object(
            handlers, "_get_game_with_participants", new=AsyncMock(return_value=mock_game)
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=(None, MagicMock(), MagicMock())),
        ),
        patch.object(handlers, "_get_bot_channel", new=AsyncMock(return_value=None)),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_created(data)


# ---------------------------------------------------------------------------
# _handle_game_updated
# ---------------------------------------------------------------------------


async def test_handle_game_updated_missing_game_id(handlers):
    """Returns early when game_id is absent from the event payload."""
    await handlers._handle_game_updated({})


async def test_handle_game_updated_redis_failure_fails_open(handlers):
    """Falls back to an immediate message refresh when Redis is unavailable."""
    game_id = str(uuid4())
    with (
        patch(
            "services.bot.events.handlers.get_redis_client",
            new=AsyncMock(side_effect=ConnectionError("redis down")),
        ),
        patch.object(handlers, "_refresh_game_message", new=AsyncMock()) as mock_refresh,
    ):
        await handlers._handle_game_updated({"game_id": game_id})
    mock_refresh.assert_called_once_with(game_id)


# ---------------------------------------------------------------------------
# _delayed_refresh
# ---------------------------------------------------------------------------


async def test_delayed_refresh_refreshes_and_clears_pending(handlers):
    """Refreshes the game message and removes game_id from pending set."""
    game_id = str(uuid4())
    handlers._pending_refreshes.add(game_id)
    with (
        patch("asyncio.sleep", new=AsyncMock()),
        patch.object(handlers, "_refresh_game_message", new=AsyncMock()) as mock_refresh,
    ):
        await handlers._delayed_refresh(game_id, 0.0)
    mock_refresh.assert_called_once_with(game_id)
    assert game_id not in handlers._pending_refreshes
