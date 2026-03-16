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


"""Unit tests for NotificationService.send_game_reminder_due()."""

import uuid
from unittest.mock import MagicMock

from services.scheduler.services.notification_service import (
    NotificationService,
    get_notification_service,
)


class TestSendGameReminderDue:
    """Tests for NotificationService.send_game_reminder_due."""

    def test_happy_path_returns_true(self):
        """Publisher connects, publishes, closes; method returns True."""
        service = NotificationService()
        mock_publisher = MagicMock()
        service.event_publisher = mock_publisher

        result = service.send_game_reminder_due(uuid.uuid4(), reminder_minutes=60)

        assert result is True
        mock_publisher.connect.assert_called_once()
        mock_publisher.publish.assert_called_once()
        mock_publisher.close.assert_called_once()

    def test_exception_during_publish_returns_false_and_closes(self):
        """publish() raises; method returns False but close() still called."""
        service = NotificationService()
        mock_publisher = MagicMock()
        mock_publisher.publish.side_effect = RuntimeError("broker unavailable")
        service.event_publisher = mock_publisher

        result = service.send_game_reminder_due(uuid.uuid4(), reminder_minutes=30)

        assert result is False
        mock_publisher.connect.assert_called_once()
        mock_publisher.close.assert_called_once()

    def test_exception_during_connect_returns_false(self):
        """connect() raises before publish; method returns False."""
        service = NotificationService()
        mock_publisher = MagicMock()
        mock_publisher.connect.side_effect = ConnectionError("no route to host")
        service.event_publisher = mock_publisher

        result = service.send_game_reminder_due(uuid.uuid4(), reminder_minutes=15)

        assert result is False
        mock_publisher.publish.assert_not_called()
        mock_publisher.close.assert_called_once()


class TestGetNotificationService:
    """Tests for get_notification_service factory."""

    def test_returns_notification_service_instance(self):
        """Factory returns a NotificationService."""
        result = get_notification_service()
        assert isinstance(result, NotificationService)
