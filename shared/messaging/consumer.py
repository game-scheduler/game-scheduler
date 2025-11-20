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

from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

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
        self._channel = None
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
        )

        logger.info(f"Consumer connected to queue: {self.queue_name}")

    async def bind(self, routing_key: str) -> None:
        """
        Bind queue to exchange with routing key pattern.

        Args:
            routing_key: Routing key pattern (supports wildcards: * and #).
        """
        if self._queue is None:
            await self.connect()

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
        """Process incoming message with error handling."""
        async with message.process():
            try:
                event = Event.model_validate_json(message.body)

                handlers = self._handlers.get(event.event_type.value, [])

                if not handlers:
                    logger.warning(f"No handlers registered for event: {event.event_type}")
                    return

                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(
                            f"Handler error for event {event.event_type}: {e}",
                            exc_info=True,
                        )
                        raise

            except Exception as e:
                logger.error(f"Failed to process message: {e}", exc_info=True)
                raise

    async def start_consuming(self) -> None:
        """Start consuming messages from queue."""
        if self._queue is None:
            await self.connect()

        logger.info(f"Starting consumer for queue: {self.queue_name}")
        await self._queue.consume(self._process_message)

    async def close(self) -> None:
        """Close channel gracefully."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            self._channel = None
            logger.info("Consumer channel closed")
