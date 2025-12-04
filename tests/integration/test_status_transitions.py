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


"""Integration tests for status transition daemon with PostgreSQL LISTEN/NOTIFY.

These tests are designed to run in Docker with docker-compose where all
services (PostgreSQL, RabbitMQ) are available.
"""

import os
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import services.scheduler.status_transition_daemon as daemon_module
from services.scheduler.postgres_listener import PostgresNotificationListener
from services.scheduler.status_schedule_queries import (
    get_next_due_transition,
    mark_transition_executed,
)
from services.scheduler.status_transition_daemon import StatusTransitionDaemon


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
def clean_game_status_schedule(db_session):
    """Clean game_status_schedule table before and after test."""
    db_session.execute(text("DELETE FROM game_status_schedule"))
    db_session.commit()

    yield

    db_session.execute(text("DELETE FROM game_status_schedule"))
    db_session.commit()


@pytest.fixture
def test_game_session(db_session):
    """
    Create minimal test data for foreign key constraints.

    Creates: guild -> channel -> user -> game_session
    Returns the game_session.id for use in game_status_schedule inserts.
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
        {
            "id": guild_id,
            "guild_id": "123456789",
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_id,
            "channel_id": "987654321",
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
            "status": "SCHEDULED",
            "created_at": now,
            "updated_at": now,
        },
    )
    db_session.commit()

    yield game_id

    # Cleanup in reverse order
    db_session.execute(
        text("DELETE FROM game_status_schedule WHERE game_id = :game_id"),
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


@pytest.fixture(autouse=True)
def reset_shutdown_flag():
    """Reset daemon shutdown flag before and after each test."""
    daemon_module.shutdown_requested = False
    yield
    daemon_module.shutdown_requested = False


class TestPostgresListenerIntegration:
    """Integration tests for PostgreSQL LISTEN/NOTIFY on game_status_schedule."""

    def test_listener_receives_notify_from_status_schedule_trigger(
        self, db_url, db_session, clean_game_status_schedule, test_game_session
    ):
        """Listener receives NOTIFY events from game_status_schedule trigger."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("game_status_schedule_changed")

            # Insert status schedule record (should trigger NOTIFY)
            game_id = test_game_session
            transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            db_session.execute(
                text(
                    """
                    INSERT INTO game_status_schedule
                        (id, game_id, target_status, transition_time, executed)
                    VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "game_id": game_id,
                    "target_status": "IN_PROGRESS",
                    "transition_time": transition_time,
                    "executed": False,
                },
            )
            db_session.commit()

            # Wait for notification with timeout
            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            assert payload is not None

        finally:
            listener.close()


class TestStatusScheduleQueries:
    """Integration tests for status schedule query functions."""

    def test_get_next_due_status_transition_with_due_transition(
        self, db_url, db_session, clean_game_status_schedule, test_game_session
    ):
        """get_next_due_transition returns transition when due."""
        game_id = test_game_session
        transition_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": str(uuid4()),
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        result = get_next_due_transition(db_session)

        assert result is not None
        assert result.game_id == game_id
        assert result.target_status == "IN_PROGRESS"
        assert result.executed is False

    def test_mark_status_transition_executed(
        self, db_url, db_session, clean_game_status_schedule, test_game_session
    ):
        """mark_transition_executed marks transition as executed."""
        game_id = test_game_session
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        mark_transition_executed(db_session, schedule_id)

        result = db_session.execute(
            text("SELECT executed FROM game_status_schedule WHERE id = :id"),
            {"id": schedule_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row[0] is True


class TestStatusTransitionDaemonIntegration:
    """Integration tests for StatusTransitionDaemon end-to-end functionality."""

    def test_daemon_transitions_game_status_when_due(
        self, db_url, db_session, rabbitmq_url, clean_game_status_schedule, test_game_session
    ):
        """Daemon updates game status and publishes event when transition is due."""
        game_id = test_game_session
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=5)

        # Insert due transition
        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        daemon = StatusTransitionDaemon(db_url, rabbitmq_url)

        try:
            # Run daemon in background thread
            daemon_thread = threading.Thread(target=daemon.run, daemon=True)
            daemon_thread.start()

            # Wait for daemon to process transition
            time.sleep(3)

            # Verify game status updated
            result = db_session.execute(
                text("SELECT status FROM game_sessions WHERE id = :id"),
                {"id": game_id},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "IN_PROGRESS"

            # Verify schedule marked executed
            result = db_session.execute(
                text("SELECT executed FROM game_status_schedule WHERE id = :id"),
                {"id": schedule_id},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] is True

        finally:
            # Stop daemon using shutdown flag
            daemon_module.shutdown_requested = True
            daemon_thread.join(timeout=2)

    def test_daemon_handles_multiple_due_transitions(
        self, db_url, db_session, rabbitmq_url, clean_game_status_schedule
    ):
        """Daemon processes multiple due transitions correctly."""
        # Create multiple games
        game_ids = []
        schedule_ids = []
        now = datetime.now(UTC).replace(tzinfo=None)

        for i in range(3):
            guild_id = str(uuid4())
            channel_id = str(uuid4())
            user_id = str(uuid4())
            game_id = str(uuid4())
            schedule_id = str(uuid4())

            db_session.execute(
                text(
                    "INSERT INTO guild_configurations "
                    "(id, guild_id, created_at, updated_at) "
                    "VALUES (:id, :guild_id, :created_at, :updated_at)"
                ),
                {
                    "id": guild_id,
                    "guild_id": f"guild_{i}",
                    "created_at": now,
                    "updated_at": now,
                },
            )

            db_session.execute(
                text(
                    "INSERT INTO channel_configurations "
                    "(id, channel_id, guild_id, created_at, updated_at) "
                    "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
                ),
                {
                    "id": channel_id,
                    "channel_id": f"channel_{i}",
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
                {
                    "id": user_id,
                    "discord_id": f"user_{i}",
                    "created_at": now,
                    "updated_at": now,
                },
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
                    "title": f"Test Game {i}",
                    "scheduled_at": now - timedelta(minutes=5),
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "host_id": user_id,
                    "status": "SCHEDULED",
                    "created_at": now,
                    "updated_at": now,
                },
            )

            db_session.execute(
                text(
                    """
                    INSERT INTO game_status_schedule
                        (id, game_id, target_status, transition_time, executed)
                    VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                    """
                ),
                {
                    "id": schedule_id,
                    "game_id": game_id,
                    "target_status": "IN_PROGRESS",
                    "transition_time": now - timedelta(minutes=5),
                    "executed": False,
                },
            )

            game_ids.append(game_id)
            schedule_ids.append(schedule_id)

        db_session.commit()

        daemon = StatusTransitionDaemon(db_url, rabbitmq_url)

        try:
            # Run daemon in background thread
            daemon_thread = threading.Thread(target=daemon.run, daemon=True)
            daemon_thread.start()

            # Wait for daemon to process all transitions
            time.sleep(5)

            # Verify all games transitioned
            for game_id in game_ids:
                result = db_session.execute(
                    text("SELECT status FROM game_sessions WHERE id = :id"),
                    {"id": game_id},
                )
                row = result.fetchone()
                assert row is not None
                assert row[0] == "IN_PROGRESS"

            # Verify all schedules marked executed
            for schedule_id in schedule_ids:
                result = db_session.execute(
                    text("SELECT executed FROM game_status_schedule WHERE id = :id"),
                    {"id": schedule_id},
                )
                row = result.fetchone()
                assert row is not None
                assert row[0] is True

        finally:
            # Stop daemon using shutdown flag
            import services.scheduler.status_transition_daemon as daemon_module

            daemon_module.shutdown_requested = True
            if daemon_thread.is_alive():
                daemon_thread.join(timeout=2)

            # Cleanup
            for game_id in game_ids:
                db_session.execute(
                    text("DELETE FROM game_status_schedule WHERE game_id = :game_id"),
                    {"game_id": game_id},
                )
                db_session.execute(
                    text("DELETE FROM game_sessions WHERE id = :id"), {"id": game_id}
                )
            db_session.commit()

    def test_daemon_waits_for_future_transition(
        self, db_url, db_session, rabbitmq_url, clean_game_status_schedule, test_game_session
    ):
        """Daemon waits and processes transition when time arrives."""
        game_id = test_game_session
        schedule_id = str(uuid4())
        # Set transition 3 seconds in the future
        transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=3)

        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        daemon = StatusTransitionDaemon(db_url, rabbitmq_url)

        try:
            # Run daemon in background thread
            daemon_thread = threading.Thread(target=daemon.run, daemon=True)
            daemon_thread.start()

            # Wait for transition time to pass
            time.sleep(5)

            # Verify game status updated
            result = db_session.execute(
                text("SELECT status FROM game_sessions WHERE id = :id"),
                {"id": game_id},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "IN_PROGRESS"

        finally:
            # Stop daemon using shutdown flag
            import services.scheduler.status_transition_daemon as daemon_module

            daemon_module.shutdown_requested = True
            if daemon_thread.is_alive():
                daemon_thread.join(timeout=2)
