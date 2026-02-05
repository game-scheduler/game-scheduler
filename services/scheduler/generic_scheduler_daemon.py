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


"""
Generic scheduler daemon for database-backed event-driven scheduling.

Replaces duplicate notification and status transition daemon implementations
with a single parameterized scheduler using PostgreSQL LISTEN/NOTIFY.
"""

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from opentelemetry import trace

from shared.database import SyncSessionLocal
from shared.messaging.sync_publisher import SyncEventPublisher
from shared.models.base import utc_now

from .postgres_listener import PostgresNotificationListener

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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
        _process_dlq: bool = False,
    ) -> None:
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
            process_dlq: Deprecated parameter, kept for backwards compatibility
        """
        self.database_url = database_url
        self.rabbitmq_url = rabbitmq_url
        self.notify_channel = notify_channel
        self.model_class = model_class
        self.time_field = time_field
        self.status_field = status_field
        self.event_builder = event_builder
        self.max_timeout = max_timeout

        self.listener: PostgresNotificationListener | None = None
        self.publisher: SyncEventPublisher | None = None
        self.db: Session | None = None

    def connect(self) -> None:
        """Establish connections to PostgreSQL and RabbitMQ."""
        self.listener = PostgresNotificationListener(self.database_url)
        self.listener.connect()
        self.listener.listen(self.notify_channel)

        self.publisher = SyncEventPublisher()
        self.publisher.connect()

        self.db = SyncSessionLocal()

        logger.info(
            "Scheduler daemon connections established (channel: %s)",
            self.notify_channel,
        )

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
        logger.info("Starting scheduler daemon for %s", self.model_class.__name__)

        self.connect()

        while not shutdown_flag():
            try:
                self._process_loop_iteration()

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in daemon loop")
                if self.db:
                    self.db.rollback()
                time.sleep(5)

        logger.info("Scheduler daemon shutting down for %s", self.model_class.__name__)
        self._cleanup()

    def _process_loop_iteration(self) -> None:
        """Process one iteration of the daemon loop."""
        if self.listener is None or self.db is None:
            msg = "Daemon not properly initialized"
            raise RuntimeError(msg)

        try:
            next_item = self._get_next_due_item()
        except Exception as e:
            logger.warning("Database query failed (%s), recreating session", e)
            self.db.close()
            self.db = SyncSessionLocal()
            next_item = self._get_next_due_item()

        if not next_item:
            wait_time = self.max_timeout
            logger.debug("No items scheduled, waiting %ss for events or timeout", wait_time)
        else:
            scheduled_time = getattr(next_item, self.time_field)
            time_until_due = (scheduled_time - utc_now()).total_seconds()

            if time_until_due <= 0:
                self._process_item(next_item)
                return

            wait_time = min(max(0.0, time_until_due), float(self.max_timeout))

            logger.debug("Next item due in %.1fs, waiting %.1fs", time_until_due, wait_time)

        received, payload = self.listener.wait_for_notification(timeout=wait_time)

        if received:
            logger.info("Woke up due to NOTIFY event: %s", payload)
        elif wait_time >= self.max_timeout:
            logger.debug("Woke up due to periodic check timeout (%ss)", self.max_timeout)
        else:
            logger.debug("Woke up due to scheduled time")

    def _get_next_due_item(self) -> object | None:
        """
        Query for next unprocessed scheduled item.

        Returns:
            Next scheduled item or None if no items pending
        """
        if self.db is None:
            msg = "Database session not initialized"
            raise RuntimeError(msg)

        return (
            self.db
            .query(self.model_class)
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
            msg = "Database session not initialized"
            raise RuntimeError(msg)

        item = self.db.query(self.model_class).filter_by(id=item_id).first()
        if item:
            setattr(item, self.status_field, True)

    def _process_item(self, item: Any) -> None:  # noqa: ANN401
        """
        Process a scheduled item by building event, publishing, and marking processed.

        Args:
            item: Schedule record to process
        """
        if self.publisher is None or self.db is None:
            msg = "Daemon not properly initialized"
            raise RuntimeError(msg)

        with tracer.start_as_current_span(
            f"scheduled.{self.model_class.__name__}",
            attributes={
                "scheduler.job_id": str(item.id),
                "scheduler.model": self.model_class.__name__,
                "scheduler.time_field": self.time_field,
            },
        ):
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

                logger.info(
                    "Processed scheduled item %s for %s",
                    item.id,
                    self.model_class.__name__,
                )

            except Exception:
                logger.exception("Failed to process scheduled item %s", item.id)
                self.db.rollback()
                # Do not re-raise - let daemon continue processing other items

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.listener:
            try:
                self.listener.close()
            except Exception as e:
                logger.error("Error closing listener: %s", e)

        if self.publisher:
            try:
                self.publisher.close()
            except Exception as e:
                logger.error("Error closing publisher: %s", e)

        if self.db:
            try:
                self.db.close()
            except Exception as e:
                logger.error("Error closing database: %s", e)

        logger.info("Scheduler daemon cleanup complete")
