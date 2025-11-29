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


"""End-to-end API tests for game notification flow.

Tests the complete pipeline through API endpoints:
1. POST /games → notification_schedule populated
2. Notification daemon processes → RabbitMQ events published
3. PUT /games → schedule recalculated
4. DELETE /games → schedule cleaned up

Requires:
- PostgreSQL with migrations applied
- RabbitMQ with exchanges/queues configured
- API service running on localhost:8000
- Notification daemon running
"""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def api_base_url():
    """Get API base URL from environment."""
    import os

    return os.getenv("API_BASE_URL", "http://api:8000")


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment."""
    import os

    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot_e2e:e2e_password@postgres:5432/game_scheduler_e2e",
    )


@pytest.fixture
def db_session(db_url):
    """Create a database session for verification queries."""
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
def http_client(api_base_url):
    """Create HTTP client for API requests."""
    with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def clean_test_data(db_session):
    """Clean up test data before and after test."""
    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.execute(text("DELETE FROM game_participants"))
    db_session.execute(text("DELETE FROM game_sessions"))
    db_session.execute(text("DELETE FROM users"))
    db_session.execute(text("DELETE FROM channel_configurations"))
    db_session.execute(text("DELETE FROM guild_configurations"))
    db_session.commit()

    yield

    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.execute(text("DELETE FROM game_participants"))
    db_session.execute(text("DELETE FROM game_sessions"))
    db_session.execute(text("DELETE FROM users"))
    db_session.execute(text("DELETE FROM channel_configurations"))
    db_session.execute(text("DELETE FROM guild_configurations"))
    db_session.commit()


@pytest.fixture
def test_guild_data(db_session, clean_test_data):
    """Create test guild via database for API to reference."""
    import json

    guild_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    db_session.execute(
        text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, guild_name, created_at, updated_at, "
            "default_reminder_minutes) "
            "VALUES (:id, :guild_id, :guild_name, :created_at, :updated_at, "
            ":default_reminder_minutes::jsonb)"
        ),
        {
            "id": guild_id,
            "guild_id": "123456789",
            "guild_name": "Test Guild",
            "created_at": now,
            "updated_at": now,
            "default_reminder_minutes": json.dumps([60, 30, 15]),
        },
    )

    channel_id = str(uuid4())
    db_session.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, channel_name, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :channel_name, :guild_id, "
            ":created_at, :updated_at)"
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

    user_id = str(uuid4())
    db_session.execute(
        text(
            "INSERT INTO users (id, discord_id, created_at, updated_at) "
            "VALUES (:id, :discord_id, :created_at, :updated_at)"
        ),
        {
            "id": user_id,
            "discord_id": "111222333",
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.commit()

    return {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
    }


class TestGameNotificationAPIFlow:
    """End-to-end API tests for game notification flow."""

    def test_create_game_via_api_populates_schedule(self, http_client, db_session, test_guild_data):
        """Creating game via API populates notification_schedule table."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)

        # Create game via API
        response = http_client.post(
            "/api/games",
            json={
                "title": "E2E Test Game",
                "scheduled_at": scheduled_at.isoformat(),
                "guild_id": test_guild_data["guild_id"],
                "channel_id": test_guild_data["channel_id"],
                "host_id": test_guild_data["user_id"],
                "max_players": 4,
                "reminder_minutes": [60, 30],
            },
        )

        assert response.status_code == 201, f"API error: {response.text}"
        game_data = response.json()
        game_id = game_data["id"]

        # Verify notification_schedule populated via database
        result = db_session.execute(
            text(
                "SELECT reminder_minutes, notification_time, sent "
                "FROM notification_schedule WHERE game_id = :game_id "
                "ORDER BY reminder_minutes DESC"
            ),
            {"game_id": game_id},
        )
        notifications = result.fetchall()

        assert len(notifications) == 2
        assert notifications[0].reminder_minutes == 60
        assert notifications[0].sent is False
        assert notifications[1].reminder_minutes == 30
        assert notifications[1].sent is False

    def test_daemon_processes_notification_for_api_created_game(
        self, http_client, db_session, test_guild_data
    ):
        """Daemon processes notifications for games created via API."""
        scheduled_at = datetime.now(UTC) + timedelta(minutes=1)

        # Create game via API with very short notification window
        response = http_client.post(
            "/api/games",
            json={
                "title": "E2E Test Game - Due Soon",
                "scheduled_at": scheduled_at.isoformat(),
                "guild_id": test_guild_data["guild_id"],
                "channel_id": test_guild_data["channel_id"],
                "host_id": test_guild_data["user_id"],
                "max_players": 4,
                "reminder_minutes": [1],
            },
        )

        assert response.status_code == 201
        game_id = response.json()["id"]

        # Wait for daemon to process notification
        time.sleep(90)

        # Verify notification was marked as sent
        result = db_session.execute(
            text("SELECT sent FROM notification_schedule WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        notification = result.fetchone()

        assert notification is not None
        assert notification.sent is True

    def test_update_game_via_api_recalculates_schedule(
        self, http_client, db_session, test_guild_data
    ):
        """Updating game via API recalculates notification schedule."""
        original_scheduled_at = datetime.now(UTC) + timedelta(hours=2)

        # Create game via API
        response = http_client.post(
            "/api/games",
            json={
                "title": "E2E Test Game - To Update",
                "scheduled_at": original_scheduled_at.isoformat(),
                "guild_id": test_guild_data["guild_id"],
                "channel_id": test_guild_data["channel_id"],
                "host_id": test_guild_data["user_id"],
                "max_players": 4,
                "reminder_minutes": [60],
            },
        )

        assert response.status_code == 201
        game_id = response.json()["id"]

        # Get original notification time
        result = db_session.execute(
            text("SELECT notification_time FROM notification_schedule WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        original_notification_time = result.scalar_one()

        # Update game scheduled_at via API
        new_scheduled_at = original_scheduled_at + timedelta(hours=1)
        response = http_client.put(
            f"/api/games/{game_id}",
            json={
                "scheduled_at": new_scheduled_at.isoformat(),
            },
        )

        assert response.status_code == 200

        # Verify schedule recalculated
        result = db_session.execute(
            text("SELECT notification_time FROM notification_schedule WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        updated_notification_time = result.scalar_one()

        time_difference = (updated_notification_time - original_notification_time).total_seconds()
        assert abs(time_difference - 3600) < 1

    def test_delete_game_via_api_cleans_schedule(self, http_client, db_session, test_guild_data):
        """Deleting game via API removes notification_schedule records."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)

        # Create game via API
        response = http_client.post(
            "/api/games",
            json={
                "title": "E2E Test Game - To Delete",
                "scheduled_at": scheduled_at.isoformat(),
                "guild_id": test_guild_data["guild_id"],
                "channel_id": test_guild_data["channel_id"],
                "host_id": test_guild_data["user_id"],
                "max_players": 4,
                "reminder_minutes": [60, 30],
            },
        )

        assert response.status_code == 201
        game_id = response.json()["id"]

        # Verify schedule exists
        result = db_session.execute(
            text("SELECT COUNT(*) FROM notification_schedule WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        count_before = result.scalar()
        assert count_before == 2

        # Delete game via API
        response = http_client.delete(f"/api/games/{game_id}")

        assert response.status_code == 204

        # Verify schedule cleaned up
        result = db_session.execute(
            text("SELECT COUNT(*) FROM notification_schedule WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        count_after = result.scalar()
        assert count_after == 0
