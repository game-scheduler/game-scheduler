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
Main notification daemon for database-backed event-driven scheduler.

Replaces polling-based notification checker with PostgreSQL LISTEN/NOTIFY
and MIN() query pattern for reliable, scalable notification delivery.
"""

import logging
import os
import signal
import time
from uuid import UUID

from sqlalchemy.orm import Session

from shared.database import SyncSessionLocal
from shared.messaging.events import EventType, GameReminderDueEvent
from shared.messaging.sync_publisher import SyncEventPublisher
from shared.models import NotificationSchedule
from shared.models.base import utc_now

from .postgres_listener import PostgresNotificationListener
from .schedule_queries import get_next_due_notification, mark_notification_sent

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_requested = True


class NotificationDaemon:
    """
    Event-driven notification scheduler daemon.

    Uses MIN() query pattern with PostgreSQL LISTEN/NOTIFY for
    efficient, scalable notification delivery.
    """

    def __init__(
        self,
        database_url: str,
        rabbitmq_url: str,
        max_timeout: int = 300,
        buffer_seconds: int = 10,
    ):
        """
        Initialize notification daemon.

        Args:
            database_url: PostgreSQL connection string (psycopg2 format)
            rabbitmq_url: RabbitMQ connection string
            max_timeout: Maximum seconds to wait between checks (default: 5 min)
            buffer_seconds: Wake up this many seconds before due time
        """
        self.database_url = database_url
        self.rabbitmq_url = rabbitmq_url
        self.max_timeout = max_timeout
        self.buffer_seconds = buffer_seconds

        self.listener: PostgresNotificationListener | None = None
        self.publisher: SyncEventPublisher | None = None
        self.db: Session | None = None

    def connect(self) -> None:
        """Establish connections to PostgreSQL and RabbitMQ."""
        self.listener = PostgresNotificationListener(self.database_url)
        self.listener.connect()
        self.listener.listen("notification_schedule_changed")

        self.publisher = SyncEventPublisher()
        self.publisher.connect()

        self.db = SyncSessionLocal()

        logger.info("Notification daemon connections established")

    def run(self) -> None:
        """
        Main daemon loop using simplified single-notification pattern.

        Algorithm:
        1. Query for next unsent notification
        2. If due now (or past due), process it immediately
        3. If in future, wait until buffer_seconds before due time
        4. On wake (due time, NOTIFY, or timeout), go back to step 1
        """
        logger.info("Starting notification daemon")

        self.connect()

        while not shutdown_requested:
            try:
                self._process_loop_iteration()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in daemon loop")
                time.sleep(5)

        logger.info("Notification daemon shutting down")
        self._cleanup()

    def _process_loop_iteration(self) -> None:
        """Process one iteration of the daemon loop."""
        if self.listener is None or self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        next_notification = get_next_due_notification(self.db)

        if not next_notification:
            wait_time = self.max_timeout
            logger.debug(f"No notifications scheduled, waiting {wait_time}s for events or timeout")
        else:
            time_until_due = (next_notification.notification_time - utc_now()).total_seconds()

            if time_until_due <= self.buffer_seconds:
                # Notification is due now, process it immediately
                self._process_notification(next_notification)
                return

            # Notification is in the future, wait for it
            wait_time = max(0, time_until_due - self.buffer_seconds)
            wait_time = min(wait_time, self.max_timeout)

            logger.debug(
                f"Next notification due in {time_until_due:.1f}s, "
                f"waiting {wait_time:.1f}s (buffer: {self.buffer_seconds}s)"
            )

        received, payload = self.listener.wait_for_notification(timeout=wait_time)

        if received:
            logger.info(f"Woke up due to NOTIFY event: {payload}")
        elif wait_time >= self.max_timeout:
            logger.debug(f"Woke up due to periodic check timeout ({self.max_timeout}s)")
        else:
            logger.debug("Woke up due to notification due time")

    def _process_notification(self, notification: NotificationSchedule) -> None:
        """
        Process a single notification.

        Args:
            notification: Notification to process
        """
        if self.publisher is None or self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        try:
            event_data = GameReminderDueEvent(
                game_id=UUID(notification.game_id),
                reminder_minutes=notification.reminder_minutes,
            )

            self.publisher.publish_dict(
                event_type=EventType.GAME_REMINDER_DUE.value,
                data=event_data.model_dump(),
            )

            mark_notification_sent(self.db, notification.id)
            self.db.commit()

            logger.info(
                f"Sent notification for game {notification.game_id} "
                f"({notification.reminder_minutes} min reminder)"
            )

        except Exception:
            logger.exception(
                f"Failed to process notification {notification.id} for game {notification.game_id}"
            )
            self.db.rollback()

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.listener:
            self.listener.close()

        if self.publisher:
            self.publisher.close()

        if self.db:
            self.db.close()

        logger.info("Notification daemon cleanup complete")


def main() -> None:
    """Entry point for notification daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    # Use base database URL for raw psycopg2 connection (no driver specifier)
    from shared.database import BASE_DATABASE_URL

    daemon = NotificationDaemon(
        database_url=BASE_DATABASE_URL,
        rabbitmq_url=rabbitmq_url,
    )

    daemon.run()


if __name__ == "__main__":
    main()
