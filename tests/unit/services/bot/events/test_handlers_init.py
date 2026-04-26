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


"""Unit tests for EventHandlers initialization and start/stop consuming."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.messaging.events import EventType


def test_event_handlers_initialization(event_handlers, mock_bot):
    """Test EventHandlers initializes correctly."""
    assert event_handlers.bot is mock_bot
    assert event_handlers.consumer is None
    assert EventType.GAME_UPDATED in event_handlers._handlers
    assert EventType.NOTIFICATION_DUE in event_handlers._handlers
    assert EventType.GAME_STATUS_TRANSITION_DUE in event_handlers._handlers
    assert EventType.NOTIFICATION_SEND_DM in event_handlers._handlers
    assert EventType.GAME_CREATED in event_handlers._handlers
    assert EventType.PLAYER_JOINED not in event_handlers._handlers
    assert EventType.PLAYER_LEFT not in event_handlers._handlers


@pytest.mark.asyncio
async def test_start_consuming(event_handlers):
    """Test starting event consumption."""
    with patch("services.bot.events.handlers.EventConsumer") as mock_consumer_class:
        mock_consumer = MagicMock()
        mock_consumer.connect = AsyncMock()
        mock_consumer.bind = AsyncMock()
        mock_consumer.register_handler = MagicMock()
        mock_consumer.start_consuming = AsyncMock()
        mock_consumer_class.return_value = mock_consumer

        await event_handlers.start_consuming("test_queue")

        mock_consumer_class.assert_called_once_with(queue_name="test_queue")
        mock_consumer.connect.assert_awaited_once()
        assert mock_consumer.bind.await_count == 3
        mock_consumer.bind.assert_any_await("game.#")
        mock_consumer.bind.assert_any_await("notification.*")
        mock_consumer.bind.assert_any_await("guild.#")
        # GAME_CREATED, GAME_UPDATED, GAME_CANCELLED, GAME_STATUS_CHANGED,
        # GAME_PARTICIPANT_JOINED, GAME_PARTICIPANT_LEFT, GAME_PARTICIPANT_PROMOTED,
        # PARTICIPANT_DROP_DUE
        assert mock_consumer.register_handler.call_count == 8
        mock_consumer.start_consuming.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_consuming(event_handlers):
    """Test stopping event consumption."""
    mock_consumer = MagicMock()
    mock_consumer.close = AsyncMock()
    event_handlers.consumer = mock_consumer

    await event_handlers.stop_consuming()

    mock_consumer.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_consuming_no_consumer(event_handlers):
    """Test stopping when no consumer exists."""
    await event_handlers.stop_consuming()
