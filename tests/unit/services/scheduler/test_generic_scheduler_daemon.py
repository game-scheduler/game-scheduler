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


"""Unit tests for generic scheduler daemon.

Note: These are focused unit tests for error/edge cases.
Happy path scenarios are covered by integration tests.
"""

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import ANY, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from services.scheduler.generic_scheduler_daemon import SchedulerDaemon
from shared.messaging.events import Event, EventType
from shared.models import NotificationSchedule


@pytest.fixture
def mock_event_builder():
    """Mock event builder function that returns proper (Event, TTL) tuples."""

    def builder(record):
        event = Event(
            event_type=EventType.NOTIFICATION_DUE,
            data={
                "game_id": str(record.game_id),
                "reminder_minutes": record.reminder_minutes,
            },
        )
        return event, None

    return builder


@pytest.fixture
def daemon(mock_event_builder):
    """Create SchedulerDaemon instance for testing."""
    return SchedulerDaemon(
        service_name="test",
        database_url="postgresql://test:test@localhost/test",
        rabbitmq_url="amqp://test:test@localhost/",
        notify_channel="test_channel",
        model_class=NotificationSchedule,
        time_field="notification_time",
        status_field="sent",
        event_builder=mock_event_builder,
        max_timeout=60,
    )


class TestSchedulerDaemonInitialization:
    """Test daemon initialization."""

    def test_init_stores_all_configuration_parameters(self, mock_event_builder):
        """Daemon stores all configuration parameters correctly."""
        daemon = SchedulerDaemon(
            service_name="test",
            database_url="postgresql://user:pass@host/db",
            rabbitmq_url="amqp://user:pass@host/",
            notify_channel="my_channel",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=mock_event_builder,
            max_timeout=900,
        )

        assert daemon.database_url == "postgresql://user:pass@host/db"
        assert daemon.rabbitmq_url == "amqp://user:pass@host/"
        assert daemon.notify_channel == "my_channel"
        assert daemon.model_class == NotificationSchedule
        assert daemon.time_field == "notification_time"
        assert daemon.status_field == "sent"
        assert daemon.event_builder == mock_event_builder
        assert daemon.max_timeout == 900

    def test_init_resources_start_as_none(self, daemon):
        """Daemon initializes with no active connections."""
        assert daemon.listener is None
        assert daemon.publisher is None
        assert daemon.db is None


class TestSchedulerDaemonConnect:
    """Test connection establishment."""

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    @patch("services.scheduler.generic_scheduler_daemon.SyncEventPublisher")
    @patch("services.scheduler.generic_scheduler_daemon.SyncSessionLocal")
    def test_connect_establishes_all_connections_correctly(
        self, mock_session_local, mock_publisher_class, mock_listener_class, daemon
    ):
        """connect() establishes PostgreSQL listener, RabbitMQ publisher, and DB session."""
        mock_listener = MagicMock()
        mock_publisher = MagicMock()
        mock_db = MagicMock()

        mock_listener_class.return_value = mock_listener
        mock_publisher_class.return_value = mock_publisher
        mock_session_local.return_value = mock_db

        daemon.connect()

        # Verify PostgreSQL listener setup
        mock_listener_class.assert_called_once_with(daemon.database_url)
        mock_listener.connect.assert_called_once_with()  # assert-no-args
        mock_listener.listen.assert_called_once_with("test_channel")

        # Verify RabbitMQ publisher setup
        mock_publisher_class.assert_called_once_with()  # assert-no-args
        mock_publisher.connect.assert_called_once_with()  # assert-no-args

        # Verify database session created
        mock_session_local.assert_called_once_with()  # assert-no-args

        # Verify connections stored
        assert daemon.listener == mock_listener
        assert daemon.publisher == mock_publisher
        assert daemon.db == mock_db

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    def test_connect_raises_when_postgres_connection_fails(self, mock_listener_class, daemon):
        """connect() propagates exception when PostgreSQL connection fails."""
        mock_listener_class.side_effect = Exception("PostgreSQL connection refused")

        with pytest.raises(Exception, match="PostgreSQL connection refused"):
            daemon.connect()

    @patch("services.scheduler.generic_scheduler_daemon.PostgresNotificationListener")
    @patch("services.scheduler.generic_scheduler_daemon.SyncEventPublisher")
    def test_connect_raises_when_rabbitmq_connection_fails(
        self, mock_publisher_class, mock_listener_class, daemon
    ):
        """connect() propagates exception when RabbitMQ connection fails."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        mock_publisher = MagicMock()
        mock_publisher.connect.side_effect = Exception("RabbitMQ connection refused")
        mock_publisher_class.return_value = mock_publisher

        with pytest.raises(Exception, match="RabbitMQ connection refused"):
            daemon.connect()


class TestSchedulerDaemonGetNextDueItem:
    """Test _get_next_due_item query logic."""

    def test_get_next_due_item_raises_when_db_not_initialized(self, daemon):
        """_get_next_due_item raises RuntimeError when db is None."""
        daemon.db = None

        with pytest.raises(RuntimeError, match="Database session not initialized"):
            daemon._get_next_due_item()

    def test_get_next_due_item_queries_with_correct_filters(self, daemon):
        """_get_next_due_item queries for unprocessed items with non-null times."""
        mock_db = MagicMock()
        daemon.db = mock_db

        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_order = MagicMock()

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value = mock_order
        mock_order.first.return_value = None

        daemon._get_next_due_item()

        # Verify query constructed correctly
        mock_db.query.assert_called_once_with(NotificationSchedule)
        assert mock_query.filter.call_count == 1
        assert mock_filter1.filter.call_count == 1
        mock_filter2.order_by.assert_called_once_with(ANY)
        mock_order.first.assert_called_once_with()  # assert-no-args

    def test_get_next_due_item_returns_record_when_found(self, daemon):
        """_get_next_due_item returns the record when one exists."""
        mock_db = MagicMock()
        daemon.db = mock_db

        mock_record = MagicMock()
        mock_record.id = str(uuid4())
        mock_record.notification_time = datetime.now(UTC).replace(tzinfo=None)
        (
            mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value
        ) = mock_record

        result = daemon._get_next_due_item()

        assert result == mock_record

    def test_get_next_due_item_returns_none_when_no_records(self, daemon):
        """_get_next_due_item returns None when no records exist."""
        mock_db = MagicMock()
        daemon.db = mock_db
        (
            mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value
        ) = None

        result = daemon._get_next_due_item()

        assert result is None


class TestSchedulerDaemonMarkItemProcessed:
    """Test _mark_item_processed logic."""

    def test_mark_item_processed_raises_when_db_not_initialized(self, daemon):
        """_mark_item_processed raises RuntimeError when db is None."""
        daemon.db = None

        with pytest.raises(RuntimeError, match="Database session not initialized"):
            daemon._mark_item_processed(str(uuid4()))

    def test_mark_item_processed_sets_status_field_to_true(self, daemon):
        """_mark_item_processed sets the status field to True."""
        mock_db = MagicMock()
        daemon.db = mock_db

        item_id = str(uuid4())
        mock_item = MagicMock()
        mock_item.sent = False
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        daemon._mark_item_processed(item_id)

        mock_db.query.assert_called_once_with(NotificationSchedule)
        mock_db.query.return_value.filter_by.assert_called_once_with(id=item_id)
        assert mock_item.sent is True

    def test_mark_item_processed_handles_item_not_found(self, daemon):
        """_mark_item_processed doesn't fail when item not found."""
        mock_db = MagicMock()
        daemon.db = mock_db
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        # Should not raise
        daemon._mark_item_processed(str(uuid4()))

        mock_db.commit.assert_not_called()


class TestSchedulerDaemonProcessItem:
    """Test _process_item event publishing and marking."""

    def test_process_item_raises_when_not_initialized(self, daemon):
        """_process_item raises RuntimeError when publisher or db is None."""
        daemon.publisher = None
        daemon.db = None
        mock_item = MagicMock()

        with pytest.raises(RuntimeError, match="Daemon not properly initialized"):
            daemon._process_item(mock_item)

    def test_process_item_builds_event_publishes_and_marks_processed(self, daemon):
        """_process_item builds event, publishes it, marks item processed, and commits."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        item_id = str(uuid4())
        game_id = str(uuid4())
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.game_id = game_id
        mock_item.reminder_minutes = 60
        mock_item.sent = False

        # Mock the DB query to return the mock_item so _mark_item_processed can set its field
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        daemon._process_item(mock_item)

        # Verify event published
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["event"].event_type == EventType.NOTIFICATION_DUE
        assert game_id in str(call_args[1]["event"].data)
        assert call_args[1]["expiration_ms"] is None

        # Verify item marked as processed
        assert mock_item.sent is True

        # Verify committed
        mock_db.commit.assert_called_once()

    def test_process_item_rolls_back_on_publish_failure(self, daemon):
        """_process_item rolls back transaction when publishing fails."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        mock_publisher.publish.side_effect = Exception("RabbitMQ unavailable")

        mock_item = MagicMock()
        mock_item.id = str(uuid4())
        mock_item.game_id = str(uuid4())
        mock_item.reminder_minutes = 60

        daemon._process_item(mock_item)

        # Should rollback, not commit
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    def test_process_item_rolls_back_on_event_builder_failure(self, daemon):
        """_process_item rolls back when event_builder raises exception."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher
        daemon.event_builder = Mock(side_effect=Exception("Builder failed"))

        mock_item = MagicMock()
        mock_item.id = str(uuid4())

        daemon._process_item(mock_item)

        # Should rollback, not commit
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()
        # Should not attempt to publish
        mock_publisher.publish.assert_not_called()

    def test_process_item_rolls_back_on_commit_failure(self, daemon):
        """_process_item rolls back when commit fails."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        mock_db.commit.side_effect = Exception("Commit failed")

        mock_item = MagicMock()
        mock_item.id = str(uuid4())
        mock_item.game_id = str(uuid4())
        mock_item.reminder_minutes = 60

        daemon._process_item(mock_item)

        # Should call rollback after commit fails
        mock_db.rollback.assert_called_once()


class TestSchedulerDaemonProcessLoopIteration:
    """Test _process_loop_iteration main logic."""

    def test_process_loop_iteration_raises_when_not_initialized(self, daemon):
        """_process_loop_iteration raises RuntimeError when listener or db is None."""
        daemon.listener = None
        daemon.db = None

        with pytest.raises(RuntimeError, match="Daemon not properly initialized"):
            daemon._process_loop_iteration()

    @patch("services.scheduler.generic_scheduler_daemon.utc_now")
    @patch.object(SchedulerDaemon, "_get_next_due_item")
    @patch.object(SchedulerDaemon, "_process_item")
    def test_process_loop_iteration_processes_due_item_immediately(
        self, mock_process, mock_get_next, mock_utc_now, daemon
    ):
        """_process_loop_iteration processes item immediately when due."""
        mock_db = MagicMock()
        mock_listener = MagicMock()
        daemon.db = mock_db
        daemon.listener = mock_listener

        current_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        past_time = datetime(2025, 1, 1, 11, 59, 30, tzinfo=UTC)  # 30 seconds ago
        mock_utc_now.return_value = current_time

        mock_item = MagicMock()
        mock_item.notification_time = past_time
        mock_get_next.return_value = mock_item

        daemon._process_loop_iteration()

        # Should process the item
        mock_process.assert_called_once_with(mock_item)
        # Should NOT wait
        mock_listener.wait_for_notification.assert_not_called()

    @patch("services.scheduler.generic_scheduler_daemon.utc_now")
    @patch.object(SchedulerDaemon, "_get_next_due_item")
    def test_process_loop_iteration_waits_for_future_item(
        self, mock_get_next, mock_utc_now, daemon
    ):
        """_process_loop_iteration waits until scheduled time for future item."""
        mock_listener = MagicMock()
        mock_listener.wait_for_notification.return_value = (False, None)
        daemon.listener = mock_listener
        daemon.db = MagicMock()

        current_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        future_time = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)  # 10 seconds in future
        mock_utc_now.return_value = current_time

        mock_item = MagicMock()
        mock_item.notification_time = future_time
        mock_get_next.return_value = mock_item

        daemon._process_loop_iteration()

        # Should wait for the item
        mock_listener.wait_for_notification.assert_called_once()
        timeout = mock_listener.wait_for_notification.call_args[1]["timeout"]
        # Should wait approximately 10 seconds (allow 2 second tolerance)
        assert 8 <= timeout <= 12

    @patch.object(SchedulerDaemon, "_get_next_due_item")
    def test_process_loop_iteration_waits_max_timeout_when_no_items(self, mock_get_next, daemon):
        """_process_loop_iteration waits max_timeout when no items scheduled."""
        mock_listener = MagicMock()
        mock_listener.wait_for_notification.return_value = (False, None)
        daemon.listener = mock_listener
        daemon.db = MagicMock()
        daemon.max_timeout = 120

        mock_get_next.return_value = None

        daemon._process_loop_iteration()

        # Should wait max_timeout
        mock_listener.wait_for_notification.assert_called_once()
        timeout = mock_listener.wait_for_notification.call_args[1]["timeout"]
        assert timeout == 120

    @patch.object(SchedulerDaemon, "_get_next_due_item")
    def test_process_loop_iteration_caps_wait_at_max_timeout(self, mock_get_next, daemon):
        """_process_loop_iteration caps wait time at max_timeout for far future items."""
        mock_listener = MagicMock()
        mock_listener.wait_for_notification.return_value = (False, None)
        daemon.listener = mock_listener
        daemon.db = MagicMock()
        daemon.max_timeout = 60

        far_future = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
        mock_item = MagicMock()
        mock_item.notification_time = far_future
        mock_get_next.return_value = mock_item

        daemon._process_loop_iteration()

        # Should wait max_timeout, not 2 hours
        timeout = mock_listener.wait_for_notification.call_args[1]["timeout"]
        assert timeout == 60

    @patch("services.scheduler.generic_scheduler_daemon.SyncSessionLocal")
    def test_process_loop_iteration_recreates_session_on_query_failure(
        self, mock_session_local, daemon
    ):
        """_process_loop_iteration recreates DB session when query fails."""
        mock_db = MagicMock()
        mock_listener = MagicMock()
        mock_listener.wait_for_notification.return_value = (False, None)
        daemon.db = mock_db
        daemon.listener = mock_listener
        daemon.max_timeout = 1  # Short timeout

        new_session = MagicMock()
        (
            new_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value
        ) = None
        mock_session_local.return_value = new_session

        # Make first query fail
        mock_db.query.side_effect = Exception("Connection lost")

        daemon._process_loop_iteration()

        # Should close old session and create new one
        mock_db.close.assert_called_once()
        mock_session_local.assert_called_once_with()  # assert-no-args
        # New session should be assigned
        assert daemon.db == new_session

    @patch.object(SchedulerDaemon, "_get_next_due_item")
    def test_process_loop_iteration_logs_notify_event(self, mock_get_next, daemon):
        """_process_loop_iteration logs when woken by PostgreSQL NOTIFY."""
        mock_listener = MagicMock()
        mock_listener.wait_for_notification.return_value = (True, "test_notification")
        daemon.listener = mock_listener
        daemon.db = MagicMock()
        daemon.max_timeout = 60

        mock_get_next.return_value = None

        daemon._process_loop_iteration()

        mock_listener.wait_for_notification.assert_called_once_with(timeout=60)


class TestSchedulerDaemonRun:
    """Test main run loop."""

    @patch.object(SchedulerDaemon, "connect")
    @patch.object(SchedulerDaemon, "_process_loop_iteration")
    @patch.object(SchedulerDaemon, "_cleanup")
    def test_run_connects_loops_and_cleans_up(
        self, mock_cleanup, mock_iteration, mock_connect, daemon
    ):
        """run() connects, processes iterations until shutdown, then cleans up."""
        call_count = [0]

        def shutdown_after_three():
            call_count[0] += 1
            return call_count[0] > 3

        daemon.run(shutdown_after_three)

        mock_connect.assert_called_once_with()  # assert-no-args
        assert mock_iteration.call_count == 3
        mock_cleanup.assert_called_once_with()  # assert-no-args

    @patch.object(SchedulerDaemon, "connect")
    @patch.object(SchedulerDaemon, "_process_loop_iteration")
    @patch.object(SchedulerDaemon, "_cleanup")
    def test_run_continues_after_iteration_error(
        self, mock_cleanup, mock_iteration, mock_connect, daemon
    ):
        """run() continues looping after iteration errors."""
        call_count = [0]

        def shutdown_after_three():
            call_count[0] += 1
            return call_count[0] > 3

        # First iteration raises, second and third succeed
        mock_iteration.side_effect = [
            Exception("Temporary error"),
            None,
            None,
        ]

        daemon.run(shutdown_after_three)

        # Should continue despite error
        assert mock_iteration.call_count == 3
        mock_cleanup.assert_called_once_with()  # assert-no-args

    @patch.object(SchedulerDaemon, "connect")
    @patch.object(SchedulerDaemon, "_process_loop_iteration")
    @patch.object(SchedulerDaemon, "_cleanup")
    def test_run_rolls_back_on_iteration_error(
        self, mock_cleanup, mock_iteration, mock_connect, daemon
    ):
        """run() rolls back database when iteration raises."""
        mock_db = MagicMock()
        daemon.db = mock_db

        call_count = [0]

        def shutdown_after_one():
            call_count[0] += 1
            return call_count[0] > 1

        mock_iteration.side_effect = Exception("Error")

        daemon.run(shutdown_after_one)

        # Should roll back after error
        mock_db.rollback.assert_called()

    @patch.object(SchedulerDaemon, "connect")
    @patch.object(SchedulerDaemon, "_process_loop_iteration")
    @patch.object(SchedulerDaemon, "_cleanup")
    def test_run_stops_on_keyboard_interrupt(
        self, mock_cleanup, mock_iteration, mock_connect, daemon
    ):
        """run() stops cleanly on KeyboardInterrupt."""
        mock_iteration.side_effect = KeyboardInterrupt()

        daemon.run(lambda: False)

        mock_connect.assert_called_once_with()  # assert-no-args
        mock_cleanup.assert_called_once_with()  # assert-no-args


class TestSchedulerDaemonCleanup:
    """Test cleanup logic."""

    def test_cleanup_closes_all_connections(self, daemon):
        """_cleanup closes listener, publisher, and db connections."""
        mock_listener = MagicMock()
        mock_publisher = MagicMock()
        mock_db = MagicMock()

        daemon.listener = mock_listener
        daemon.publisher = mock_publisher
        daemon.db = mock_db

        daemon._cleanup()

        mock_listener.close.assert_called_once()
        mock_publisher.close.assert_called_once()
        mock_db.close.assert_called_once()

    def test_cleanup_handles_none_connections_gracefully(self, daemon):
        """_cleanup doesn't fail when connections are None."""
        daemon.listener = None
        daemon.publisher = None
        daemon.db = None

        # Should not raise
        daemon._cleanup()

        assert daemon.listener is None
        assert daemon.publisher is None
        assert daemon.db is None

    def test_cleanup_continues_if_close_raises(self, daemon):
        """_cleanup continues closing other connections if one fails."""
        mock_listener = MagicMock()
        mock_publisher = MagicMock()
        mock_db = MagicMock()

        mock_listener.close.side_effect = Exception("Close failed")

        daemon.listener = mock_listener
        daemon.publisher = mock_publisher
        daemon.db = mock_db

        # Should not raise, should continue
        daemon._cleanup()

        # All close() should be attempted
        mock_listener.close.assert_called_once()
        mock_publisher.close.assert_called_once()
        mock_db.close.assert_called_once()

    def test_cleanup_continues_if_publisher_close_raises(self, daemon):
        """_cleanup continues when publisher close raises."""
        mock_listener = MagicMock()
        mock_publisher = MagicMock()
        mock_db = MagicMock()
        mock_publisher.close.side_effect = Exception("Publisher close failed")

        daemon.listener = mock_listener
        daemon.publisher = mock_publisher
        daemon.db = mock_db

        daemon._cleanup()

        mock_listener.close.assert_called_once()
        mock_publisher.close.assert_called_once()
        mock_db.close.assert_called_once()

    def test_cleanup_continues_if_db_close_raises(self, daemon):
        """_cleanup completes gracefully when database close raises."""
        mock_listener = MagicMock()
        mock_publisher = MagicMock()
        mock_db = MagicMock()
        mock_db.close.side_effect = Exception("DB close failed")

        daemon.listener = mock_listener
        daemon.publisher = mock_publisher
        daemon.db = mock_db

        daemon._cleanup()

        mock_listener.close.assert_called_once()
        mock_publisher.close.assert_called_once()
        mock_db.close.assert_called_once()


class TestSchedulerDaemonTupleHandling:
    """Test daemon handling of event builder tuple returns."""

    def test_process_item_handles_tuple_return_with_ttl(self, daemon):
        """_process_item correctly unpacks tuple with TTL and passes to publisher."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        ttl_value = 30000

        def builder_with_ttl(record):
            event = Event(
                event_type=EventType.NOTIFICATION_DUE,
                data={"game_id": str(record.game_id)},
            )
            return event, ttl_value

        daemon.event_builder = builder_with_ttl

        item_id = str(uuid4())
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.game_id = str(uuid4())
        mock_item.sent = False

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        daemon._process_item(mock_item)

        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["expiration_ms"] == ttl_value

    def test_process_item_handles_tuple_return_with_none_ttl(self, daemon):
        """_process_item correctly unpacks tuple with None TTL."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        def builder_no_ttl(record):
            event = Event(
                event_type=EventType.GAME_STATUS_TRANSITION_DUE,
                data={"game_id": str(record.game_id)},
            )
            return event, None

        daemon.event_builder = builder_no_ttl

        item_id = str(uuid4())
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.game_id = str(uuid4())
        mock_item.sent = False

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        daemon._process_item(mock_item)

        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["expiration_ms"] is None

    def test_process_item_handles_legacy_single_event_return(self, daemon):
        """_process_item handles legacy event builders returning just Event."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        def legacy_builder(record):
            return Event(
                event_type=EventType.NOTIFICATION_DUE,
                data={"game_id": str(record.game_id)},
            )

        daemon.event_builder = legacy_builder

        item_id = str(uuid4())
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.game_id = str(uuid4())
        mock_item.sent = False

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        daemon._process_item(mock_item)

        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["expiration_ms"] is None


class TestSchedulerDaemonServiceName:
    """Tests for service_name attribution in log messages and OTel spans."""

    @patch.object(SchedulerDaemon, "connect")
    @patch.object(SchedulerDaemon, "_cleanup")
    def test_run_log_includes_service_name(self, mock_cleanup, mock_connect, daemon, caplog):
        """run() startup log message contains the service_name in brackets."""
        with caplog.at_level(logging.INFO, logger="services.scheduler.generic_scheduler_daemon"):
            daemon.run(lambda: True)

        assert "[test]" in caplog.text

    def test_process_item_span_includes_service_name_attribute(self, daemon):
        """_process_item OTel span attributes include scheduler.service_name."""
        mock_db = MagicMock()
        mock_publisher = MagicMock()
        daemon.db = mock_db
        daemon.publisher = mock_publisher

        mock_item = MagicMock()
        mock_item.id = str(uuid4())
        mock_item.game_id = str(uuid4())
        mock_item.reminder_minutes = 60
        mock_item.sent = False
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

        with patch("services.scheduler.generic_scheduler_daemon.tracer") as mock_tracer:
            mock_span_ctx = MagicMock()
            mock_span_ctx.__enter__ = Mock(return_value=mock_span_ctx)
            mock_span_ctx.__exit__ = Mock(return_value=False)
            mock_tracer.start_as_current_span.return_value = mock_span_ctx

            daemon._process_item(mock_item)

        mock_tracer.start_as_current_span.assert_called_once_with(ANY, attributes=ANY)
        call_kwargs = mock_tracer.start_as_current_span.call_args
        attributes = call_kwargs.kwargs.get("attributes", {})
        assert "scheduler.service_name" in attributes
        assert attributes["scheduler.service_name"] == "test"
