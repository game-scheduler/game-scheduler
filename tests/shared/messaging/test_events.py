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


"""Unit tests for RabbitMQ event schemas."""

from datetime import datetime
from uuid import uuid4

from shared.messaging.events import (
    Event,
    EventType,
    GameCreatedEvent,
    NotificationSendDMEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
)


class TestEventType:
    """Test EventType enum."""

    def test_event_type_values(self):
        """Test event type string values."""
        assert EventType.GAME_CREATED.value == "game.created"
        assert EventType.GAME_UPDATED.value == "game.updated"
        assert EventType.PLAYER_JOINED.value == "game.player_joined"
        assert EventType.NOTIFICATION_SEND_DM.value == "notification.send_dm"


class TestEvent:
    """Test Event base model."""

    def test_event_creation(self):
        """Test creating event with required fields."""
        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": str(uuid4())},
        )

        assert event.event_type == EventType.GAME_CREATED
        assert "game_id" in event.data
        assert isinstance(event.timestamp, datetime)
        assert event.trace_id is None

    def test_event_with_trace_id(self):
        """Test creating event with trace ID."""
        trace_id = "trace-123"
        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": str(uuid4())},
            trace_id=trace_id,
        )

        assert event.trace_id == trace_id

    def test_event_timestamp_auto_generated(self):
        """Test timestamp is automatically set."""
        event = Event(
            event_type=EventType.GAME_CREATED,
            data={},
        )

        assert isinstance(event.timestamp, datetime)
        assert event.timestamp <= datetime.utcnow()

    def test_event_serialization(self):
        """Test event can be serialized to JSON."""
        game_id = uuid4()
        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": game_id},
        )

        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        assert "game.created" in json_str


class TestGameCreatedEvent:
    """Test GameCreatedEvent schema."""

    def test_game_created_event(self):
        """Test creating game created event payload."""
        game_id = uuid4()
        scheduled_at = datetime.utcnow()

        event_data = GameCreatedEvent(
            game_id=game_id,
            title="Test Game",
            guild_id="123456789",
            channel_id="987654321",
            host_id="111222333",
            scheduled_at=scheduled_at,
            max_players=5,
        )

        assert event_data.game_id == game_id
        assert event_data.title == "Test Game"
        assert event_data.guild_id == "123456789"
        assert event_data.max_players == 5

    def test_game_created_event_optional_max_players(self):
        """Test game created event without max players."""
        scheduled_at = datetime.utcnow()

        event_data = GameCreatedEvent(
            game_id=uuid4(),
            title="Test Game",
            guild_id="123",
            channel_id="456",
            host_id="789",
            scheduled_at=scheduled_at,
        )

        assert event_data.max_players is None


class TestPlayerJoinedEvent:
    """Test PlayerJoinedEvent schema."""

    def test_player_joined_event(self):
        """Test creating player joined event payload."""
        event_data = PlayerJoinedEvent(
            game_id=uuid4(),
            player_id="123456789",
            player_count=3,
            max_players=5,
        )

        assert event_data.player_count == 3
        assert event_data.max_players == 5


class TestPlayerLeftEvent:
    """Test PlayerLeftEvent schema."""

    def test_player_left_event(self):
        """Test creating player left event payload."""
        event_data = PlayerLeftEvent(
            game_id=uuid4(),
            player_id="123456789",
            player_count=2,
            max_players=5,
        )

        assert event_data.player_count == 2


class TestNotificationSendDMEvent:
    """Test NotificationSendDMEvent schema."""

    def test_notification_event(self):
        """Test creating notification send DM event payload."""
        event_data = NotificationSendDMEvent(
            user_id="123456789",
            game_id=uuid4(),
            game_title="Test Game",
            game_time_unix=1234567890,
            notification_type="reminder",
            message="Game starts in 1 hour",
        )

        assert event_data.user_id == "123456789"
        assert event_data.game_title == "Test Game"
        assert event_data.notification_type == "reminder"
        assert event_data.message == "Game starts in 1 hour"
