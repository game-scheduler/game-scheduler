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


"""Tests for deferred event publisher."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.messaging.deferred_publisher import DeferredEventPublisher
from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.info = {}
    return db


@pytest.fixture
def mock_event_publisher():
    """Mock base event publisher."""
    return AsyncMock(spec=EventPublisher)


@pytest.fixture
def deferred_publisher(mock_db, mock_event_publisher):
    """DeferredEventPublisher instance."""
    return DeferredEventPublisher(db=mock_db, event_publisher=mock_event_publisher)


def test_publish_deferred_queues_event(deferred_publisher, mock_db):
    """Test that publish_deferred stores event in session.info."""
    event = Event(
        event_type=EventType.GAME_CREATED,
        data={"game_id": "test-123"},
    )

    deferred_publisher.publish_deferred(event=event)

    assert "_deferred_events" in mock_db.info
    assert len(mock_db.info["_deferred_events"]) == 1
    assert mock_db.info["_deferred_events"][0]["event"] == event
    assert mock_db.info["_deferred_events"][0]["routing_key"] is None


def test_publish_deferred_with_routing_key(deferred_publisher, mock_db):
    """Test that publish_deferred stores routing key."""
    event = Event(
        event_type=EventType.GAME_UPDATED,
        data={"game_id": "test-456"},
    )

    deferred_publisher.publish_deferred(event=event, routing_key="custom.routing.key")

    stored_event = mock_db.info["_deferred_events"][0]
    assert stored_event["routing_key"] == "custom.routing.key"


def test_publish_deferred_multiple_events(deferred_publisher, mock_db):
    """Test that multiple events are queued in order."""
    event1 = Event(event_type=EventType.GAME_CREATED, data={"id": "1"})
    event2 = Event(event_type=EventType.GAME_UPDATED, data={"id": "2"})
    event3 = Event(event_type=EventType.GAME_CANCELLED, data={"id": "3"})

    deferred_publisher.publish_deferred(event=event1)
    deferred_publisher.publish_deferred(event=event2)
    deferred_publisher.publish_deferred(event=event3)

    assert len(mock_db.info["_deferred_events"]) == 3
    assert mock_db.info["_deferred_events"][0]["event"] == event1
    assert mock_db.info["_deferred_events"][1]["event"] == event2
    assert mock_db.info["_deferred_events"][2]["event"] == event3


def test_publish_dict_deferred(deferred_publisher, mock_db):
    """Test publish_dict_deferred convenience method."""
    deferred_publisher.publish_dict_deferred(
        event_type="game.created",
        data={"game_id": "test-789"},
        trace_id="trace-123",
    )

    assert len(mock_db.info["_deferred_events"]) == 1
    stored_event = mock_db.info["_deferred_events"][0]["event"]
    assert stored_event.event_type == EventType.GAME_CREATED
    assert stored_event.data == {"game_id": "test-789"}
    assert stored_event.trace_id == "trace-123"


def test_get_deferred_events_empty(mock_db):
    """Test getting deferred events from empty session."""
    events = DeferredEventPublisher.get_deferred_events(mock_db)

    assert events == []


def test_get_deferred_events_with_data(mock_db):
    """Test getting deferred events with stored data."""
    mock_db.info["_deferred_events"] = [
        {"event": "event1", "routing_key": None},
        {"event": "event2", "routing_key": "key"},
    ]

    events = DeferredEventPublisher.get_deferred_events(mock_db)

    assert len(events) == 2
    assert events[0]["event"] == "event1"
    assert events[1]["event"] == "event2"


def test_clear_deferred_events_empty(mock_db):
    """Test clearing deferred events from empty session."""
    DeferredEventPublisher.clear_deferred_events(mock_db)

    assert "_deferred_events" not in mock_db.info


def test_clear_deferred_events_with_data(mock_db):
    """Test clearing deferred events removes data."""
    mock_db.info["_deferred_events"] = [
        {"event": "event1"},
        {"event": "event2"},
    ]

    DeferredEventPublisher.clear_deferred_events(mock_db)

    assert "_deferred_events" not in mock_db.info


def test_publish_deferred_preserves_existing_events(deferred_publisher, mock_db):
    """Test that publish_deferred preserves existing queued events."""
    # Manually add an event
    mock_db.info["_deferred_events"] = [{"event": "existing_event", "routing_key": None}]

    # Add new event
    new_event = Event(event_type=EventType.GAME_CREATED, data={"id": "new"})
    deferred_publisher.publish_deferred(event=new_event)

    assert len(mock_db.info["_deferred_events"]) == 2
    assert mock_db.info["_deferred_events"][0]["event"] == "existing_event"
    assert mock_db.info["_deferred_events"][1]["event"] == new_event
