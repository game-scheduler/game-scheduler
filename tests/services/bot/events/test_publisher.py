# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for bot event publisher."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from services.bot.events.publisher import BotEventPublisher
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
async def test_publish_player_joined(bot_publisher, mock_publisher):
    """Test publishing player joined event."""
    game_id = "550e8400-e29b-41d4-a716-446655440000"
    player_id = "123456789"
    player_count = 3
    max_players = 10

    await bot_publisher.publish_player_joined(
        game_id=game_id,
        player_id=player_id,
        player_count=player_count,
        max_players=max_players,
    )

    mock_publisher.publish.assert_awaited_once()
    call_args = mock_publisher.publish.call_args

    event = call_args.kwargs["event"]
    assert isinstance(event, Event)
    assert event.event_type == EventType.PLAYER_JOINED
    assert event.data["game_id"] == UUID(game_id)
    assert event.data["player_id"] == player_id
    assert event.data["player_count"] == player_count
    assert event.data["max_players"] == max_players

    assert call_args.kwargs["routing_key"] == "game.player_joined"


@pytest.mark.asyncio
async def test_publish_player_left(bot_publisher, mock_publisher):
    """Test publishing player left event."""
    game_id = "550e8400-e29b-41d4-a716-446655440000"
    player_id = "123456789"
    player_count = 2

    await bot_publisher.publish_player_left(
        game_id=game_id, player_id=player_id, player_count=player_count
    )

    mock_publisher.publish.assert_awaited_once()
    call_args = mock_publisher.publish.call_args

    event = call_args.kwargs["event"]
    assert isinstance(event, Event)
    assert event.event_type == EventType.PLAYER_LEFT
    assert event.data["game_id"] == UUID(game_id)
    assert event.data["player_id"] == player_id
    assert event.data["player_count"] == player_count

    assert call_args.kwargs["routing_key"] == "game.player_left"


@pytest.mark.asyncio
async def test_publish_game_created(bot_publisher, mock_publisher):
    """Test publishing game created event."""
    game_id = "550e8400-e29b-41d4-a716-446655440000"
    title = "Test Game"
    guild_id = "987654321"
    channel_id = "123456789"
    host_id = "111222333"
    scheduled_at = "2025-11-20T18:00:00Z"
    scheduled_at_unix = 1732125600

    await bot_publisher.publish_game_created(
        game_id=game_id,
        title=title,
        guild_id=guild_id,
        channel_id=channel_id,
        host_id=host_id,
        scheduled_at=scheduled_at,
        scheduled_at_unix=scheduled_at_unix,
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
    updated_fields = {"title": "New Title", "max_players": 12}

    await bot_publisher.publish_game_updated(game_id=game_id, updated_fields=updated_fields)

    mock_publisher.publish.assert_awaited_once()
    call_args = mock_publisher.publish.call_args

    event = call_args.kwargs["event"]
    assert isinstance(event, Event)
    assert event.event_type == EventType.GAME_UPDATED
    assert event.data["game_id"] == game_id
    assert event.data["updated_fields"] == updated_fields

    assert call_args.kwargs["routing_key"] == "game.updated"


@pytest.mark.asyncio
async def test_get_bot_publisher_singleton():
    """Test get_bot_publisher returns singleton instance."""
    from services.bot.events.publisher import get_bot_publisher

    publisher1 = get_bot_publisher()
    publisher2 = get_bot_publisher()

    assert publisher1 is publisher2
