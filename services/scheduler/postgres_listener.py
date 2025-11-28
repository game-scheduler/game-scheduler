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
PostgreSQL LISTEN/NOTIFY client for event-driven scheduler wake-ups.

Uses psycopg2 for synchronous LISTEN connections to receive real-time
notifications when the notification_schedule table changes.
"""

import json
import logging
import select
from typing import Any

import psycopg2
import psycopg2.extensions

logger = logging.getLogger(__name__)


class PostgresNotificationListener:
    """
    Synchronous PostgreSQL LISTEN/NOTIFY client for scheduler service.

    Establishes a dedicated connection for receiving NOTIFY events from
    PostgreSQL triggers. Uses select() for timeout-based waiting without
    blocking the main thread.
    """

    def __init__(self, database_url: str):
        """
        Initialize listener with database URL.

        Args:
            database_url: PostgreSQL connection string (plain format without driver specifier)
        """
        self.database_url = database_url
        self.conn: psycopg2.extensions.connection | None = None
        self._channels: set[str] = set()

    def connect(self) -> None:
        """
        Establish connection with autocommit for LISTEN.

        Raises:
            psycopg2.Error: If connection fails
        """
        if self.conn is not None and not self.conn.closed:
            logger.warning("Connection already established")
            return

        self.conn = psycopg2.connect(self.database_url)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        if self._channels:
            for channel in self._channels:
                self._execute_listen(channel)

        logger.info("PostgreSQL LISTEN connection established")

    def _execute_listen(self, channel: str) -> None:
        """Execute LISTEN command on the connection."""
        if self.conn is None:
            raise RuntimeError("Not connected to database")

        with self.conn.cursor() as cursor:
            cursor.execute(f"LISTEN {channel};")
        logger.info(f"Listening on channel: {channel}")

    def listen(self, channel: str) -> None:
        """
        Subscribe to notification channel.

        Args:
            channel: PostgreSQL notification channel name
        """
        if self.conn is None:
            raise RuntimeError("Must call connect() before listen()")

        self._channels.add(channel)
        self._execute_listen(channel)

    def wait_for_notification(self, timeout: float) -> tuple[bool, dict[str, Any] | None]:
        """
        Wait for notification or timeout.

        Uses select() to wait for incoming notifications without blocking.
        Automatically parses JSON payloads from NOTIFY events.

        Args:
            timeout: Maximum seconds to wait for notification

        Returns:
            (received, payload) tuple:
            - received: True if notification received, False if timeout
            - payload: Parsed JSON payload if received, None otherwise

        Raises:
            RuntimeError: If not connected to database
        """
        if self.conn is None:
            raise RuntimeError("Not connected to database")

        if self.conn.closed:
            logger.warning("Connection closed, attempting reconnect")
            self.connect()

        if select.select([self.conn], [], [], timeout) == ([], [], []):
            return False, None

        self.conn.poll()

        if self.conn.notifies:
            notify = self.conn.notifies.pop(0)
            payload = None

            if notify.payload:
                try:
                    payload = json.loads(notify.payload)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse NOTIFY payload: {notify.payload}")
                    payload = {"raw": notify.payload}

            logger.debug(f"Received NOTIFY on channel {notify.channel}: {payload}")
            return True, payload

        return False, None

    def close(self) -> None:
        """Close the connection."""
        if self.conn is not None and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL LISTEN connection closed")
