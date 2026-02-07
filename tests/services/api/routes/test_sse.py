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


"""Tests for SSE endpoint."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from services.api.routes.sse import game_updates
from shared.schemas.auth import CurrentUser


@pytest.fixture
def mock_sse_bridge():
    """Mock SSE bridge for testing."""
    bridge = Mock()
    bridge.connections = {}
    return bridge


@pytest.fixture
def mock_user():
    """Mock database user."""
    user = Mock()
    user.id = "user-id-123"
    user.discord_id = "user123"
    return user


@pytest.fixture
def mock_current_user(mock_user):
    """Mock authenticated user."""
    return CurrentUser(
        user=mock_user,
        session_token="session123",
        access_token="access123",
    )


@pytest.mark.asyncio
async def test_game_updates_creates_sse_connection(mock_sse_bridge, mock_current_user):
    """Test that game_updates endpoint registers connection with bridge."""
    with patch("services.api.routes.sse.get_sse_bridge", return_value=mock_sse_bridge):
        response = await game_updates(mock_current_user)

        assert response.status_code == 200
        assert response.media_type == "text/event-stream"
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"

        registered_clients = list(mock_sse_bridge.connections.keys())
        assert len(registered_clients) == 1

        client_id = registered_clients[0]
        queue, session_token, discord_id = mock_sse_bridge.connections[client_id]

        assert session_token == "session123"
        assert discord_id == "user123"
        assert isinstance(queue, asyncio.Queue)


@pytest.mark.asyncio
async def test_game_updates_returns_streaming_response(mock_sse_bridge, mock_current_user):
    """Test that game_updates returns proper streaming response."""
    with patch("services.api.routes.sse.get_sse_bridge", return_value=mock_sse_bridge):
        response = await game_updates(mock_current_user)

        assert response.status_code == 200
        assert response.media_type == "text/event-stream"
        assert response.headers["x-accel-buffering"] == "no"
