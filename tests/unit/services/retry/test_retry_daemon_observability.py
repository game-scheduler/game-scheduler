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


"""Tests for retry daemon observability features."""

from unittest.mock import MagicMock, Mock, patch

import pika.exceptions

from services.retry.retry_daemon import RetryDaemon
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS_DLQ


class TestRetryDaemonObservability:
    """Test observability features of the retry daemon."""

    def test_metrics_initialized_on_create(self):
        """Verify OpenTelemetry metrics are initialized when daemon is created."""
        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)

        assert daemon.messages_processed_counter is not None
        assert daemon.messages_failed_counter is not None
        assert daemon.dlq_depth_gauge is not None
        assert daemon.processing_duration_histogram is not None

    def test_health_tracking_initialized(self):
        """Verify health tracking variables are initialized."""
        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)

        assert daemon.last_successful_processing_time == {}
        assert daemon.consecutive_failures == {}

    @patch("pika.BlockingConnection")
    def test_is_healthy_with_rabbitmq_up(self, mock_connection_class):
        """Verify is_healthy returns True when RabbitMQ is accessible."""
        mock_connection = Mock()
        mock_connection_class.return_value = mock_connection

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)
        daemon.consecutive_failures = {}

        assert daemon.is_healthy() is True
        mock_connection.close.assert_called_once()

    @patch("pika.BlockingConnection")
    def test_is_healthy_with_rabbitmq_down(self, mock_connection_class):
        """Verify is_healthy returns False when RabbitMQ is down."""
        mock_connection_class.side_effect = pika.exceptions.AMQPConnectionError("Connection failed")

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)

        assert daemon.is_healthy() is False

    @patch("pika.BlockingConnection")
    def test_is_healthy_with_consecutive_failures(self, mock_connection_class):
        """Verify is_healthy returns False when consecutive failures exceed threshold."""
        mock_connection = Mock()
        mock_connection_class.return_value = mock_connection

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)
        daemon.consecutive_failures = {QUEUE_BOT_EVENTS_DLQ: 3}

        assert daemon.is_healthy() is False

    @patch("pika.BlockingConnection")
    def test_observe_dlq_depth(self, mock_connection_class):
        """Verify DLQ depth observation callback works."""
        mock_channel = MagicMock()
        mock_connection = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        # Mock queue declare response
        mock_method = Mock()
        mock_method.message_count = 5
        mock_queue_state = Mock()
        mock_queue_state.method = mock_method
        mock_channel.queue_declare.return_value = mock_queue_state

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)

        # Call the observation callback
        observations = list(daemon._observe_dlq_depth(None))

        # Should have one observation per DLQ
        assert len(observations) == 2

        # Each observation should have the correct value and attributes
        for obs in observations:
            assert obs.value == 5
            assert obs.attributes is not None
            assert "dlq_name" in obs.attributes

    @patch("pika.BlockingConnection")
    @patch("services.retry.retry_daemon.tracer")
    def test_span_attributes_on_process_dlq(self, mock_tracer, mock_connection_class):
        """Verify span attributes are set during DLQ processing."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        mock_channel = MagicMock()
        mock_connection = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        # Mock empty queue
        mock_method = Mock()
        mock_method.message_count = 0
        mock_queue_state = Mock()
        mock_queue_state.method = mock_method
        mock_channel.queue_declare.return_value = mock_queue_state

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)
        daemon.publisher = MagicMock()

        daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

        # Verify span attributes were set
        mock_span.set_attribute.assert_called()
        set_attribute_calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        assert ("retry.dlq.message_count", 0) in set_attribute_calls

    @patch("pika.BlockingConnection")
    def test_consecutive_failures_reset_on_success(self, mock_connection_class):
        """Verify consecutive failures counter resets on successful processing."""
        mock_channel = MagicMock()
        mock_connection = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        # Mock empty queue (successful processing)
        mock_method = Mock()
        mock_method.message_count = 0
        mock_queue_state = Mock()
        mock_queue_state.method = mock_method
        mock_channel.queue_declare.return_value = mock_queue_state

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)
        daemon.publisher = MagicMock()
        daemon.consecutive_failures = {QUEUE_BOT_EVENTS_DLQ: 2}

        daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 0

    @patch("pika.BlockingConnection")
    def test_consecutive_failures_incremented_on_error(self, mock_connection_class):
        """Verify consecutive failures counter increments on error."""
        mock_connection_class.side_effect = Exception("Connection error")

        daemon = RetryDaemon(rabbitmq_url="amqp://test", retry_interval_seconds=60)
        daemon.publisher = MagicMock()
        daemon.consecutive_failures = {QUEUE_BOT_EVENTS_DLQ: 0}

        daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

        assert daemon.consecutive_failures[QUEUE_BOT_EVENTS_DLQ] == 1
