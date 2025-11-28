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


"""Tests for notification daemon core logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from services.scheduler.notification_daemon import NotificationDaemon
from shared.models.notification_schedule import NotificationSchedule


class TestNotificationDaemon:
    """Test suite for NotificationDaemon."""

    def test_init_stores_configuration(self):
        """Daemon stores configuration parameters."""
        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
            max_timeout=600,
            buffer_seconds=20,
        )

        assert daemon.database_url == "postgresql://user:pass@host:5432/db"
        assert daemon.rabbitmq_url == "amqp://user:pass@host:5672/"
        assert daemon.max_timeout == 600
        assert daemon.buffer_seconds == 20

    def test_init_uses_default_values(self):
        """Daemon uses default values for optional parameters."""
        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
        )

        assert daemon.max_timeout == 300  # 5 minutes default
        assert daemon.buffer_seconds == 10  # 10 seconds default

    @patch("services.scheduler.notification_daemon.PostgresNotificationListener")
    @patch("services.scheduler.notification_daemon.SyncEventPublisher")
    @patch("services.scheduler.notification_daemon.SyncSessionLocal")
    def test_connect_establishes_connections(self, mock_session, mock_publisher, mock_listener):
        """Connect establishes database and message broker connections."""
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance

        mock_publisher_instance = MagicMock()
        mock_publisher.return_value = mock_publisher_instance

        mock_db_instance = MagicMock()
        mock_session.return_value = mock_db_instance

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
        )
        daemon.connect()

        # Verify PostgreSQL LISTEN connection
        mock_listener.assert_called_once_with("postgresql://user:pass@host:5432/db")
        mock_listener_instance.connect.assert_called_once()
        mock_listener_instance.listen.assert_called_once_with("notification_schedule_changed")

        # Verify RabbitMQ publisher connection
        mock_publisher_instance.connect.assert_called_once()

        # Verify database session created
        mock_session.assert_called_once()

    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    @patch("services.scheduler.notification_daemon.SyncSessionLocal")
    def test_process_loop_handles_no_notifications(self, mock_session, mock_get_next):
        """Process loop waits for max_timeout when no notifications scheduled."""
        mock_get_next.return_value = None

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
            max_timeout=300,
        )

        # Mock connections
        daemon.listener = MagicMock()
        daemon.listener.wait_for_notification.return_value = (False, None)
        daemon.publisher = MagicMock()
        daemon.db = MagicMock()

        daemon._process_loop_iteration()

        # Should wait for max_timeout when no notifications
        daemon.listener.wait_for_notification.assert_called_once()
        # Access keyword argument
        call_kwargs = daemon.listener.wait_for_notification.call_args.kwargs
        timeout = call_kwargs["timeout"]
        assert timeout == 300

    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    @patch("services.scheduler.notification_daemon.utc_now")
    def test_process_loop_processes_due_notification(self, mock_utc_now, mock_get_next):
        """Process loop immediately processes notification that is due."""
        now = datetime.now(UTC).replace(tzinfo=None)
        mock_utc_now.return_value = now

        # Notification is due (1 minute ago)
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=now - timedelta(minutes=1),
            sent=False,
        )
        mock_get_next.return_value = notification

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
        )

        daemon.listener = MagicMock()
        daemon.publisher = MagicMock()
        daemon.db = MagicMock()

        with patch.object(daemon, "_process_notification") as mock_process:
            daemon._process_loop_iteration()

            # Should process immediately without waiting
            mock_process.assert_called_once_with(notification)
            daemon.listener.wait_for_notification.assert_not_called()

    @patch("services.scheduler.notification_daemon.utc_now")
    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    def test_process_loop_waits_until_notification_due(self, mock_get_next, mock_utc_now):
        """Process loop waits until notification is due."""
        now = datetime.now(UTC).replace(tzinfo=None)
        mock_utc_now.return_value = now

        # Notification due in 2 hours
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=now + timedelta(hours=2),
            sent=False,
        )
        mock_get_next.return_value = notification

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
            buffer_seconds=10,
            max_timeout=300,
        )

        daemon.listener = MagicMock()
        daemon.listener.wait_for_notification.return_value = (False, None)
        daemon.publisher = MagicMock()
        daemon.db = MagicMock()

        daemon._process_loop_iteration()

        # Should wait until notification time minus buffer, capped at max_timeout
        daemon.listener.wait_for_notification.assert_called_once()
        call_kwargs = daemon.listener.wait_for_notification.call_args.kwargs
        timeout = call_kwargs["timeout"]

        # With 2 hours = 7200s and buffer 10s, expected 7190s
        # But capped at max_timeout of 300s
        assert timeout == 300

    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    @patch("services.scheduler.notification_daemon.mark_notification_sent")
    def test_process_notification_publishes_event(self, mock_mark_sent, mock_get_next):
        """Process notification publishes RabbitMQ event and marks as sent."""
        # Use valid UUID format
        game_uuid = "a1b2c3d4-e5f6-4789-a012-b34567890123"
        notif_uuid = "b2c3d4e5-f678-4901-a234-c56789012345"

        notification = NotificationSchedule(
            id=notif_uuid,
            game_id=game_uuid,
            reminder_minutes=60,
            notification_time=datetime.now(UTC).replace(tzinfo=None),
            sent=False,
        )

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
        )

        daemon.publisher = MagicMock()
        daemon.db = MagicMock()
        mock_mark_sent.return_value = True

        daemon._process_notification(notification)

        # Should publish event using publish_dict
        daemon.publisher.publish_dict.assert_called_once()
        call_kwargs = daemon.publisher.publish_dict.call_args.kwargs

        assert call_kwargs["event_type"] == "game.reminder_due"
        # game_id is UUID object in the data dict
        assert str(call_kwargs["data"]["game_id"]) == game_uuid
        assert call_kwargs["data"]["reminder_minutes"] == 60

        # Should mark notification as sent
        mock_mark_sent.assert_called_once_with(daemon.db, notif_uuid)
        daemon.db.commit.assert_called_once()

    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    @patch("services.scheduler.notification_daemon.mark_notification_sent")
    def test_process_notification_handles_publish_error(self, mock_mark_sent, mock_get_next):
        """Process notification handles RabbitMQ publish errors gracefully."""
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=datetime.now(UTC).replace(tzinfo=None),
            sent=False,
        )

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
        )

        daemon.publisher = MagicMock()
        daemon.publisher.publish.side_effect = Exception("RabbitMQ connection failed")
        daemon.db = MagicMock()

        # Should not raise exception
        daemon._process_notification(notification)

        # Should not mark as sent if publish failed
        mock_mark_sent.assert_not_called()
        daemon.db.rollback.assert_called_once()

    @patch("services.scheduler.notification_daemon.get_next_due_notification")
    def test_process_loop_respects_max_timeout(self, mock_get_next):
        """Process loop never waits longer than max_timeout."""
        now = datetime.now(UTC).replace(tzinfo=None)

        # Notification due in 10 hours
        notification = NotificationSchedule(
            id="test-id",
            game_id="game-123",
            reminder_minutes=60,
            notification_time=now + timedelta(hours=10),
            sent=False,
        )
        mock_get_next.return_value = notification

        daemon = NotificationDaemon(
            database_url="postgresql://user:pass@host:5432/db",
            rabbitmq_url="amqp://user:pass@host:5672/",
            max_timeout=300,  # 5 minutes max
        )

        daemon.listener = MagicMock()
        daemon.listener.wait_for_notification.return_value = (False, None)
        daemon.publisher = MagicMock()
        daemon.db = MagicMock()

        with patch("services.scheduler.notification_daemon.utc_now", return_value=now):
            daemon._process_loop_iteration()

        # Should cap wait time at max_timeout
        daemon.listener.wait_for_notification.assert_called_once()
        call_kwargs = daemon.listener.wait_for_notification.call_args.kwargs
        timeout = call_kwargs["timeout"]

        assert timeout <= 300
