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


"""Unit tests for event builder functions."""

from datetime import timedelta
from uuid import uuid4

from services.scheduler.event_builders import (
    build_game_reminder_event,
    build_status_transition_event,
)
from shared.messaging.events import EventType
from shared.models import GameStatusSchedule, NotificationSchedule
from shared.models.base import utc_now
from shared.models.game import GameStatus


class TestBuildGameReminderEvent:
    """Test build_game_reminder_event function."""

    def test_returns_tuple_with_event_and_ttl(self):
        """Function returns tuple of (Event, TTL)."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        result = build_game_reminder_event(notification)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_event_has_correct_type_and_data(self):
        """Event has GAME_REMINDER_DUE type and correct payload."""
        game_id = str(uuid4())
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=game_id,
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        event, _ = build_game_reminder_event(notification)

        assert event.event_type == EventType.GAME_REMINDER_DUE
        assert str(event.data["game_id"]) == game_id
        assert event.data["reminder_minutes"] == 60

    def test_ttl_calculated_from_game_scheduled_at(self):
        """TTL is calculated as milliseconds until game starts."""
        future_time = utc_now() + timedelta(hours=2)
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=future_time,
            sent=False,
        )

        _, ttl = build_game_reminder_event(notification)

        assert ttl is not None
        expected_seconds = (future_time - utc_now()).total_seconds()
        expected_ms = int(expected_seconds * 1000)
        assert abs(ttl - expected_ms) < 1000

    def test_minimum_ttl_for_imminent_games(self):
        """TTL is minimum 60 seconds for games starting soon."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            reminder_minutes=60,
            notification_time=utc_now(),
            game_scheduled_at=utc_now() + timedelta(seconds=30),
            sent=False,
        )

        _, ttl = build_game_reminder_event(notification)

        assert ttl == 60000

    def test_none_ttl_when_no_scheduled_time(self):
        """TTL is None when game has no scheduled_at time."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=None,
            sent=False,
        )

        _, ttl = build_game_reminder_event(notification)

        assert ttl is None


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
