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
Dedicated retry daemon for DLQ processing.

Periodically checks configured DLQs and republishes messages
to their primary queues with configurable intervals.
"""

import logging
import time
from collections.abc import Callable

import pika
from opentelemetry import metrics, trace

from shared.messaging.events import Event
from shared.messaging.infrastructure import (
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION_DLQ,
)
from shared.messaging.sync_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)


class RetryDaemon:
    """Processes DLQs and republishes messages with configurable retry intervals."""

    def __init__(self, rabbitmq_url: str, retry_interval_seconds: int = 900):
        """
        Initialize retry daemon.

        Args:
            rabbitmq_url: RabbitMQ connection string
            retry_interval_seconds: How often to check DLQs (default 15 min)
        """
        self.rabbitmq_url = rabbitmq_url
        self.retry_interval = retry_interval_seconds
        self.publisher: SyncEventPublisher | None = None

        # Map DLQ names to process
        self.dlq_names = [
            QUEUE_BOT_EVENTS_DLQ,
            QUEUE_NOTIFICATION_DLQ,
        ]

        # Initialize OpenTelemetry metrics
        self.messages_processed_counter = meter.create_counter(
            name="retry.messages.processed",
            description="Number of messages successfully processed from DLQ",
            unit="1",
        )
        self.messages_failed_counter = meter.create_counter(
            name="retry.messages.failed",
            description="Number of messages that failed to republish",
            unit="1",
        )
        self.dlq_depth_gauge = meter.create_observable_gauge(
            name="retry.dlq.depth",
            description="Current number of messages in DLQ",
            unit="1",
            callbacks=[self._observe_dlq_depth],
        )
        self.processing_duration_histogram = meter.create_histogram(
            name="retry.processing.duration",
            description="Duration of DLQ processing in seconds",
            unit="s",
        )
        self.last_successful_processing_time: dict[str, float] = {}
        self.consecutive_failures: dict[str, int] = {}

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        self.publisher = SyncEventPublisher()
        self.publisher.connect()
        logger.info("Retry daemon connected to RabbitMQ")

    def run(self, shutdown_requested: Callable[[], bool]) -> None:
        """
        Main daemon loop.

        Args:
            shutdown_requested: Callable returning True when shutdown is requested
        """
        logger.info("Starting retry daemon")

        self.connect()

        while not shutdown_requested():
            try:
                for dlq_name in self.dlq_names:
                    self._process_dlq(dlq_name)

                time.sleep(self.retry_interval)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in retry daemon loop")
                time.sleep(5)

        logger.info("Retry daemon shutting down")
        self._cleanup()

    def _process_dlq(self, dlq_name: str) -> None:
        """
        Process messages from one DLQ.

        Args:
            dlq_name: Name of the dead letter queue to process
        """
        start_time = time.time()

        with tracer.start_as_current_span(
            "retry.process_dlq",
            attributes={
                "retry.dlq_name": dlq_name,
                "retry.check_interval": self.retry_interval,
            },
        ) as span:
            try:
                connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
                channel = connection.channel()

                queue_state = channel.queue_declare(queue=dlq_name, durable=True)
                message_count = queue_state.method.message_count

                span.set_attribute("retry.dlq.message_count", message_count)

                if message_count == 0:
                    logger.debug(f"DLQ {dlq_name} is empty, nothing to process")
                    connection.close()
                    self.consecutive_failures[dlq_name] = 0
                    return

                logger.info(f"Processing {message_count} messages from {dlq_name}")

                processed = 0
                failed = 0

                for method, properties, body in channel.consume(dlq_name, auto_ack=False):
                    # Create child span for individual message processing
                    with tracer.start_as_current_span(
                        "retry.process_message",
                        attributes={
                            "retry.dlq_name": dlq_name,
                            "messaging.message_id": properties.message_id or "unknown",
                        },
                    ) as msg_span:
                        try:
                            routing_key = self._get_routing_key(properties)

                            event = Event.model_validate_json(body)

                            # Add detailed span attributes
                            msg_span.set_attribute("retry.routing_key", routing_key)
                            msg_span.set_attribute("retry.event_type", event.event_type)
                            if properties.headers and "x-death" in properties.headers:
                                deaths = properties.headers["x-death"]
                                if deaths and len(deaths) > 0:
                                    retry_count = deaths[0].get("count", 0)
                                    msg_span.set_attribute("retry.retry_count", retry_count)

                            if self.publisher is None:
                                raise RuntimeError("Publisher not initialized")

                            # Republish without TTL to prevent re-entering DLQ
                            self.publisher.publish(
                                event, routing_key=routing_key, expiration_ms=None
                            )

                            channel.basic_ack(method.delivery_tag)
                            processed += 1

                            # Record successful processing
                            self.messages_processed_counter.add(
                                1,
                                attributes={
                                    "dlq_name": dlq_name,
                                    "event_type": event.event_type,
                                    "routing_key": routing_key,
                                },
                            )

                            if processed >= message_count:
                                break

                        except Exception as e:
                            logger.error(
                                f"Failed to republish message from {dlq_name}: {e}",
                                exc_info=True,
                            )
                            # NACK with requeue - message stays in DLQ for next cycle
                            channel.basic_nack(method.delivery_tag, requeue=True)
                            failed += 1

                            # Record failed processing
                            self.messages_failed_counter.add(
                                1,
                                attributes={
                                    "dlq_name": dlq_name,
                                    "error_type": type(e).__name__,
                                },
                            )
                            msg_span.record_exception(e)

                channel.cancel()
                connection.close()

                logger.info(f"Republished {processed} messages from {dlq_name}")

                # Update health tracking
                if processed > 0 or failed == 0:
                    self.last_successful_processing_time[dlq_name] = time.time()
                    self.consecutive_failures[dlq_name] = 0
                else:
                    current_failures = self.consecutive_failures.get(dlq_name, 0)
                    self.consecutive_failures[dlq_name] = current_failures + 1

                span.set_attribute("retry.processed_count", processed)
                span.set_attribute("retry.failed_count", failed)

            except Exception as e:
                logger.error(f"Error during DLQ processing for {dlq_name}: {e}", exc_info=True)
                self.consecutive_failures[dlq_name] = self.consecutive_failures.get(dlq_name, 0) + 1
                span.record_exception(e)
            finally:
                # Record processing duration
                duration = time.time() - start_time
                self.processing_duration_histogram.record(
                    duration,
                    attributes={"dlq_name": dlq_name},
                )

    def _get_routing_key(self, properties) -> str:
        """
        Extract original routing key from message headers.

        Args:
            properties: Message properties from RabbitMQ

        Returns:
            Original routing key from x-death header or message properties
        """
        if properties.headers and "x-death" in properties.headers:
            deaths = properties.headers["x-death"]
            if deaths and len(deaths) > 0:
                routing_keys = deaths[0].get("routing-keys", [])
                if routing_keys and len(routing_keys) > 0:
                    return routing_keys[0]

        return properties.routing_key or "unknown"

    def _observe_dlq_depth(self, options):
        """
        Observable callback for DLQ depth gauge.

        Args:
            options: Callback options from OpenTelemetry

        Yields:
            Observation: DLQ depth observations for each queue
        """
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            channel = connection.channel()

            for dlq_name in self.dlq_names:
                try:
                    queue_state = channel.queue_declare(queue=dlq_name, durable=True, passive=True)
                    message_count = queue_state.method.message_count

                    yield metrics.Observation(
                        value=message_count,
                        attributes={"dlq_name": dlq_name},
                    )
                except Exception as e:
                    logger.warning(f"Failed to get depth for {dlq_name}: {e}")

            connection.close()
        except Exception as e:
            logger.error(f"Failed to observe DLQ depths: {e}")

    def is_healthy(self) -> bool:
        """
        Check if the retry daemon is healthy.

        Returns:
            True if healthy, False otherwise
        """
        # Check RabbitMQ connectivity
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            connection.close()
        except Exception:
            return False

        # Check for excessive consecutive failures
        for dlq_name, failures in self.consecutive_failures.items():
            if failures >= 3:
                logger.warning(f"DLQ {dlq_name} has {failures} consecutive failures")
                return False

        return True

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.publisher:
            try:
                self.publisher.close()
            except Exception as e:
                logger.error(f"Error closing publisher: {e}")

        logger.info("Retry daemon cleanup complete")
