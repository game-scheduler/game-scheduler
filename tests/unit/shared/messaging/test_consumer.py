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
                RuntimeError, match="Queue connection failed: unable to bind routing key"
            ):
                await consumer.bind("test.routing.key")

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
