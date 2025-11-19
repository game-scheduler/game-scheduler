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


"""Tests for notification time window calculations."""

import datetime

from services.scheduler.utils.notification_windows import (
    get_upcoming_games_window,
    should_send_notification,
)


class TestNotificationWindows:
    """Test suite for notification timing calculations."""

    def test_should_send_notification_exact_time(self):
        """Notification should be sent when exactly at reminder time."""
        game_time = datetime.datetime(2025, 11, 20, 15, 0, 0)
        current_time = datetime.datetime(2025, 11, 20, 14, 45, 0)
        reminder_minutes = 15

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        assert should_send is True
        assert notif_time == datetime.datetime(2025, 11, 20, 14, 45, 0)

    def test_should_send_notification_within_5_minutes_before(self):
        """Notification should be sent up to 5 minutes before reminder time."""
        game_time = datetime.datetime(2025, 11, 20, 15, 0, 0)
        current_time = datetime.datetime(2025, 11, 20, 14, 40, 0)
        reminder_minutes = 15

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        assert should_send is True

    def test_should_send_notification_within_5_minutes_after(self):
        """Notification should be sent up to 5 minutes after reminder time."""
        game_time = datetime.datetime(2025, 11, 20, 15, 0, 0)
        current_time = datetime.datetime(2025, 11, 20, 14, 50, 0)
        reminder_minutes = 15

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        assert should_send is True

    def test_should_not_send_notification_too_early(self):
        """Notification should not be sent more than 5 minutes before reminder time."""
        game_time = datetime.datetime(2025, 11, 20, 15, 0, 0)
        current_time = datetime.datetime(2025, 11, 20, 14, 35, 0)
        reminder_minutes = 15

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        assert should_send is False

    def test_should_not_send_notification_too_late(self):
        """Notification should not be sent more than 5 minutes after reminder time."""
        game_time = datetime.datetime(2025, 11, 20, 15, 0, 0)
        current_time = datetime.datetime(2025, 11, 20, 14, 55, 0)
        reminder_minutes = 15

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        assert should_send is False

    def test_should_send_notification_default_current_time(self):
        """should_send_notification uses current time if not provided."""
        game_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
            minutes=60
        )
        reminder_minutes = 60

        should_send, notif_time = should_send_notification(game_time, reminder_minutes)

        assert should_send is True

    def test_get_upcoming_games_window_default_params(self):
        """Default window is 5 min lookback to 180 min lookahead."""
        start_time, end_time = get_upcoming_games_window()

        time_diff = end_time - start_time
        expected_diff = datetime.timedelta(minutes=175)

        assert abs((time_diff - expected_diff).total_seconds()) < 60

    def test_get_upcoming_games_window_custom_params(self):
        """Custom lookback and lookahead values work correctly."""
        start_time, end_time = get_upcoming_games_window(lookback_minutes=10, lookahead_minutes=60)

        time_diff = end_time - start_time
        expected_diff = datetime.timedelta(minutes=50)

        assert abs((time_diff - expected_diff).total_seconds()) < 60

    def test_get_upcoming_games_window_returns_future_times(self):
        """Window times are in the future relative to now."""
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        start_time, end_time = get_upcoming_games_window()

        assert start_time > now
        assert end_time > start_time

    def test_notification_time_calculation(self):
        """Notification time is correctly calculated as game_time - reminder_minutes."""
        game_time = datetime.datetime(2025, 11, 20, 18, 30, 0)
        reminder_minutes = 45
        current_time = datetime.datetime(2025, 11, 20, 17, 45, 0)

        should_send, notif_time = should_send_notification(
            game_time, reminder_minutes, current_time
        )

        expected_notif_time = datetime.datetime(2025, 11, 20, 17, 45, 0)
        assert notif_time == expected_notif_time

    def test_multiple_reminder_times(self):
        """Different reminder times produce different notification windows."""
        game_time = datetime.datetime(2025, 11, 20, 16, 0, 0)

        current_time = datetime.datetime(2025, 11, 20, 15, 45, 0)
        should_send_15, notif_15 = should_send_notification(game_time, 15, current_time)

        should_send_60, notif_60 = should_send_notification(game_time, 60, current_time)

        assert should_send_15 is True
        assert should_send_60 is False
        assert notif_15 != notif_60
