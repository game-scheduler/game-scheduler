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
