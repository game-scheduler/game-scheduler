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


"""Unit tests for bot event publisher."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from services.bot.events.publisher import BotEventPublisher, get_bot_publisher
from shared.messaging.events import Event, EventType


@pytest.fixture
def mock_publisher():
    """Create mock EventPublisher."""
    publisher = MagicMock()
    publisher.connect = AsyncMock()
    publisher.close = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def bot_publisher(mock_publisher):
    """Create BotEventPublisher with mock."""
    return BotEventPublisher(publisher=mock_publisher)


@pytest.mark.asyncio
async def test_connect(bot_publisher, mock_publisher):
    """Test connecting to RabbitMQ."""
    await bot_publisher.connect()

    mock_publisher.connect.assert_awaited_once()
    assert bot_publisher._connected is True


@pytest.mark.asyncio
async def test_connect_idempotent(bot_publisher, mock_publisher):
    """Test connecting multiple times is idempotent."""
    await bot_publisher.connect()
    await bot_publisher.connect()

    mock_publisher.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect(bot_publisher, mock_publisher):
    """Test disconnecting from RabbitMQ."""
    await bot_publisher.connect()
    await bot_publisher.disconnect()

    mock_publisher.close.assert_awaited_once()
    assert bot_publisher._connected is False


@pytest.mark.asyncio
async def test_disconnect_when_not_connected(bot_publisher, mock_publisher):
    """Test disconnecting when not connected does nothing."""
    await bot_publisher.disconnect()

    mock_publisher.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_game_created(bot_publisher, mock_publisher):
    """Test publishing game created event."""

    game_id = "550e8400-e29b-41d4-a716-446655440000"
    title = "Test Game"
    guild_id = "987654321"
    channel_id = "123456789"
    host_id = "111222333"
    scheduled_at = "2025-11-20T18:00:00Z"
    signup_method = "SELF_SIGNUP"

    await bot_publisher.publish_game_created(
        game_id=game_id,
        title=title,
        guild_id=guild_id,
        channel_id=channel_id,
        host_id=host_id,
        scheduled_at=scheduled_at,
        signup_method=signup_method,
    )

    mock_publisher.publish.assert_awaited_once()
    call_args = mock_publisher.publish.call_args

    event = call_args.kwargs["event"]
    assert isinstance(event, Event)
    assert event.event_type == EventType.GAME_CREATED
    assert event.data["game_id"] == UUID(game_id)
    assert event.data["title"] == title
    assert event.data["guild_id"] == guild_id
    assert event.data["channel_id"] == channel_id
    assert event.data["host_id"] == host_id

    assert call_args.kwargs["routing_key"] == "game.created"


@pytest.mark.asyncio
async def test_publish_game_updated(bot_publisher, mock_publisher):
    """Test publishing game updated event."""
    game_id = "550e8400-e29b-41d4-a716-446655440000"
    guild_id = "123456789012345678"
    updated_fields = {"title": "New Title", "max_players": 12}

    await bot_publisher.publish_game_updated(
        game_id=game_id, guild_id=guild_id, updated_fields=updated_fields
    )

    mock_publisher.publish.assert_awaited_once()
    call_args = mock_publisher.publish.call_args

    event = call_args.kwargs["event"]
    assert isinstance(event, Event)
    assert event.event_type == EventType.GAME_UPDATED
    assert event.data["game_id"] == game_id
    assert event.data["guild_id"] == guild_id
    assert event.data["updated_fields"] == updated_fields

    assert call_args.kwargs["routing_key"] == f"game.updated.{guild_id}"


@pytest.mark.asyncio
async def test_get_bot_publisher_singleton():
    """Test get_bot_publisher returns singleton instance."""

    publisher1 = get_bot_publisher()
    publisher2 = get_bot_publisher()

    assert publisher1 is publisher2
