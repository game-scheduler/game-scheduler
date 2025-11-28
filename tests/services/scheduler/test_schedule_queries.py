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


"""Tests for notification schedule query functions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, Mock

from services.scheduler.schedule_queries import (
    get_next_due_notification,
    mark_notification_sent,
)
from shared.models.notification_schedule import NotificationSchedule


class TestGetNextDueNotification:
    """Test suite for get_next_due_notification function."""

    def test_returns_earliest_unsent_notification(self):
        """Returns notification with earliest notification_time."""
        mock_db = MagicMock()

        # Create mock notification
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            sent=False,
        )

        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = notification
        mock_db.execute.return_value = mock_result

        result = get_next_due_notification(mock_db)

        assert result == notification
        mock_db.execute.assert_called_once()

    def test_returns_none_when_no_notifications(self):
        """Returns None when no unsent notifications exist."""
        mock_db = MagicMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = get_next_due_notification(mock_db)

        assert result is None

    def test_includes_overdue_notifications(self):
        """Returns overdue notifications for daemon recovery."""
        mock_db = MagicMock()

        # Notification in the past
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
            sent=False,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = notification
        mock_db.execute.return_value = mock_result

        result = get_next_due_notification(mock_db)

        assert result is not None
        assert result == notification
        assert notification.notification_time < datetime.now(UTC).replace(tzinfo=None)

    def test_filters_sent_notifications(self):
        """Only returns unsent notifications (sent=False)."""
        mock_db = MagicMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        get_next_due_notification(mock_db)

        # Verify query filters by sent=False
        call_args = mock_db.execute.call_args
        query = call_args[0][0]
        # Query should contain WHERE clause for sent=False
        assert "sent" in str(query).lower()


class TestMarkNotificationSent:
    """Test suite for mark_notification_sent function."""

    def test_marks_notification_as_sent(self):
        """Updates notification sent status to True."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        notification_id = "test-notification-id"

        result = mark_notification_sent(mock_db, notification_id)

        # Verify execute was called with UPDATE statement
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result is True

    def test_returns_false_when_no_rows_updated(self):
        """Returns False when notification not found."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        notification_id = "test-notification-id"

        result = mark_notification_sent(mock_db, notification_id)

        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result is False

    def test_handles_nonexistent_notification(self):
        """Gracefully handles marking nonexistent notification."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        # Should not raise error
        result = mark_notification_sent(mock_db, "nonexistent-id")

        assert result is False
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()
