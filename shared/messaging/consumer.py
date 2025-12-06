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


"""
Event consumer framework for RabbitMQ messaging.

Provides async event consumption with automatic queue creation,
message acknowledgment, and error handling.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel

from shared.messaging.config import get_rabbitmq_connection
from shared.messaging.events import Event, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Awaitable[None]]


class EventConsumer:
    """
    Consumes events from RabbitMQ queue.

    Subscribes to events by routing key pattern and handles
    automatic acknowledgment and error recovery.
    """

    def __init__(
        self,
        queue_name: str,
        exchange_name: str = "game_scheduler",
        connection: AbstractRobustConnection | None = None,
    ):
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self._connection = connection
        self._channel: AbstractChannel | None = None
        self._queue = None
        self._handlers: dict[str, list[EventHandler]] = {}

    async def connect(self) -> None:
        """Establish connection and declare queue."""
        if self._connection is None:
            self._connection = await get_rabbitmq_connection()

        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        self._exchange = await self._channel.declare_exchange(
            self.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )

        self._queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{self.exchange_name}.dlx",
            },
        )  # type: ignore[assignment]

        logger.info(f"Consumer connected to queue: {self.queue_name}")

    async def bind(self, routing_key: str) -> None:
        """
        Bind queue to exchange with routing key pattern.

        Args:
            routing_key: Routing key pattern (supports wildcards: * and #).
        """
        if self._queue is None:
            await self.connect()

        assert self._queue is not None
        await self._queue.bind(self._exchange, routing_key=routing_key)
        logger.info(f"Queue {self.queue_name} bound to routing key: {routing_key}")

    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Register handler function for event type.

        Args:
            event_type: Event type to handle.
            handler: Async function that receives Event object.
        """
        routing_key = event_type.value

        if routing_key not in self._handlers:
            self._handlers[routing_key] = []

        self._handlers[routing_key].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")

    async def _process_message(self, message: AbstractIncomingMessage) -> None:
        """
        Process incoming message with manual acknowledgment.

        Handles message processing with explicit ACK/NACK to prevent message loss.
        Successfully processed messages are ACKed. Failed messages are NACKed
        without requeue, sending them to the dead letter queue for daemon processing.

        Args:
            message: Incoming RabbitMQ message to process
        """
        try:
            event = Event.model_validate_json(message.body)

            handlers = self._handlers.get(event.event_type.value, [])

            if not handlers:
                await message.ack()
                logger.warning(f"No handlers registered for event: {event.event_type}")
                return

            for handler in handlers:
                await handler(event)

            await message.ack()
            logger.debug(f"Successfully processed and ACKed {event.event_type}")

        except Exception as e:
            await message.nack(requeue=False)
            event_type = "unknown"
            try:
                event = Event.model_validate_json(message.body)
                event_type = event.event_type
            except Exception:
                pass
            logger.error(
                f"Handler failed, sending to DLQ for daemon processing: {event_type}, error: {e}",
                exc_info=True,
            )

    async def start_consuming(self) -> None:
        """Start consuming messages from queue."""
        if self._queue is None:
            await self.connect()

        assert self._queue is not None
        logger.info(f"Starting consumer for queue: {self.queue_name}")
        await self._queue.consume(self._process_message)

    async def close(self) -> None:
        """Close channel gracefully."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            self._channel = None
            logger.info("Consumer channel closed")
