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


"""Unit tests for event builder functions."""

from datetime import timedelta
from uuid import uuid4

from services.scheduler.event_builders import (
    build_notification_event,
    build_status_transition_event,
)
from shared.messaging.events import EventType
from shared.models import GameStatus, GameStatusSchedule, NotificationSchedule
from shared.models.base import utc_now


class TestBuildNotificationEvent:
    """Test build_notification_event function."""

    def test_returns_tuple_with_event_and_ttl(self):
        """Function returns tuple of (Event, TTL)."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        result = build_notification_event(notification)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_event_has_correct_type_and_data_for_reminder(self):
        """Event has NOTIFICATION_DUE type and correct payload for reminder."""
        game_id = str(uuid4())
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=game_id,
            notification_type="reminder",
            participant_id=None,
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        event, _ = build_notification_event(notification)

        assert event.event_type == EventType.NOTIFICATION_DUE
        assert str(event.data["game_id"]) == game_id
        assert event.data["notification_type"] == "reminder"
        assert event.data["participant_id"] is None

    def test_ttl_calculated_from_game_scheduled_at(self):
        """TTL is calculated as milliseconds until game starts."""
        future_time = utc_now() + timedelta(hours=2)
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=future_time,
            sent=False,
        )

        _, ttl = build_notification_event(notification)

        assert ttl is not None
        expected_seconds = (future_time - utc_now()).total_seconds()
        expected_ms = int(expected_seconds * 1000)
        assert abs(ttl - expected_ms) < 1000

    def test_minimum_ttl_for_imminent_games(self):
        """TTL is minimum 60 seconds for games starting soon."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now(),
            game_scheduled_at=utc_now() + timedelta(seconds=30),
            sent=False,
        )

        _, ttl = build_notification_event(notification)

        assert ttl == 60000

    def test_none_ttl_when_no_scheduled_time(self):
        """TTL is None when game has no scheduled_at time."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=None,
            sent=False,
        )

        _, ttl = build_notification_event(notification)

        assert ttl is None

    def test_event_has_correct_type_and_data_for_join_notification(self):
        """Event has NOTIFICATION_DUE type and correct payload for join notification."""
        game_id = str(uuid4())
        participant_id = str(uuid4())
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=game_id,
            notification_type="join_notification",
            participant_id=participant_id,
            reminder_minutes=None,
            notification_time=utc_now() + timedelta(seconds=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        event, ttl = build_notification_event(notification)

        assert event.event_type == EventType.NOTIFICATION_DUE
        assert str(event.data["game_id"]) == game_id
        assert event.data["notification_type"] == "join_notification"
        assert event.data["participant_id"] == participant_id
        assert ttl is not None


class TestBuildStatusTransitionEvent:
    """Test build_status_transition_event function."""

    def test_returns_tuple_with_event_and_none(self):
        """Function returns tuple of (Event, None) - no TTL."""
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            target_status=GameStatus.IN_PROGRESS.value,
            transition_time=utc_now(),
            executed=False,
        )

        result = build_status_transition_event(transition)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[1] is None

    def test_event_has_correct_type_and_data(self):
        """Event has GAME_STATUS_TRANSITION_DUE type and correct payload."""
        game_id = str(uuid4())
        transition_time = utc_now()
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=game_id,
            target_status=GameStatus.COMPLETED.value,
            transition_time=transition_time,
            executed=False,
        )

        event, _ = build_status_transition_event(transition)

        assert event.event_type == EventType.GAME_STATUS_TRANSITION_DUE
        assert str(event.data["game_id"]) == game_id
        assert event.data["target_status"] == GameStatus.COMPLETED.value
        assert event.data["transition_time"] == transition_time

    def test_always_returns_none_ttl(self):
        """Status transitions always have None TTL (never expire)."""
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            target_status=GameStatus.CANCELLED.value,
            transition_time=utc_now() - timedelta(hours=1),
            executed=False,
        )

        _, ttl = build_status_transition_event(transition)

        assert ttl is None
