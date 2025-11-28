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


"""Tests for PostgreSQL LISTEN/NOTIFY client."""

import json
from unittest.mock import MagicMock, Mock, patch

import psycopg2
import pytest

from services.scheduler.postgres_listener import PostgresNotificationListener


class TestPostgresNotificationListener:
    """Test suite for PostgresNotificationListener."""

    def test_init_stores_plain_url(self):
        """Listener stores plain PostgreSQL URL."""
        url = "postgresql://user:pass@host:5432/db"
        listener = PostgresNotificationListener(url)

        assert listener.database_url == url

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_connect_establishes_connection(self, mock_connect):
        """Connect establishes database connection with autocommit."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()

        mock_connect.assert_called_once_with("postgresql://user:pass@host:5432/db")
        mock_conn.set_isolation_level.assert_called_once_with(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
        )

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_connect_does_not_reconnect_if_already_connected(self, mock_connect):
        """Connect skips if connection already established."""
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_connect.return_value = mock_conn

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()

        # Try connecting again
        listener.connect()

        # Should only connect once
        assert mock_connect.call_count == 1

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_listen_subscribes_to_channel(self, mock_connect):
        """Listen executes LISTEN command for channel."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()
        listener.listen("test_channel")

        mock_cursor.execute.assert_called_once_with("LISTEN test_channel;")
        assert "test_channel" in listener._channels

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_listen_raises_if_not_connected(self, mock_connect):
        """Listen raises RuntimeError if not connected."""
        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")

        with pytest.raises(RuntimeError, match="Must call connect"):
            listener.listen("test_channel")

    @patch("services.scheduler.postgres_listener.select.select")
    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_wait_for_notification_timeout(self, mock_connect, mock_select):
        """Wait returns False on timeout."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_select.return_value = ([], [], [])  # Empty = timeout

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()

        received, payload = listener.wait_for_notification(1.0)

        assert received is False
        assert payload is None
        mock_select.assert_called_once()

    @patch("services.scheduler.postgres_listener.select.select")
    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_wait_for_notification_receives_notify(self, mock_connect, mock_select):
        """Wait returns True with payload when notification received."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Simulate notification received
        mock_select.return_value = ([mock_conn], [], [])

        # Mock notification
        mock_notify = Mock()
        mock_notify.payload = json.dumps({"game_id": "test-id", "operation": "INSERT"})
        mock_conn.notifies = [mock_notify]

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()

        received, payload = listener.wait_for_notification(1.0)

        assert received is True
        assert payload == {"game_id": "test-id", "operation": "INSERT"}
        mock_conn.poll.assert_called_once()

    @patch("services.scheduler.postgres_listener.select.select")
    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_wait_for_notification_handles_empty_payload(self, mock_connect, mock_select):
        """Wait handles notifications with empty payload."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_select.return_value = ([mock_conn], [], [])

        mock_notify = Mock()
        mock_notify.payload = None
        mock_conn.notifies = [mock_notify]

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()

        received, payload = listener.wait_for_notification(1.0)

        assert received is True
        # Empty payload returns None, not empty dict
        assert payload is None

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_close_closes_connection(self, mock_connect):
        """Close closes the database connection."""
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_connect.return_value = mock_conn

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()
        listener.close()

        mock_conn.close.assert_called_once()

    @patch("services.scheduler.postgres_listener.psycopg2.connect")
    def test_close_handles_already_closed(self, mock_connect):
        """Close handles already closed connection."""
        mock_conn = MagicMock()
        mock_conn.closed = True
        mock_connect.return_value = mock_conn

        listener = PostgresNotificationListener("postgresql://user:pass@host:5432/db")
        listener.connect()
        listener.close()

        # Should not call close on already closed connection
        mock_conn.close.assert_not_called()
