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


"""Integration tests for database deferred event publishing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import (
    clear_deferred_events_after_rollback,
    publish_deferred_events_after_commit,
)
from shared.messaging.deferred_publisher import DeferredEventPublisher
from shared.messaging.events import Event, EventType


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    session.info = {}
    return session


def test_publish_deferred_events_after_commit_empty_session(mock_session):
    """Test after_commit with no deferred events does nothing."""
    with patch("shared.messaging.publisher.EventPublisher") as mock_publisher_class:
        publish_deferred_events_after_commit(mock_session)

        # Should not create publisher if no events
        mock_publisher_class.assert_not_called()


def test_publish_deferred_events_after_commit_with_events(mock_session):
    """Test after_commit publishes deferred events."""
    # Setup deferred events
    event1 = Event(event_type=EventType.GAME_CREATED, data={"id": "1"})
    event2 = Event(event_type=EventType.GAME_UPDATED, data={"id": "2"})

    mock_session.info["_deferred_events"] = [
        {"event": event1, "routing_key": None},
        {"event": event2, "routing_key": "custom.key"},
    ]

    with patch("shared.messaging.publisher.EventPublisher") as mock_publisher_class:
        mock_publisher = AsyncMock()
        mock_publisher_class.return_value = mock_publisher

        with patch("asyncio.create_task") as mock_create_task:
            # Mock create_task to prevent coroutine warning
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            publish_deferred_events_after_commit(mock_session)

            # Verify task was created with a coroutine
            mock_create_task.assert_called_once()
            call_args = mock_create_task.call_args[0]
            # Close the coroutine to prevent RuntimeWarning
            if hasattr(call_args[0], "close"):
                call_args[0].close()


def test_clear_deferred_events_after_rollback_empty(mock_session):
    """Test after_rollback with no events."""
    clear_deferred_events_after_rollback(mock_session)

    assert "_deferred_events" not in mock_session.info


def test_clear_deferred_events_after_rollback_with_events(mock_session):
    """Test after_rollback clears deferred events."""
    # Setup deferred events
    mock_session.info["_deferred_events"] = [
        {"event": "event1", "routing_key": None},
        {"event": "event2", "routing_key": None},
    ]

    clear_deferred_events_after_rollback(mock_session)

    assert "_deferred_events" not in mock_session.info


def test_deferred_events_preserved_in_session_info():
    """Test that session.info correctly stores deferred events."""
    # Create a real AsyncSession mock with working info dict
    db = MagicMock(spec=AsyncSession)
    db.info = {}

    event_publisher = AsyncMock()
    deferred = DeferredEventPublisher(db=db, event_publisher=event_publisher)

    # Add events
    event1 = Event(event_type=EventType.GAME_CREATED, data={"id": "1"})
    event2 = Event(event_type=EventType.GAME_UPDATED, data={"id": "2"})

    deferred.publish_deferred(event1)
    deferred.publish_deferred(event2)

    # Verify events are in session.info
    assert "_deferred_events" in db.info
    assert len(db.info["_deferred_events"]) == 2

    # Simulate commit clearing events
    DeferredEventPublisher.clear_deferred_events(db)
    assert "_deferred_events" not in db.info
