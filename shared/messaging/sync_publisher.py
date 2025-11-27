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
Synchronous event publisher for RabbitMQ messaging.

Provides synchronous event publishing for Celery tasks where async
operations provide no benefit. Uses pika library instead of aio_pika.
"""

import logging
import os
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection

from shared.messaging.events import Event, EventType

logger = logging.getLogger(__name__)


class SyncEventPublisher:
    """
    Publishes events to RabbitMQ exchange synchronously.

    Events are published to a topic exchange with routing key
    based on event type, allowing flexible message routing.

    Use this publisher in Celery tasks and other synchronous code
    where async operations provide no concurrency benefit.
    """

    def __init__(self, exchange_name: str = "game_scheduler"):
        self.exchange_name = exchange_name
        self._connection: BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def connect(self) -> None:
        """Establish connection and declare exchange."""
        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

        parameters = pika.URLParameters(rabbitmq_url)
        parameters.heartbeat = 60
        parameters.connection_attempts = 3
        parameters.retry_delay = 2

        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()

        self._channel.exchange_declare(
            exchange=self.exchange_name,
            exchange_type="topic",
            durable=True,
        )

        logger.info(f"Sync publisher connected to exchange: {self.exchange_name}")

    def publish(
        self,
        event: Event,
        routing_key: str | None = None,
    ) -> None:
        """
        Publish event to exchange.

        Args:
            event: Event to publish.
            routing_key: Optional routing key override. Uses event_type if not
                provided.

        Raises:
            RuntimeError: If not connected.
        """
        if self._channel is None:
            self.connect()

        if routing_key is None:
            routing_key = event.event_type.value

        message_body = event.model_dump_json().encode()

        self._channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=routing_key,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )

        logger.debug(f"Published event: {event.event_type} with routing key: {routing_key}")

    def publish_dict(
        self,
        event_type: str,
        data: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Publish event from dictionary data.

        Convenience method for publishing without creating Event object.

        Args:
            event_type: Event type string.
            data: Event payload.
            trace_id: Optional correlation ID.
        """
        event = Event(
            event_type=EventType(event_type),
            data=data,
            trace_id=trace_id,
        )

        self.publish(event)

    def close(self) -> None:
        """Close channel and connection gracefully."""
        if self._channel and self._channel.is_open:
            self._channel.close()
            self._channel = None

        if self._connection and self._connection.is_open:
            self._connection.close()
            self._connection = None

            logger.info("Sync publisher connection closed")
