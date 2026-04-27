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


"""Tests for RabbitMQ consumer implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType


class TestEventConsumerConnectionFailures:
    """Test suite for EventConsumer connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_bind_routing_key_connection_failure(self) -> None:
        """Test bind_routing_key raises RuntimeError when connection fails."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            consumer._queue = None

            with pytest.raises(
                RuntimeError,
                match="Queue connection failed: unable to bind routing key",
            ):
                await consumer.bind("test.routing.key")
            mock_connect.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_start_consuming_connection_failure(self) -> None:
        """Test start_consuming raises RuntimeError when connection fails."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            consumer._queue = None

            with pytest.raises(
                RuntimeError, match="Queue connection failed: unable to start consumer"
            ):
                await consumer.start_consuming()
            mock_connect.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_bind_routing_key_succeeds_after_reconnect(self) -> None:
        """Test bind_routing_key succeeds when connection is re-established."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        mock_queue = MagicMock()
        mock_queue.bind = AsyncMock()

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            consumer._queue = None
            mock_connect.side_effect = lambda: setattr(consumer, "_queue", mock_queue)
            mock_exchange = MagicMock()
            consumer._exchange = mock_exchange

            await consumer.bind("test.routing.key")

            mock_connect.assert_awaited_once()
            mock_queue.bind.assert_awaited_once_with(mock_exchange, routing_key="test.routing.key")

    @pytest.mark.asyncio
    async def test_start_consuming_succeeds_after_reconnect(self) -> None:
        """Test start_consuming succeeds when connection is re-established."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        mock_queue = MagicMock()
        mock_queue.consume = AsyncMock()

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            consumer._queue = None
            mock_connect.side_effect = lambda: setattr(consumer, "_queue", mock_queue)

            await consumer.start_consuming()

            mock_connect.assert_awaited_once()
            mock_queue.consume.assert_awaited_once()


class TestEventConsumerConnect:
    """Test EventConsumer.connect() establishes channel and queue."""

    @pytest.mark.asyncio
    async def test_connect_creates_channel_and_queue(self) -> None:
        """connect() sets up channel, exchange, and queue via provided connection."""
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel.return_value = mock_channel
        mock_channel.declare_exchange.return_value = mock_exchange
        mock_channel.declare_queue.return_value = mock_queue

        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
            connection=mock_connection,
        )

        await consumer.connect()

        assert consumer._channel is mock_channel
        assert consumer._queue is mock_queue

    @pytest.mark.asyncio
    async def test_connect_fetches_connection_when_none(self) -> None:
        """connect() calls get_rabbitmq_connection when no connection provided."""
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel.return_value = mock_channel
        mock_channel.declare_exchange.return_value = mock_exchange
        mock_channel.declare_queue.return_value = mock_queue

        consumer = EventConsumer(queue_name="test_queue")

        with patch(
            "shared.messaging.consumer.get_rabbitmq_connection",
            new_callable=AsyncMock,
            return_value=mock_connection,
        ):
            await consumer.connect()

        assert consumer._connection is mock_connection


class TestEventConsumerRegisterHandler:
    """Test EventConsumer.register_handler() registers handlers correctly."""

    def test_register_handler_stores_handler(self) -> None:
        """register_handler stores handler in internal dict keyed by event type."""
        consumer = EventConsumer(queue_name="test_queue")

        async def my_handler(event):
            pass

        consumer.register_handler(EventType.NOTIFICATION_DUE, my_handler)

        key = EventType.NOTIFICATION_DUE.value
        assert key in consumer._handlers
        assert my_handler in consumer._handlers[key]

    def test_register_multiple_handlers_for_same_type(self) -> None:
        """Multiple handlers can be registered for the same event type."""
        consumer = EventConsumer(queue_name="test_queue")

        async def handler_a(event):
            pass

        async def handler_b(event):
            pass

        consumer.register_handler(EventType.NOTIFICATION_DUE, handler_a)
        consumer.register_handler(EventType.NOTIFICATION_DUE, handler_b)

        key = EventType.NOTIFICATION_DUE.value
        assert len(consumer._handlers[key]) == 2


class TestEventConsumerProcessMessage:
    """Test EventConsumer._process_message() handles messages correctly."""

    @pytest.mark.asyncio
    async def test_process_message_calls_handler_and_acks(self) -> None:
        """_process_message calls handler and ACKs on success."""
        consumer = EventConsumer(queue_name="test_queue")

        handler = AsyncMock()
        consumer.register_handler(EventType.NOTIFICATION_DUE, handler)

        event = Event(
            event_type=EventType.NOTIFICATION_DUE,
            data={"game_id": "abc"},
        )

        message = AsyncMock()
        message.body = event.model_dump_json().encode()

        await consumer._process_message(message)

        handler.assert_awaited_once()
        message.ack.assert_awaited_once()
        message.nack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_message_acks_when_no_handlers(self) -> None:
        """_process_message ACKs and logs warning when no handlers registered."""
        consumer = EventConsumer(queue_name="test_queue")

        event = Event(event_type=EventType.NOTIFICATION_DUE, data={})
        message = AsyncMock()
        message.body = event.model_dump_json().encode()

        await consumer._process_message(message)

        message.ack.assert_awaited_once()
        message.nack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_message_nacks_on_handler_exception(self) -> None:
        """_process_message NACKs without requeue when handler raises exception."""
        consumer = EventConsumer(queue_name="test_queue")

        async def bad_handler(event):
            msg = "handler failed"
            raise ValueError(msg)

        consumer.register_handler(EventType.NOTIFICATION_DUE, bad_handler)

        event = Event(event_type=EventType.NOTIFICATION_DUE, data={})
        message = AsyncMock()
        message.body = event.model_dump_json().encode()

        await consumer._process_message(message)

        message.nack.assert_awaited_once_with(requeue=False)
        message.ack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_message_nacks_on_invalid_body(self) -> None:
        """_process_message NACKs when message body cannot be parsed as Event."""
        consumer = EventConsumer(queue_name="test_queue")

        message = AsyncMock()
        message.body = b"not valid json"

        await consumer._process_message(message)

        message.nack.assert_awaited_once_with(requeue=False)


class TestEventConsumerClose:
    """Test EventConsumer.close() cleans up channel."""

    @pytest.mark.asyncio
    async def test_close_closes_open_channel(self) -> None:
        """close() closes channel when it is open."""
        consumer = EventConsumer(queue_name="test_queue")

        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        consumer._channel = mock_channel

        await consumer.close()

        mock_channel.close.assert_awaited_once()
        assert consumer._channel is None

    @pytest.mark.asyncio
    async def test_close_skips_when_channel_already_closed(self) -> None:
        """close() does nothing when channel is already closed."""
        consumer = EventConsumer(queue_name="test_queue")

        mock_channel = AsyncMock()
        mock_channel.is_closed = True
        consumer._channel = mock_channel

        await consumer.close()

        mock_channel.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_does_nothing_when_no_channel(self) -> None:
        """close() is a no-op when never connected."""
        consumer = EventConsumer(queue_name="test_queue")
        await consumer.close()
        assert consumer._channel is None
