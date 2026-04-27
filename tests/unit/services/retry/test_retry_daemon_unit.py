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


"""Unit tests for RetryDaemon class."""

from collections import namedtuple
from unittest.mock import ANY, Mock, patch

import pytest

from services.retry.retry_daemon import RetryDaemon
from shared.messaging.events import Event, EventType
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS_DLQ, QUEUE_NOTIFICATION_DLQ


class TestRetryDaemon:
    """Test suite for RetryDaemon class."""

    @pytest.fixture
    def daemon(self):
        """Create RetryDaemon instance for testing."""
        return RetryDaemon(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            retry_interval_seconds=60,
        )

    def test_init(self, daemon):
        """Test RetryDaemon initialization."""
        assert daemon.rabbitmq_url == "amqp://guest:guest@localhost:5672/"
        assert daemon.retry_interval == 60
        assert daemon.publisher is None
        assert daemon.dlq_names == [QUEUE_BOT_EVENTS_DLQ, QUEUE_NOTIFICATION_DLQ]

    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_connect(self, mock_publisher_class, daemon):
        """Test connection establishment."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        daemon.connect()

        mock_publisher_class.assert_called_once_with()  # assert-not-weak: predates reason
        mock_publisher.connect.assert_called_once_with()
        assert daemon.publisher == mock_publisher

    def test_get_routing_key_from_x_death(self, daemon):
        """Test routing key extraction from x-death header."""
        properties = Mock()
        properties.headers = {
            "x-death": [
                {
                    "queue": "bot_events",
                    "reason": "expired",
                    "routing-keys": ["game.created"],
                }
            ]
        }
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "game.created"

    def test_get_routing_key_from_properties(self, daemon):
        """Test routing key extraction from message properties when x-death missing."""
        properties = Mock()
        properties.headers = None
        properties.routing_key = "notification.send_dm"

        result = daemon._get_routing_key(properties)

        assert result == "notification.send_dm"

    def test_get_routing_key_unknown_fallback(self, daemon):
        """Test routing key fallback to 'unknown' when both sources missing."""
        properties = Mock()
        properties.headers = None
        properties.routing_key = None

        result = daemon._get_routing_key(properties)

        assert result == "unknown"

    def test_get_routing_key_with_empty_x_death(self, daemon):
        """Test routing key extraction when x-death exists but is empty."""
        properties = Mock()
        properties.headers = {"x-death": []}
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "fallback.key"

    def test_get_routing_key_with_empty_routing_keys(self, daemon):
        """Test routing key extraction when x-death has no routing-keys."""
        properties = Mock()
        properties.headers = {
            "x-death": [
                {
                    "queue": "bot_events",
                    "reason": "expired",
                    "routing-keys": [],
                }
            ]
        }
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "fallback.key"

    def test_process_dlq_empty_queue(self, daemon, caplog):
        """Test processing of empty DLQ."""
        with caplog.at_level("DEBUG"):
            with patch("pika.BlockingConnection") as mock_connection_class:
                # Mock connection and channel
                mock_connection = Mock()
                mock_channel = Mock()
                mock_connection_class.return_value = mock_connection
                mock_connection.channel.return_value = mock_channel

                # Mock queue state showing empty queue
                Method = namedtuple("Method", ["message_count"])
                mock_queue_state = Mock()
                mock_queue_state.method = Method(message_count=0)
                mock_channel.queue_declare.return_value = mock_queue_state

                daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

                mock_channel.queue_declare.assert_called_once_with(
                    queue=QUEUE_BOT_EVENTS_DLQ, durable=True
                )
                mock_connection.close.assert_called_once()
                mock_connection_class.assert_called_once_with(ANY)
                assert "is empty, nothing to process" in caplog.text

    def test_process_dlq_with_messages(self, daemon):
        """Test processing DLQ with messages."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            # Create mock publisher
            mock_publisher = Mock()
            daemon.publisher = mock_publisher

            # Mock connection and channel
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            # Mock queue state showing 2 messages
            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=2, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            # Mock message properties
            mock_properties1 = Mock()
            mock_properties1.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_properties1.routing_key = "game.created"

            mock_properties2 = Mock()
            mock_properties2.headers = {"x-death": [{"routing-keys": ["game.updated"]}]}
            mock_properties2.routing_key = "game.updated"

            # Create valid Event messages
            event1 = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )
            event2 = Event(
                event_type=EventType.GAME_UPDATED,
                data={"game_id": "456"},
            )

            # Mock consume to return 2 messages
            mock_method1 = Method(message_count=2, delivery_tag=1)
            mock_method2 = Method(message_count=2, delivery_tag=2)
            mock_channel.consume.return_value = [
                (mock_method1, mock_properties1, event1.model_dump_json()),
                (mock_method2, mock_properties2, event2.model_dump_json()),
            ]

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            assert mock_publisher.publish.call_count == 2
            mock_channel.basic_ack.assert_any_call(1)
            mock_channel.basic_ack.assert_any_call(2)
            mock_channel.cancel.assert_called_once_with()  # assert-not-weak: predates reason
            mock_connection.close.assert_called_once()
            mock_connection_class.assert_called_once_with(ANY)

    def test_process_dlq_with_publish_error(self, daemon):
        """Test error handling when republish fails."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            # Create mock publisher that raises error
            mock_publisher = Mock()
            mock_publisher.publish.side_effect = Exception("Publish failed")
            daemon.publisher = mock_publisher

            # Mock connection and channel
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            # Mock queue state showing 1 message
            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=1, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            # Mock message properties
            mock_properties = Mock()
            mock_properties.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_properties.routing_key = "game.created"

            # Create valid Event message
            event = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )

            # Mock consume to return 1 message
            mock_method = Method(message_count=1, delivery_tag=1)
            mock_channel.consume.return_value = [
                (mock_method, mock_properties, event.model_dump_json()),
            ]

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            # Should NACK with requeue when publish fails
            mock_channel.basic_nack.assert_called_once_with(1, requeue=True)
            mock_connection.close.assert_called_once()
            mock_connection_class.assert_called_once_with(ANY)

    def test_process_dlq_connection_error(self, daemon, caplog):
        """Test error handling when connection fails."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection_class.side_effect = Exception("Connection failed")

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            assert "Error during DLQ processing" in caplog.text
            mock_connection_class.assert_called_once_with(ANY)

    def test_cleanup(self, daemon):
        """Test cleanup closes publisher connection."""
        mock_publisher = Mock()
        daemon.publisher = mock_publisher

        daemon._cleanup()

        mock_publisher.close.assert_called_once()

    def test_cleanup_with_error(self, daemon, caplog):
        """Test cleanup handles publisher close errors."""
        mock_publisher = Mock()
        mock_publisher.close.side_effect = Exception("Close failed")
        daemon.publisher = mock_publisher

        daemon._cleanup()

        assert "Error closing publisher" in caplog.text

    def test_cleanup_without_publisher(self, daemon):
        """Test cleanup when publisher is None."""
        daemon.publisher = None

        daemon._cleanup()

        assert daemon.publisher is None

    @patch("services.retry.retry_daemon.time")
    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop(self, mock_publisher_class, mock_time, daemon):
        """Test main daemon run loop."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        # Shutdown after processing both DLQs once
        iteration_count = [0]

        def shutdown_after_first_iteration():
            # Called at start of while loop, before processing
            return iteration_count[0] > 0

        def sleep_side_effect(duration):
            # Increment counter after sleep (end of iteration)
            iteration_count[0] += 1

        mock_time.sleep.side_effect = sleep_side_effect

        with patch.object(daemon, "_process_dlq") as mock_process:
            daemon.run(shutdown_after_first_iteration)

            # Should process both DLQs once
            assert mock_process.call_count == 2  # 1 iteration * 2 DLQs
            mock_process.assert_any_call(QUEUE_BOT_EVENTS_DLQ)
            mock_process.assert_any_call(QUEUE_NOTIFICATION_DLQ)

    @patch("services.retry.retry_daemon.time")
    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop_handles_exceptions(self, mock_publisher_class, mock_time, daemon):
        """Test run loop continues after exceptions."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        iteration_count = [0]

        def shutdown_after_iterations():
            # Shutdown after 2 complete iterations
            return iteration_count[0] >= 2

        def sleep_side_effect(duration):
            iteration_count[0] += 1

        mock_time.sleep.side_effect = sleep_side_effect

        with patch.object(daemon, "_process_dlq") as mock_process:
            # Raise exception on first call, daemon catches it and continues after sleep
            mock_process.side_effect = [
                Exception("First error"),  # First iteration - triggers exception handler
                None,  # Second iteration, first DLQ
                None,  # Second iteration, second DLQ
            ]

            daemon.run(shutdown_after_iterations)

            # Should continue processing after exception (1 failed + 1 successful iteration)
            assert mock_process.call_count == 3

    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop_keyboard_interrupt(self, mock_publisher_class, daemon):
        """Test run loop exits cleanly on KeyboardInterrupt."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        with patch.object(daemon, "_process_dlq") as mock_process:
            mock_process.side_effect = KeyboardInterrupt()

            daemon.run(lambda: False)

            mock_process.assert_called_once_with(QUEUE_BOT_EVENTS_DLQ)

    def test_process_dlq_publisher_not_initialized(self, daemon):
        """Test _process_dlq raises error if publisher not initialized."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=1, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            event = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )

            mock_method = Method(message_count=1, delivery_tag=1)
            mock_properties = Mock()
            mock_properties.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_channel.consume.return_value = [
                (mock_method, mock_properties, event.model_dump_json())
            ]

            # Publisher is None
            daemon.publisher = None

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            # Should NACK message due to RuntimeError
            mock_channel.basic_nack.assert_called_once_with(1, requeue=True)
            mock_connection_class.assert_called_once_with(ANY)


class TestRetryDaemonHelpers:
    """Test suite for RetryDaemon extracted helper methods."""

    @pytest.fixture
    def daemon(self):
        """Create RetryDaemon instance for testing."""
        return RetryDaemon(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            retry_interval_seconds=60,
        )

    def test_check_dlq_depth(self, daemon):
        """Test _check_dlq_depth returns message count."""
        mock_channel = Mock()
        Method = namedtuple("Method", ["message_count"])
        mock_queue_state = Mock()
        mock_queue_state.method = Method(message_count=42)
        mock_channel.queue_declare.return_value = mock_queue_state

        result = daemon._check_dlq_depth(mock_channel, QUEUE_BOT_EVENTS_DLQ)

        assert result == 42
        mock_channel.queue_declare.assert_called_once_with(queue=QUEUE_BOT_EVENTS_DLQ, durable=True)

    def test_process_single_message_success(self, daemon):
        """Test _process_single_message successfully processes a message."""
        mock_publisher = Mock()
        daemon.publisher = mock_publisher

        mock_channel = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = 123

        mock_properties = Mock()
        mock_properties.message_id = "msg-456"
        mock_properties.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
        mock_properties.routing_key = "game.created"

        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": "789"},
        )
        body = event.model_dump_json().encode()

        result = daemon._process_single_message(
            mock_channel,
            QUEUE_BOT_EVENTS_DLQ,
            mock_method,
            mock_properties,
            body,
        )

        assert result is True
        mock_publisher.publish.assert_called_once_with(ANY, routing_key=ANY, expiration_ms=None)
        mock_channel.basic_ack.assert_called_once_with(123)

    def test_process_single_message_with_retry_count(self, daemon):
        """Test _process_single_message records retry count from x-death."""
        mock_publisher = Mock()
        daemon.publisher = mock_publisher

        mock_channel = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = 123

        mock_properties = Mock()
        mock_properties.message_id = "msg-456"
        mock_properties.headers = {
            "x-death": [
                {
                    "routing-keys": ["game.created"],
                    "count": 5,
                }
            ]
        }
        mock_properties.routing_key = "game.created"

        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": "789"},
        )
        body = event.model_dump_json().encode()

        result = daemon._process_single_message(
            mock_channel,
            QUEUE_BOT_EVENTS_DLQ,
            mock_method,
            mock_properties,
            body,
        )

        assert result is True

    def test_process_single_message_publisher_not_initialized(self, daemon):
        """Test _process_single_message handles missing publisher."""
        daemon.publisher = None

        mock_channel = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = 123

        mock_properties = Mock()
        mock_properties.message_id = "msg-456"
        mock_properties.headers = None
        mock_properties.routing_key = "game.created"

        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": "789"},
        )
        body = event.model_dump_json().encode()

        result = daemon._process_single_message(
            mock_channel,
            QUEUE_BOT_EVENTS_DLQ,
            mock_method,
            mock_properties,
            body,
        )

        assert result is False
        mock_channel.basic_nack.assert_called_once_with(123, requeue=True)

    def test_process_single_message_publish_failure(self, daemon):
        """Test _process_single_message handles publish errors."""
        mock_publisher = Mock()
        mock_publisher.publish.side_effect = Exception("Publish failed")
        daemon.publisher = mock_publisher

        mock_channel = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = 123

        mock_properties = Mock()
        mock_properties.message_id = "msg-456"
        mock_properties.headers = None
        mock_properties.routing_key = "game.created"

        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": "789"},
        )
        body = event.model_dump_json().encode()

        result = daemon._process_single_message(
            mock_channel,
            QUEUE_BOT_EVENTS_DLQ,
            mock_method,
            mock_properties,
            body,
        )

        assert result is False
        mock_channel.basic_nack.assert_called_once_with(123, requeue=True)

    def test_process_single_message_invalid_json(self, daemon):
        """Test _process_single_message handles invalid JSON."""
        mock_publisher = Mock()
        daemon.publisher = mock_publisher

        mock_channel = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = 123

        mock_properties = Mock()
        mock_properties.message_id = "msg-456"
        mock_properties.headers = None
        mock_properties.routing_key = "game.created"

        body = b"invalid json"

        result = daemon._process_single_message(
            mock_channel,
            QUEUE_BOT_EVENTS_DLQ,
            mock_method,
            mock_properties,
            body,
        )

        assert result is False
        mock_channel.basic_nack.assert_called_once_with(123, requeue=True)

    def test_consume_and_process_messages(self, daemon):
        """Test _consume_and_process_messages processes all messages."""
        mock_channel = Mock()

        Method = namedtuple("Method", ["delivery_tag"])
        mock_method1 = Method(delivery_tag=1)
        mock_method2 = Method(delivery_tag=2)

        mock_properties1 = Mock()
        mock_properties2 = Mock()

        event1 = Event(event_type=EventType.GAME_CREATED, data={})
        event2 = Event(event_type=EventType.GAME_UPDATED, data={})

        body1 = event1.model_dump_json().encode()
        body2 = event2.model_dump_json().encode()

        mock_channel.consume.return_value = [
            (mock_method1, mock_properties1, body1),
            (mock_method2, mock_properties2, body2),
        ]

        with patch.object(daemon, "_process_single_message") as mock_process:
            mock_process.side_effect = [True, True]

            processed, failed = daemon._consume_and_process_messages(
                mock_channel, QUEUE_BOT_EVENTS_DLQ, 2
            )

        assert processed == 2
        assert failed == 0
        assert mock_process.call_count == 2

    def test_consume_and_process_messages_with_failures(self, daemon):
        """Test _consume_and_process_messages counts failures."""
        mock_channel = Mock()

        Method = namedtuple("Method", ["delivery_tag"])
        mock_method1 = Method(delivery_tag=1)
        mock_method2 = Method(delivery_tag=2)
        mock_method3 = Method(delivery_tag=3)

        mock_properties = Mock()
        event = Event(event_type=EventType.GAME_CREATED, data={})
        body = event.model_dump_json().encode()

        mock_channel.consume.return_value = [
            (mock_method1, mock_properties, body),
            (mock_method2, mock_properties, body),
            (mock_method3, mock_properties, body),
        ]

        with patch.object(daemon, "_process_single_message") as mock_process:
            mock_process.side_effect = [True, False, True]

            processed, failed = daemon._consume_and_process_messages(
                mock_channel, QUEUE_BOT_EVENTS_DLQ, 3
            )

        assert processed == 2
        assert failed == 1
        assert mock_process.call_count == 3

    def test_consume_and_process_messages_stops_at_count(self, daemon):
        """Test _consume_and_process_messages stops at expected count."""
        mock_channel = Mock()

        Method = namedtuple("Method", ["delivery_tag"])
        mock_method = Method(delivery_tag=1)
        mock_properties = Mock()
        event = Event(event_type=EventType.GAME_CREATED, data={})
        body = event.model_dump_json().encode()

        # Provide more messages than expected
        mock_channel.consume.return_value = [
            (mock_method, mock_properties, body),
            (mock_method, mock_properties, body),
            (mock_method, mock_properties, body),
        ]

        with patch.object(daemon, "_process_single_message") as mock_process:
            mock_process.return_value = True

            processed, failed = daemon._consume_and_process_messages(
                mock_channel, QUEUE_BOT_EVENTS_DLQ, 2
            )

        # Should stop after processing expected count
        assert processed == 2
        assert failed == 0
        assert mock_process.call_count == 2

    @patch("services.retry.retry_daemon.time")
    def test_update_health_tracking_success(self, mock_time, daemon):
        """Test _update_health_tracking records success."""
        mock_time.time.return_value = 1234567890.0

        daemon._update_health_tracking(QUEUE_BOT_EVENTS_DLQ, processed=5, failed=0)

        assert daemon.last_successful_processing_time[QUEUE_BOT_EVENTS_DLQ] == pytest.approx(
            1234567890.0
        )
        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 0

    @patch("services.retry.retry_daemon.time")
    def test_update_health_tracking_partial_success(self, mock_time, daemon):
        """Test _update_health_tracking with some processed messages."""
        mock_time.time.return_value = 1234567890.0

        daemon._update_health_tracking(QUEUE_BOT_EVENTS_DLQ, processed=3, failed=2)

        assert daemon.last_successful_processing_time[QUEUE_BOT_EVENTS_DLQ] == pytest.approx(
            1234567890.0
        )
        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 0

    def test_update_health_tracking_all_failed(self, daemon):
        """Test _update_health_tracking increments failure count."""
        daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] = 2

        daemon._update_health_tracking(QUEUE_BOT_EVENTS_DLQ, processed=0, failed=5)

        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 3
        assert QUEUE_BOT_EVENTS_DLQ not in daemon.last_successful_processing_time

    def test_update_health_tracking_no_failures_from_zero(self, daemon):
        """Test _update_health_tracking with no failures from clean state."""
        daemon._update_health_tracking(QUEUE_BOT_EVENTS_DLQ, processed=0, failed=0)

        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 0
