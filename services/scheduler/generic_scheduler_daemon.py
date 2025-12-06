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
Generic scheduler daemon for database-backed event-driven scheduling.

Replaces duplicate notification and status transition daemon implementations
with a single parameterized scheduler using PostgreSQL LISTEN/NOTIFY.
"""

import logging
import time
from collections.abc import Callable

import pika
from sqlalchemy.orm import Session

from shared.database import SyncSessionLocal
from shared.messaging.events import Event
from shared.messaging.sync_publisher import SyncEventPublisher
from shared.models.base import utc_now

from .postgres_listener import PostgresNotificationListener

logger = logging.getLogger(__name__)


class SchedulerDaemon:
    """
    Generic event-driven scheduler daemon.

    Uses MIN() query pattern with PostgreSQL LISTEN/NOTIFY for
    efficient, scalable scheduled event delivery. Supports any
    schedule model with configurable time and status fields.
    """

    def __init__(
        self,
        database_url: str,
        rabbitmq_url: str,
        notify_channel: str,
        model_class: type,
        time_field: str,
        status_field: str,
        event_builder: Callable,
        max_timeout: int = 900,
        process_dlq: bool = False,
        dlq_check_interval: int = 900,
    ):
        """
        Initialize generic scheduler daemon.

        Args:
            database_url: PostgreSQL connection string (psycopg2 format)
            rabbitmq_url: RabbitMQ connection string
            notify_channel: PostgreSQL LISTEN channel name
            model_class: SQLAlchemy model class for schedule records
            time_field: Name of datetime field for scheduled time
            status_field: Name of boolean field indicating processed status
            event_builder: Function to build Event from schedule record
            max_timeout: Maximum seconds to wait between checks (default: 15 min)
            process_dlq: Whether to process dead letter queue (default: False)
            dlq_check_interval: Seconds between DLQ checks (default: 15 min)
        """
        self.database_url = database_url
        self.rabbitmq_url = rabbitmq_url
        self.notify_channel = notify_channel
        self.model_class = model_class
        self.time_field = time_field
        self.status_field = status_field
        self.event_builder = event_builder
        self.max_timeout = max_timeout
        self.process_dlq = process_dlq
        self.dlq_check_interval = dlq_check_interval

        self.listener: PostgresNotificationListener | None = None
        self.publisher: SyncEventPublisher | None = None
        self.db: Session | None = None
        self.last_dlq_check: float = 0

    def connect(self) -> None:
        """Establish connections to PostgreSQL and RabbitMQ."""
        self.listener = PostgresNotificationListener(self.database_url)
        self.listener.connect()
        self.listener.listen(self.notify_channel)

        self.publisher = SyncEventPublisher()
        self.publisher.connect()

        self.db = SyncSessionLocal()

        logger.info(f"Scheduler daemon connections established (channel: {self.notify_channel})")

    def run(self, shutdown_flag: Callable[[], bool]) -> None:
        """
        Main daemon loop using simplified single-item pattern.

        Algorithm:
        1. Query for next unprocessed scheduled item
        2. If due now (or past due), process it immediately
        3. If in future, wait until scheduled time
        4. On wake (due time, NOTIFY, or timeout), go back to step 1

        Args:
            shutdown_flag: Callable returning True when shutdown is requested
        """
        logger.info(f"Starting scheduler daemon for {self.model_class.__name__}")

        self.connect()

        if self.process_dlq:
            self._process_dlq_messages()
            self.last_dlq_check = time.time()

        while not shutdown_flag():
            try:
                self._process_loop_iteration()

                if self.process_dlq and time.time() - self.last_dlq_check > self.dlq_check_interval:
                    self._process_dlq_messages()
                    self.last_dlq_check = time.time()

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in daemon loop")
                if self.db:
                    self.db.rollback()
                time.sleep(5)

        logger.info(f"Scheduler daemon shutting down for {self.model_class.__name__}")
        self._cleanup()

    def _process_loop_iteration(self) -> None:
        """Process one iteration of the daemon loop."""
        if self.listener is None or self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        try:
            next_item = self._get_next_due_item()
        except Exception as e:
            logger.warning(f"Database query failed ({e}), recreating session")
            self.db.close()
            self.db = SyncSessionLocal()
            next_item = self._get_next_due_item()

        if not next_item:
            wait_time = self.max_timeout
            logger.debug(f"No items scheduled, waiting {wait_time}s for events or timeout")
        else:
            scheduled_time = getattr(next_item, self.time_field)
            time_until_due = (scheduled_time - utc_now()).total_seconds()

            if time_until_due <= 0:
                self._process_item(next_item)
                return

            wait_time = min(max(0.0, time_until_due), float(self.max_timeout))

            logger.debug(f"Next item due in {time_until_due:.1f}s, waiting {wait_time:.1f}s")

        received, payload = self.listener.wait_for_notification(timeout=wait_time)

        if received:
            logger.info(f"Woke up due to NOTIFY event: {payload}")
        elif wait_time >= self.max_timeout:
            logger.debug(f"Woke up due to periodic check timeout ({self.max_timeout}s)")
        else:
            logger.debug("Woke up due to scheduled time")

    def _get_next_due_item(self) -> object | None:
        """
        Query for next unprocessed scheduled item.

        Returns:
            Next scheduled item or None if no items pending
        """
        if self.db is None:
            raise RuntimeError("Database session not initialized")

        return (
            self.db.query(self.model_class)
            .filter(getattr(self.model_class, self.status_field) == False)  # noqa: E712
            .filter(getattr(self.model_class, self.time_field).isnot(None))
            .order_by(getattr(self.model_class, self.time_field).asc())
            .first()
        )

    def _mark_item_processed(self, item_id: str) -> None:
        """
        Mark scheduled item as processed.

        Args:
            item_id: ID of the item to mark as processed
        """
        if self.db is None:
            raise RuntimeError("Database session not initialized")

        item = self.db.query(self.model_class).filter_by(id=item_id).first()
        if item:
            setattr(item, self.status_field, True)

    def _process_item(self, item) -> None:
        """
        Process a scheduled item by building event, publishing, and marking processed.

        Args:
            item: Schedule record to process
        """
        if self.publisher is None or self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        try:
            result = self.event_builder(item)

            if isinstance(result, tuple):
                event, expiration_ms = result
            else:
                event, expiration_ms = result, None

            self.publisher.publish(
                event=event,
                expiration_ms=expiration_ms,
            )

            self._mark_item_processed(item.id)
            self.db.commit()

            logger.info(f"Processed scheduled item {item.id} for {self.model_class.__name__}")

        except Exception:
            logger.exception(f"Failed to process scheduled item {item.id}")
            self.db.rollback()

    def _process_dlq_messages(self) -> None:
        """
        Consume messages from DLQ and republish to primary queue.

        Processes all messages currently in the dead letter queue by:
        1. Consuming each message with manual acknowledgment
        2. Republishing to primary queue without TTL
        3. ACKing successful republish or NACKing failures

        The bot handler performs defensive staleness checks, so republishing
        without TTL is safe - stale notifications will be skipped.
        """
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            channel = connection.channel()

            queue_state = channel.queue_declare(queue="DLQ", durable=True)
            message_count = queue_state.method.message_count

            if message_count == 0:
                logger.debug("DLQ is empty, nothing to process")
                connection.close()
                return

            logger.info(f"Processing {message_count} messages from DLQ")

            processed = 0
            republished = 0

            for method, _properties, body in channel.consume("DLQ", auto_ack=False):
                try:
                    event = Event.model_validate_json(body)

                    if self.publisher is None:
                        raise RuntimeError("Publisher not initialized")

                    self.publisher.publish(event, expiration_ms=None)
                    republished += 1

                    channel.basic_ack(method.delivery_tag)
                    processed += 1

                    if processed >= message_count:
                        break

                except Exception as e:
                    logger.error(f"Error processing DLQ message: {e}")
                    channel.basic_nack(method.delivery_tag, requeue=False)

            channel.cancel()
            connection.close()

            logger.info(f"DLQ processing: {republished} messages republished")

        except Exception as e:
            logger.error(f"Error during DLQ processing: {e}", exc_info=True)

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.listener:
            try:
                self.listener.close()
            except Exception as e:
                logger.error(f"Error closing listener: {e}")

        if self.publisher:
            try:
                self.publisher.close()
            except Exception as e:
                logger.error(f"Error closing publisher: {e}")

        if self.db:
            try:
                self.db.close()
            except Exception as e:
                logger.error(f"Error closing database: {e}")

        logger.info("Scheduler daemon cleanup complete")
