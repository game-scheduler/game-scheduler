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


"""Unit tests for EmbedDeletionConsumer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.api.services.embed_deletion_consumer import EmbedDeletionConsumer
from shared.messaging.events import Event, EventType
from shared.utils.status_transitions import GameStatus


@pytest.fixture
def mock_game():
    """Create a mock game session."""
    game = MagicMock()
    game.id = str(uuid4())
    game.thumbnail_id = None
    game.banner_image_id = None
    return game


@pytest.fixture
def embed_deleted_event(mock_game):
    """Create a mock EMBED_DELETED event."""
    return Event(
        event_type=EventType.EMBED_DELETED,
        data={"game_id": mock_game.id},
    )


@pytest.mark.asyncio
async def test_handle_embed_deleted_cancels_game(mock_game, embed_deleted_event):
    """Test that receiving EMBED_DELETED calls _delete_game_internal on the game."""
    consumer = EmbedDeletionConsumer()

    mock_game_service = AsyncMock()
    mock_game_service.get_game = AsyncMock(return_value=mock_game)
    mock_game_service._delete_game_internal = AsyncMock()

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    with (
        patch(
            "services.api.services.embed_deletion_consumer.get_bypass_db_session",
            return_value=mock_db,
        ),
        patch(
            "services.api.services.embed_deletion_consumer.GameService",
            return_value=mock_game_service,
        ),
    ):
        await consumer._handle_embed_deleted(embed_deleted_event)

    mock_game_service.get_game.assert_awaited_once_with(mock_game.id)
    mock_game_service._delete_game_internal.assert_awaited_once_with(mock_game)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_embed_deleted_unknown_game_id_is_silently_dropped(embed_deleted_event):
    """Test that an unknown game_id is logged and silently dropped without error."""
    consumer = EmbedDeletionConsumer()

    mock_game_service = AsyncMock()
    mock_game_service.get_game = AsyncMock(return_value=None)
    mock_game_service._delete_game_internal = AsyncMock()

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    with (
        patch(
            "services.api.services.embed_deletion_consumer.get_bypass_db_session",
            return_value=mock_db,
        ),
        patch(
            "services.api.services.embed_deletion_consumer.GameService",
            return_value=mock_game_service,
        ),
    ):
        await consumer._handle_embed_deleted(embed_deleted_event)

    mock_game_service._delete_game_internal.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_embed_deleted_archived_game_is_skipped(mock_game, embed_deleted_event):
    """EMBED_DELETED for an already-ARCHIVED game is silently dropped without cancellation."""
    mock_game.status = GameStatus.ARCHIVED
    consumer = EmbedDeletionConsumer()

    mock_game_service = AsyncMock()
    mock_game_service.get_game = AsyncMock(return_value=mock_game)
    mock_game_service._delete_game_internal = AsyncMock()

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    with (
        patch(
            "services.api.services.embed_deletion_consumer.get_bypass_db_session",
            return_value=mock_db,
        ),
        patch(
            "services.api.services.embed_deletion_consumer.GameService",
            return_value=mock_game_service,
        ),
    ):
        await consumer._handle_embed_deleted(embed_deleted_event)

    mock_game_service._delete_game_internal.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_embed_deleted_missing_game_id_is_dropped():
    """Event with no game_id is logged and dropped without touching the DB."""
    consumer = EmbedDeletionConsumer()
    event = Event(event_type=EventType.EMBED_DELETED, data={})

    with patch("services.api.services.embed_deletion_consumer.get_bypass_db_session") as mock_db:
        await consumer._handle_embed_deleted(event)

    mock_db.assert_not_called()


@pytest.mark.asyncio
async def test_start_consuming_connects_binds_and_starts():
    """start_consuming wires up EventConsumer with bind, handler, and start."""
    consumer = EmbedDeletionConsumer()

    mock_event_consumer = MagicMock()
    mock_event_consumer.connect = AsyncMock()
    mock_event_consumer.bind = AsyncMock()
    mock_event_consumer.start_consuming = AsyncMock()

    with patch(
        "services.api.services.embed_deletion_consumer.EventConsumer",
        return_value=mock_event_consumer,
    ):
        await consumer.start_consuming()

    mock_event_consumer.connect.assert_awaited_once()
    mock_event_consumer.bind.assert_awaited_once_with(EventType.EMBED_DELETED)
    mock_event_consumer.register_handler.assert_called_once_with(
        EventType.EMBED_DELETED, consumer._handle_embed_deleted
    )
    mock_event_consumer.start_consuming.assert_awaited_once()
