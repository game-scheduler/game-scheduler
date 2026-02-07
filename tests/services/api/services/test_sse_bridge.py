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


"""Tests for SSE bridge service."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from services.api.services.sse_bridge import SSEGameUpdateBridge, get_sse_bridge
from shared.messaging.events import Event, EventType


@pytest.fixture
def sse_bridge():
    """Create SSE bridge instance for testing."""
    return SSEGameUpdateBridge()


@pytest.fixture
def mock_event():
    """Create mock game.updated event."""
    return Event(
        event_type=EventType.GAME_UPDATED,
        data={
            "game_id": str(uuid4()),
            "guild_id": "123456789",
            "action": "player_joined",
        },
    )


@pytest.mark.asyncio
async def test_broadcast_filters_by_guild_membership(sse_bridge, mock_event):
    """Test that events are only sent to users who are guild members."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with (
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch("services.api.services.sse_bridge.oauth2.get_user_guilds") as mock_guilds,
    ):
        mock_tokens.return_value = {"access_token": "token123"}
        mock_guilds.return_value = [{"id": "123456789", "name": "Test Guild"}]

        await sse_bridge._broadcast_to_clients(mock_event)

        assert not client_queue.empty()
        message = await client_queue.get()
        data = json.loads(message)
        assert data["type"] == "game_updated"
        assert data["guild_id"] == "123456789"


@pytest.mark.asyncio
async def test_broadcast_skips_non_members(sse_bridge, mock_event):
    """Test that events are not sent to non-guild members."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with (
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch("services.api.services.sse_bridge.oauth2.get_user_guilds") as mock_guilds,
    ):
        mock_tokens.return_value = {"access_token": "token123"}
        mock_guilds.return_value = [{"id": "999999999", "name": "Other Guild"}]

        await sse_bridge._broadcast_to_clients(mock_event)

        assert client_queue.empty()


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected_clients(sse_bridge, mock_event):
    """Test that clients with expired sessions are removed."""
    client_queue = asyncio.Queue()
    session_token = "expired_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens:
        mock_tokens.return_value = None

        await sse_bridge._broadcast_to_clients(mock_event)

        assert "client1" not in sse_bridge.connections


@pytest.mark.asyncio
async def test_broadcast_handles_full_queue(sse_bridge, mock_event):
    """Test that events are dropped when client queue is full."""
    client_queue = asyncio.Queue(maxsize=1)
    await client_queue.put("existing_message")

    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with (
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch("services.api.services.sse_bridge.oauth2.get_user_guilds") as mock_guilds,
    ):
        mock_tokens.return_value = {"access_token": "token123"}
        mock_guilds.return_value = [{"id": "123456789", "name": "Test Guild"}]

        await sse_bridge._broadcast_to_clients(mock_event)

        assert client_queue.qsize() == 1
        assert await client_queue.get() == "existing_message"


@pytest.mark.asyncio
async def test_broadcast_handles_missing_guild_id(sse_bridge):
    """Test that events without guild_id are skipped."""
    event = Event(event_type=EventType.GAME_UPDATED, data={"game_id": str(uuid4())})

    client_queue = asyncio.Queue()
    sse_bridge.connections["client1"] = (client_queue, "session", "discord123")

    await sse_bridge._broadcast_to_clients(event)

    assert client_queue.empty()


@pytest.mark.asyncio
async def test_broadcast_handles_api_errors(sse_bridge, mock_event):
    """Test that API errors during guild check don't crash the bridge."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens:
        mock_tokens.side_effect = Exception("API error")

        await sse_bridge._broadcast_to_clients(mock_event)

        assert "client1" in sse_bridge.connections
        assert client_queue.empty()


@pytest.mark.asyncio
async def test_start_consuming_initializes_consumer(sse_bridge):
    """Test that start_consuming sets up RabbitMQ consumer."""
    mock_consumer = Mock()
    mock_consumer.connect = AsyncMock()
    mock_consumer.bind = AsyncMock()
    mock_consumer.start_consuming = AsyncMock()

    with patch("services.api.services.sse_bridge.EventConsumer") as mock_consumer_class:
        mock_consumer_class.return_value = mock_consumer

        await sse_bridge.start_consuming()

        assert sse_bridge.consumer is not None
        mock_consumer.connect.assert_called_once()
        mock_consumer.bind.assert_called_once_with("game.updated.*")
        mock_consumer.start_consuming.assert_called_once()


@pytest.mark.asyncio
async def test_stop_consuming_closes_consumer(sse_bridge):
    """Test that stop_consuming closes RabbitMQ connection."""
    mock_consumer = Mock()
    mock_consumer.close = AsyncMock()

    sse_bridge.consumer = mock_consumer

    await sse_bridge.stop_consuming()

    mock_consumer.close.assert_called_once()
    assert sse_bridge.consumer is None


@pytest.mark.asyncio
async def test_stop_consuming_handles_no_consumer(sse_bridge):
    """Test that stop_consuming works when no consumer exists."""
    sse_bridge.consumer = None
    await sse_bridge.stop_consuming()


def test_get_sse_bridge_returns_singleton():
    """Test that get_sse_bridge returns the same instance."""
    bridge1 = get_sse_bridge()
    bridge2 = get_sse_bridge()
    assert bridge1 is bridge2


@pytest.mark.asyncio
async def test_broadcast_to_multiple_clients(sse_bridge, mock_event):
    """Test broadcasting to multiple authorized clients."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()

    sse_bridge.connections["client1"] = (queue1, "session1", "user1")
    sse_bridge.connections["client2"] = (queue2, "session2", "user2")

    with (
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch("services.api.services.sse_bridge.oauth2.get_user_guilds") as mock_guilds,
    ):
        mock_tokens.return_value = {"access_token": "token123"}
        mock_guilds.return_value = [{"id": "123456789", "name": "Test Guild"}]

        await sse_bridge._broadcast_to_clients(mock_event)

        assert not queue1.empty()
        assert not queue2.empty()

        message1 = json.loads(await queue1.get())
        message2 = json.loads(await queue2.get())

        assert message1["guild_id"] == "123456789"
        assert message2["guild_id"] == "123456789"
