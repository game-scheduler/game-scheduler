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


"""Unit tests for SyncEventPublisher."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pika
import pytest

from shared.messaging.events import Event, EventType
from shared.messaging.sync_publisher import SyncEventPublisher


@pytest.fixture
def publisher():
    """Create publisher instance for testing."""
    return SyncEventPublisher(exchange_name="test_exchange")


@pytest.fixture
def mock_channel():
    """Create mock channel for testing."""
    channel = MagicMock()
    channel.is_open = True
    return channel


@pytest.fixture
def sample_event():
    """Create sample event for testing."""
    return Event(
        event_type=EventType.NOTIFICATION_DUE,
        data={"game_id": str(uuid4()), "reminder_minutes": 60},
    )


class TestSyncEventPublisherInit:
    """Test publisher initialization."""

    def test_init_sets_exchange_name(self):
        """Publisher stores exchange name."""
        publisher = SyncEventPublisher(exchange_name="my_exchange")
        assert publisher.exchange_name == "my_exchange"

    def test_init_defaults_to_game_scheduler(self):
        """Publisher defaults to game_scheduler exchange."""
        publisher = SyncEventPublisher()
        assert publisher.exchange_name == "game_scheduler"

    def test_init_connection_starts_as_none(self):
        """Publisher initializes with no connection."""
        publisher = SyncEventPublisher()
        assert publisher._connection is None
        assert publisher._channel is None


class TestSyncEventPublisherPublish:
    """Test event publishing."""

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_without_expiration(self, mock_connection_class, publisher, sample_event):
        """Publish without expiration_ms sets no expiration property."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()
        publisher.publish(sample_event)

        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]["properties"]

        assert not hasattr(properties, "expiration") or properties.expiration is None

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_with_expiration_sets_property(
        self, mock_connection_class, publisher, sample_event
    ):
        """Publish with expiration_ms sets expiration property as string."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()
        publisher.publish(sample_event, expiration_ms=30000)

        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]["properties"]

        assert properties.expiration == "30000"

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_expiration_converted_to_string(
        self, mock_connection_class, publisher, sample_event
    ):
        """Expiration value is converted to string for RabbitMQ."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()
        publisher.publish(sample_event, expiration_ms=60000)

        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]["properties"]

        assert isinstance(properties.expiration, str)
        assert properties.expiration == "60000"

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_zero_expiration_is_valid(self, mock_connection_class, publisher, sample_event):
        """Zero expiration is a valid value."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()
        publisher.publish(sample_event, expiration_ms=0)

        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]["properties"]

        assert properties.expiration == "0"

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_maintains_other_properties(
        self, mock_connection_class, publisher, sample_event
    ):
        """Publishing with expiration maintains other message properties."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()
        publisher.publish(sample_event, expiration_ms=45000)

        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]["properties"]

        assert properties.delivery_mode == 2  # pika.DeliveryMode.Persistent value
        assert properties.content_type == "application/json"
        assert properties.expiration == "45000"

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_retry_preserves_expiration(
        self, mock_connection_class, publisher, sample_event
    ):
        """Retry after connection loss preserves expiration property."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()

        mock_channel.basic_publish.side_effect = [
            pika.exceptions.ConnectionClosed(200, "Closed"),
            None,
        ]

        publisher.publish(sample_event, expiration_ms=15000)

        assert mock_channel.basic_publish.call_count == 2
        retry_call_args = mock_channel.basic_publish.call_args_list[1]
        properties = retry_call_args[1]["properties"]

        assert properties.expiration == "15000"


class TestSyncEventPublisherPublishDict:
    """Test convenience publish_dict method."""

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_dict_creates_event_internally(self, mock_connection_class, publisher):
        """publish_dict creates Event and calls publish."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection

        publisher.connect()

        with patch.object(publisher, "publish") as mock_publish:
            publisher.publish_dict(
                event_type=EventType.NOTIFICATION_DUE.value,
                data={"game_id": str(uuid4())},
            )

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            event = call_args[0][0]
            assert event.event_type == EventType.NOTIFICATION_DUE


class TestSyncEventPublisherConnect:
    """Test connection management in connect()."""

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_connect_closes_existing_open_connection(self, mock_connection_class):
        """connect() closes and discards an existing open connection before reconnecting."""
        publisher = SyncEventPublisher()
        existing_conn = MagicMock()
        existing_conn.is_open = True
        publisher._connection = existing_conn

        mock_connection_class.return_value = MagicMock()

        publisher.connect()

        existing_conn.close.assert_called_once()

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_connect_logs_warning_when_close_raises(self, mock_connection_class):
        """connect() logs warning and continues when closing existing connection fails."""
        publisher = SyncEventPublisher()
        existing_conn = MagicMock()
        existing_conn.is_open = True
        existing_conn.close.side_effect = Exception("close failed")
        publisher._connection = existing_conn

        mock_new_conn = MagicMock()
        mock_connection_class.return_value = mock_new_conn

        publisher.connect()

        assert publisher._connection is mock_new_conn

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_reconnects_when_channel_is_none(self, mock_connection_class, sample_event):
        """publish() reconnects when _channel is None before publishing."""
        publisher = SyncEventPublisher()

        mock_conn = MagicMock()
        mock_chan = MagicMock()
        mock_chan.is_open = True
        mock_conn.channel.return_value = mock_chan
        mock_connection_class.return_value = mock_conn

        publisher.publish(sample_event)

        call_kwargs = mock_chan.basic_publish.call_args.kwargs
        assert call_kwargs["exchange"] == "game_scheduler"
        assert call_kwargs["routing_key"] == sample_event.event_type.value
        assert call_kwargs["body"] == sample_event.model_dump_json().encode()

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_publish_reconnects_when_channel_closed(self, mock_connection_class, sample_event):
        """publish() reconnects when _channel.is_open is False."""
        publisher = SyncEventPublisher()

        mock_conn = MagicMock()
        mock_chan = MagicMock()
        mock_chan.is_open = True
        mock_conn.channel.return_value = mock_chan
        mock_connection_class.return_value = mock_conn

        publisher._connection = MagicMock(is_open=False)
        publisher._channel = MagicMock(is_open=False)

        publisher.publish(sample_event)

        call_kwargs = mock_chan.basic_publish.call_args.kwargs
        assert call_kwargs["exchange"] == "game_scheduler"
        assert call_kwargs["routing_key"] == sample_event.event_type.value
        assert call_kwargs["body"] == sample_event.model_dump_json().encode()


class TestSyncEventPublisherClose:
    """Test close() method."""

    @patch("shared.messaging.sync_publisher.pika.BlockingConnection")
    def test_close_shuts_channel_and_connection(self, mock_connection_class):
        """close() closes both open channel and connection."""
        publisher = SyncEventPublisher()

        mock_conn = MagicMock()
        mock_chan = MagicMock()
        mock_chan.is_open = True
        mock_conn.is_open = True
        mock_conn.channel.return_value = mock_chan
        mock_connection_class.return_value = mock_conn

        publisher.connect()
        publisher.close()

        mock_chan.close.assert_called_once()
        mock_conn.close.assert_called_once()
        assert publisher._channel is None
        assert publisher._connection is None

    def test_close_does_nothing_when_not_connected(self):
        """close() is a no-op when publisher was never connected."""
        publisher = SyncEventPublisher()
        publisher.close()
        assert publisher._channel is None
        assert publisher._connection is None
