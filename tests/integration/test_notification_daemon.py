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


"""Integration tests for notification daemon with PostgreSQL LISTEN/NOTIFY.

These tests are designed to run in Docker with docker-compose where all
services (PostgreSQL, RabbitMQ) are available.
"""

import os
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.scheduler.notification_daemon import NotificationDaemon
from services.scheduler.postgres_listener import PostgresNotificationListener
from services.scheduler.schedule_queries import (
    get_next_due_notification,
    mark_notification_sent,
)


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment (set by docker-compose)."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )


@pytest.fixture
def db_session(db_url):
    """Create a database session for tests."""
    sync_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine)

    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def clean_notification_schedule(db_session):
    """Clean notification_schedule table before and after test."""
    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.commit()

    yield

    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.commit()


@pytest.fixture
def test_game_session(db_session):
    """
    Create minimal test data for foreign key constraints.

    Creates: guild -> channel -> user -> game_session
    Returns the game_session.id for use in notification_schedule inserts.
    """
    guild_id = str(uuid4())
    channel_id = str(uuid4())
    user_id = str(uuid4())
    game_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    db_session.execute(
        text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, created_at, updated_at) "
            "VALUES (:id, :guild_id, :created_at, :updated_at)"
        ),
        {"id": guild_id, "guild_id": "123456789", "created_at": now, "updated_at": now},
    )

    db_session.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, channel_name, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :channel_name, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_id,
            "channel_id": "987654321",
            "channel_name": "test-channel",
            "guild_id": guild_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.execute(
        text(
            "INSERT INTO users (id, discord_id, created_at, updated_at) "
            "VALUES (:id, :discord_id, :created_at, :updated_at)"
        ),
        {"id": user_id, "discord_id": "111222333", "created_at": now, "updated_at": now},
    )

    db_session.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, title, scheduled_at, guild_id, channel_id, host_id, "
            "status, created_at, updated_at) "
            "VALUES (:id, :title, :scheduled_at, :guild_id, :channel_id, :host_id, "
            ":status, :created_at, :updated_at)"
        ),
        {
            "id": game_id,
            "title": "Test Game",
            "scheduled_at": now + timedelta(hours=2),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": user_id,
            "status": "scheduled",
            "created_at": now,
            "updated_at": now,
        },
    )
    db_session.commit()

    yield game_id

    # Cleanup in reverse order
    db_session.execute(
        text("DELETE FROM notification_schedule WHERE game_id = :game_id"),
        {"game_id": game_id},
    )
    db_session.execute(text("DELETE FROM game_sessions WHERE id = :id"), {"id": game_id})
    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db_session.execute(
        text("DELETE FROM channel_configurations WHERE id = :id"), {"id": channel_id}
    )
    db_session.execute(text("DELETE FROM guild_configurations WHERE id = :id"), {"id": guild_id})
    db_session.commit()


@pytest.fixture
def rabbitmq_url():
    """Get RabbitMQ URL from environment (set by docker-compose)."""
    return os.getenv("RABBITMQ_URL", "amqp://gamebot:dev_password_change_in_prod@rabbitmq:5672/")


class TestPostgresListenerIntegration:
    """Integration tests for PostgreSQL LISTEN/NOTIFY."""

    def test_listener_connects_to_real_database(self, db_url):
        """Listener can connect to actual PostgreSQL database."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            assert listener.conn is not None
            assert not listener.conn.closed
        finally:
            listener.close()

    def test_listener_subscribes_to_channel(self, db_url):
        """Listener can subscribe to notification channel."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("test_channel")

            # Verify channel is registered
            assert "test_channel" in listener._channels
        finally:
            listener.close()

    def test_listener_receives_notify_from_trigger(
        self, db_url, db_session, clean_notification_schedule, test_game_session
    ):
        """Listener receives NOTIFY events from PostgreSQL trigger."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("notification_schedule_changed")

            # Insert notification record (should trigger NOTIFY)
            game_id = test_game_session
            notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            db_session.execute(
                text(
                    """
                    INSERT INTO notification_schedule
                        (id, game_id, reminder_minutes, notification_time, sent)
                    VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "game_id": game_id,
                    "reminder_minutes": 60,
                    "notification_time": notification_time,
                    "sent": False,
                },
            )
            db_session.commit()

            # Wait for notification with timeout
            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            assert payload is not None
            # Trigger only sends NOTIFY for near-term notifications
            # (within 10 minutes), so this may not trigger

        finally:
            listener.close()

    def test_listener_timeout_when_no_notification(self, db_url):
        """Listener times out when no notifications received."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("notification_schedule_changed")

            # Wait with short timeout
            start_time = time.time()
            received, payload = listener.wait_for_notification(timeout=0.5)
            elapsed_time = time.time() - start_time

            assert received is False
            assert payload is None
            assert 0.4 <= elapsed_time <= 0.7  # Allow some margin

        finally:
            listener.close()


class TestScheduleQueriesIntegration:
    """Integration tests for notification schedule queries."""

    def test_get_next_due_notification_returns_earliest(
        self, db_session, clean_notification_schedule, test_game_session
    ):
        """get_next_due_notification returns earliest unsent notification."""
        game_id = test_game_session
        now = datetime.now(UTC).replace(tzinfo=None)

        # Insert multiple notifications
        notifications = [
            {
                "id": str(uuid4()),
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": now + timedelta(hours=2),
                "sent": False,
            },
            {
                "id": str(uuid4()),
                "game_id": game_id,
                "reminder_minutes": 15,
                "notification_time": now + timedelta(minutes=30),
                "sent": False,
            },
            {
                "id": str(uuid4()),
                "game_id": game_id,
                "reminder_minutes": 5,
                "notification_time": now + timedelta(minutes=10),
                "sent": False,
            },
        ]

        for notif in notifications:
            db_session.execute(
                text(
                    """
                    INSERT INTO notification_schedule
                        (id, game_id, reminder_minutes, notification_time, sent)
                    VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                    """
                ),
                notif,
            )
        db_session.commit()

        # Query for next notification
        next_notif = get_next_due_notification(db_session)

        assert next_notif is not None
        # Should return the one due in 10 minutes (earliest)
        assert next_notif.reminder_minutes == 5
        assert next_notif.notification_time == now + timedelta(minutes=10)

    def test_get_next_due_notification_excludes_sent(
        self, db_session, clean_notification_schedule, test_game_session
    ):
        """get_next_due_notification excludes already sent notifications."""
        game_id = test_game_session
        now = datetime.now(UTC).replace(tzinfo=None)

        # Insert sent notification (earlier)
        db_session.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time, sent)
                VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                """
            ),
            {
                "id": str(uuid4()),
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": now + timedelta(minutes=10),
                "sent": True,  # Already sent
            },
        )

        # Insert unsent notification (later)
        unsent_id = str(uuid4())
        db_session.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time, sent)
                VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                """
            ),
            {
                "id": unsent_id,
                "game_id": game_id,
                "reminder_minutes": 15,
                "notification_time": now + timedelta(minutes=30),
                "sent": False,
            },
        )
        db_session.commit()

        # Should return unsent notification, not sent one
        next_notif = get_next_due_notification(db_session)

        assert next_notif is not None
        assert str(next_notif.id) == unsent_id
        assert next_notif.sent is False

    def test_mark_notification_sent_updates_database(
        self, db_session, clean_notification_schedule, test_game_session
    ):
        """mark_notification_sent updates notification in database."""
        game_id = test_game_session
        notif_id = str(uuid4())
        now = datetime.now(UTC).replace(tzinfo=None)

        # Insert notification
        db_session.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time, sent)
                VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                """
            ),
            {
                "id": notif_id,
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": now + timedelta(hours=1),
                "sent": False,
            },
        )
        db_session.commit()

        # Mark as sent
        result = mark_notification_sent(db_session, notif_id)

        assert result is True

        # Verify in database
        db_session.expire_all()
        updated = db_session.execute(
            text("SELECT sent FROM notification_schedule WHERE id = :id"),
            {"id": notif_id},
        ).scalar_one()

        assert updated is True


class TestNotificationDaemonIntegration:
    """Integration tests for notification daemon with real database."""

    def test_daemon_connects_to_database(self, db_url, rabbitmq_url):
        """Daemon can establish database connections."""
        daemon = NotificationDaemon(
            database_url=db_url,
            rabbitmq_url=rabbitmq_url,
        )

        try:
            daemon.connect()

            assert daemon.listener is not None
            assert daemon.publisher is not None
            assert daemon.db is not None

        finally:
            daemon._cleanup()

    def test_daemon_processes_due_notification(
        self, db_url, db_session, clean_notification_schedule, test_game_session
    ):
        """Daemon processes notification that is due now."""
        game_id = test_game_session
        notif_id = str(uuid4())
        # Notification due 1 minute ago
        notification_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        # Insert notification
        db_session.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time, sent)
                VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                """
            ),
            {
                "id": notif_id,
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "sent": False,
            },
        )
        db_session.commit()

        daemon = NotificationDaemon(
            database_url=db_url,
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
        )

        try:
            daemon.connect()

            # Process one iteration (should process the due notification)
            daemon._process_loop_iteration()

            # Verify notification marked as sent
            db_session.expire_all()
            updated = db_session.execute(
                text("SELECT sent FROM notification_schedule WHERE id = :id"),
                {"id": notif_id},
            ).scalar_one()

            assert updated is True

        finally:
            daemon._cleanup()

    def test_daemon_waits_for_future_notification(
        self, db_url, db_session, clean_notification_schedule, test_game_session
    ):
        """Daemon waits when notification is in future."""
        game_id = test_game_session
        notif_id = str(uuid4())
        # Notification due 10 minutes from now
        notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        # Insert notification
        db_session.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time, sent)
                VALUES (:id, :game_id, :reminder_minutes, :notification_time, :sent)
                """
            ),
            {
                "id": notif_id,
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "sent": False,
            },
        )
        db_session.commit()

        daemon = NotificationDaemon(
            database_url=db_url,
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            max_timeout=2,  # Short timeout for test
        )

        try:
            daemon.connect()

            # Process one iteration (should wait, not process)
            start_time = time.time()
            daemon._process_loop_iteration()
            elapsed = time.time() - start_time

            # Should have waited approximately max_timeout
            assert elapsed >= 1.5  # Allow some margin

            # Notification should NOT be marked as sent
            db_session.expire_all()
            still_unsent = db_session.execute(
                text("SELECT sent FROM notification_schedule WHERE id = :id"),
                {"id": notif_id},
            ).scalar_one()

            assert still_unsent is False

        finally:
            daemon._cleanup()
