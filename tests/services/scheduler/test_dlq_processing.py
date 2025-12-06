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


"""Unit tests for DLQ processing in generic scheduler daemon."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from services.scheduler.generic_scheduler_daemon import SchedulerDaemon
from shared.messaging.events import Event, EventType
from shared.models import NotificationSchedule


@pytest.fixture
def mock_event_builder():
    """Mock event builder function that returns proper (Event, TTL) tuples."""

    def builder(record):
        event = Event(
            event_type=EventType.GAME_REMINDER_DUE,
            data={"game_id": str(record.game_id), "reminder_minutes": record.reminder_minutes},
        )
        return event, None

    return builder


@pytest.fixture
def daemon(mock_event_builder):
    """Create SchedulerDaemon instance for testing."""
    return SchedulerDaemon(
        database_url="postgresql://test:test@localhost/test",
        rabbitmq_url="amqp://test:test@localhost/",
        notify_channel="test_channel",
        model_class=NotificationSchedule,
        time_field="notification_time",
        status_field="sent",
        event_builder=mock_event_builder,
        max_timeout=60,
    )


class TestDLQConfiguration:
    """Test DLQ configuration parameters."""

    def test_init_stores_dlq_configuration(self, mock_event_builder):
        """Daemon stores DLQ configuration parameters."""
        daemon = SchedulerDaemon(
            database_url="postgresql://test:test@localhost/test",
            rabbitmq_url="amqp://test:test@localhost/",
            notify_channel="test_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
            process_dlq=True,
            dlq_check_interval=600,
        )

        assert daemon.process_dlq is True
        assert daemon.dlq_check_interval == 600
        assert daemon.last_dlq_check == 0

    def test_init_defaults_dlq_to_disabled(self, mock_event_builder):
        """Daemon defaults to DLQ processing disabled."""
        daemon = SchedulerDaemon(
            database_url="postgresql://test:test@localhost/test",
            rabbitmq_url="amqp://test:test@localhost/",
            notify_channel="test_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
        )

        assert daemon.process_dlq is False
        assert daemon.dlq_check_interval == 900


class TestProcessDLQMessages:
    """Test _process_dlq_messages method."""

    @patch("services.scheduler.generic_scheduler_daemon.pika")
    def test_handles_empty_queue(self, mock_pika, daemon):
        """_process_dlq_messages returns early when DLQ is empty."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        mock_queue_state = MagicMock()
        mock_queue_state.method.message_count = 0
        mock_channel.queue_declare.return_value = mock_queue_state

        daemon._process_dlq_messages()

        mock_channel.queue_declare.assert_called_once_with(queue="DLQ", durable=True)
        mock_connection.close.assert_called_once()
        mock_channel.consume.assert_not_called()

    @patch("services.scheduler.generic_scheduler_daemon.pika")
    def test_republishes_messages(self, mock_pika, daemon):
        """_process_dlq_messages consumes and republishes DLQ messages."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_publisher = MagicMock()
        daemon.publisher = mock_publisher

        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        mock_queue_state = MagicMock()
        mock_queue_state.method.message_count = 2
        mock_channel.queue_declare.return_value = mock_queue_state

        event1_json = '{"event_type": "game.reminder_due", "data": {"game_id": "123"}}'
        event2_json = '{"event_type": "game.reminder_due", "data": {"game_id": "456"}}'

        mock_method1 = MagicMock()
        mock_method1.delivery_tag = "tag1"
        mock_method2 = MagicMock()
        mock_method2.delivery_tag = "tag2"

        mock_channel.consume.return_value = [
            (mock_method1, MagicMock(), event1_json.encode()),
            (mock_method2, MagicMock(), event2_json.encode()),
        ]

        daemon._process_dlq_messages()

        assert mock_publisher.publish.call_count == 2
        assert mock_channel.basic_ack.call_count == 2
        mock_channel.basic_ack.assert_any_call("tag1")
        mock_channel.basic_ack.assert_any_call("tag2")
        mock_channel.cancel.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch("services.scheduler.generic_scheduler_daemon.pika")
    def test_republishes_without_ttl(self, mock_pika, daemon):
        """_process_dlq_messages republishes messages with expiration_ms=None."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_publisher = MagicMock()
        daemon.publisher = mock_publisher

        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        mock_queue_state = MagicMock()
        mock_queue_state.method.message_count = 1
        mock_channel.queue_declare.return_value = mock_queue_state

        event_json = '{"event_type": "game.reminder_due", "data": {"game_id": "123"}}'
        mock_method = MagicMock()
        mock_method.delivery_tag = "tag1"

        mock_channel.consume.return_value = [
            (mock_method, MagicMock(), event_json.encode()),
        ]

        daemon._process_dlq_messages()

        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["expiration_ms"] is None

    @patch("services.scheduler.generic_scheduler_daemon.pika")
    def test_nacks_invalid_messages(self, mock_pika, daemon):
        """_process_dlq_messages NACKs messages that fail to parse."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_publisher = MagicMock()
        daemon.publisher = mock_publisher

        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        mock_queue_state = MagicMock()
        mock_queue_state.method.message_count = 1
        mock_channel.queue_declare.return_value = mock_queue_state

        invalid_json = b"not valid json"
        mock_method = MagicMock()
        mock_method.delivery_tag = "tag1"

        mock_channel.consume.return_value = [
            (mock_method, MagicMock(), invalid_json),
        ]

        daemon._process_dlq_messages()

        mock_publisher.publish.assert_not_called()
        mock_channel.basic_nack.assert_called_once_with("tag1", requeue=False)

    @patch("services.scheduler.generic_scheduler_daemon.pika")
    def test_handles_connection_error(self, mock_pika, daemon):
        """_process_dlq_messages handles RabbitMQ connection errors gracefully."""
        mock_pika.BlockingConnection.side_effect = Exception("Connection failed")

        daemon._process_dlq_messages()

        # Should not raise exception


class TestRunDLQIntegration:
    """Test DLQ processing integration in run() method."""

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    @patch("services.scheduler.generic_scheduler_daemon.SyncEventPublisher")
    @patch("services.scheduler.generic_scheduler_daemon.SyncSessionLocal")
    @patch("services.scheduler.generic_scheduler_daemon.time")
    def test_calls_dlq_processing_on_startup_when_enabled(
        self, mock_time, mock_session, mock_publisher_class, mock_listener_class, mock_event_builder
    ):
        """run() calls DLQ processing on startup when process_dlq=True."""
        daemon = SchedulerDaemon(
            database_url="postgresql://test:test@localhost/test",
            rabbitmq_url="amqp://test:test@localhost/",
            notify_channel="test_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
            process_dlq=True,
            dlq_check_interval=900,
        )

        mock_time.time.return_value = 1000.0
        shutdown_flag = Mock(side_effect=[False, True])

        with patch.object(daemon, "_process_dlq_messages") as mock_dlq:
            with patch.object(daemon, "_process_loop_iteration"):
                daemon.run(shutdown_flag)

        assert mock_dlq.call_count >= 1

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    @patch("services.scheduler.generic_scheduler_daemon.SyncEventPublisher")
    @patch("services.scheduler.generic_scheduler_daemon.SyncSessionLocal")
    @patch("services.scheduler.generic_scheduler_daemon.time")
    def test_calls_dlq_processing_periodically(
        self, mock_time, mock_session, mock_publisher_class, mock_listener_class, mock_event_builder
    ):
        """run() calls DLQ processing periodically based on dlq_check_interval."""
        daemon = SchedulerDaemon(
            database_url="postgresql://test:test@localhost/test",
            rabbitmq_url="amqp://test:test@localhost/",
            notify_channel="test_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
            process_dlq=True,
            dlq_check_interval=100,
        )

        # Simulate time passing
        time_values = [0.0, 50.0, 150.0]
        mock_time.time.side_effect = time_values + [200.0] * 10
        shutdown_flag = Mock(side_effect=[False, False, True])

        with patch.object(daemon, "_process_dlq_messages") as mock_dlq:
            with patch.object(daemon, "_process_loop_iteration"):
                daemon.run(shutdown_flag)

        # Should be called on startup (time=0) and after interval passes (time=150)
        assert mock_dlq.call_count >= 2

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    @patch("services.scheduler.generic_scheduler_daemon.SyncEventPublisher")
    @patch("services.scheduler.generic_scheduler_daemon.SyncSessionLocal")
    def test_skips_dlq_processing_when_disabled(
        self, mock_session, mock_publisher_class, mock_listener_class, mock_event_builder
    ):
        """run() does not call DLQ processing when process_dlq=False."""
        daemon = SchedulerDaemon(
            database_url="postgresql://test:test@localhost/test",
            rabbitmq_url="amqp://test:test@localhost/",
            notify_channel="test_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
            process_dlq=False,
        )

        shutdown_flag = Mock(side_effect=[False, True])

        with patch.object(daemon, "_process_dlq_messages") as mock_dlq:
            with patch.object(daemon, "_process_loop_iteration"):
                daemon.run(shutdown_flag)

        mock_dlq.assert_not_called()
