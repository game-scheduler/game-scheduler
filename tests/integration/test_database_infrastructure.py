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


"""Integration tests for PostgreSQL database infrastructure.

Tests verify that the database initialization creates all required infrastructure:
1. PostgreSQL version compatibility
2. Schema completeness (all expected tables)
3. Alembic migration status
4. Critical indexes for performance
5. Database triggers for LISTEN/NOTIFY functionality
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )


@pytest.fixture(scope="module")
def db_engine(db_url):
    """Create database engine for testing."""
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create database session for testing."""
    session_factory = sessionmaker(bind=db_engine)
    session = session_factory()
    yield session
    session.close()


def test_postgresql_version_compatibility(db_session):
    """Verify PostgreSQL version is 17.x or compatible."""
    result = db_session.execute(text("SELECT version()")).fetchone()
    version_string = result[0]

    assert "PostgreSQL" in version_string
    # Extract major version (e.g., "PostgreSQL 17.7" -> 17)
    version_parts = version_string.split()[1].split(".")
    major_version = int(version_parts[0])

    # Verify we're running on PostgreSQL 17 or newer
    assert major_version >= 17, f"Expected PostgreSQL 17+, got {major_version}"


def test_all_expected_tables_exist(db_session):
    """Verify all expected tables are present in the database."""
    expected_tables = [
        "alembic_version",
        "channel_configurations",
        "game_participants",
        "game_sessions",
        "game_status_schedule",
        "game_templates",
        "guild_configurations",
        "notification_schedule",
        "users",
    ]

    result = db_session.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
    )

    actual_tables = [row[0] for row in result.fetchall()]

    for expected_table in expected_tables:
        assert expected_table in actual_tables, f"Missing expected table: {expected_table}"


def test_alembic_migration_status(db_session):
    """Verify Alembic migrations have been applied."""
    result = db_session.execute(text("SELECT version_num FROM alembic_version")).fetchone()

    assert result is not None, "No Alembic version found - migrations not applied"

    version = result[0]
    assert version is not None and len(version) > 0, "Alembic version is empty"

    # Version should be in format like "021_add_game_scheduled_at"
    assert "_" in version, f"Unexpected Alembic version format: {version}"


def test_critical_indexes_exist(db_session):
    """Verify performance-critical indexes are present."""
    expected_indexes = {
        "users": ["ix_users_discord_id"],
        "guild_configurations": ["ix_guild_configurations_guild_id"],
        "game_sessions": [
            "ix_game_sessions_created_at",
            "ix_game_sessions_status",
            "ix_game_sessions_template_id",
        ],
    }

    for table_name, index_names in expected_indexes.items():
        result = db_session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = :table_name
                ORDER BY indexname
                """
            ),
            {"table_name": table_name},
        )

        actual_indexes = [row[0] for row in result.fetchall()]

        for expected_index in index_names:
            assert expected_index in actual_indexes, (
                f"Missing index {expected_index} on table {table_name}"
            )


def test_notification_trigger_exists(db_session):
    """Verify NOTIFY trigger exists on notification_schedule table."""
    result = db_session.execute(
        text(
            """
            SELECT trigger_name
            FROM information_schema.triggers
            WHERE event_object_table = 'notification_schedule'
            AND trigger_name = 'notification_schedule_trigger'
            """
        )
    )

    trigger = result.fetchone()
    assert trigger is not None, "notification_schedule_trigger not found"


def test_status_schedule_trigger_exists(db_session):
    """Verify NOTIFY trigger exists on game_status_schedule table."""
    result = db_session.execute(
        text(
            """
            SELECT trigger_name
            FROM information_schema.triggers
            WHERE event_object_table = 'game_status_schedule'
            AND trigger_name = 'game_status_schedule_trigger'
            """
        )
    )

    trigger = result.fetchone()
    assert trigger is not None, "game_status_schedule_trigger not found"


def test_foreign_key_constraints_exist(db_session):
    """Verify critical foreign key constraints are present."""
    # Check game_sessions has foreign keys to guild and channel configurations
    result = db_session.execute(
        text(
            """
            SELECT constraint_name, table_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name IN ('game_sessions', 'game_participants', 'notification_schedule')
            AND constraint_type = 'FOREIGN KEY'
            ORDER BY table_name, constraint_name
            """
        )
    )

    constraints = result.fetchall()

    # Should have multiple foreign key constraints across these tables
    assert len(constraints) > 0, "No foreign key constraints found on critical tables"

    # Verify specific important foreign keys exist
    table_names = [row[1] for row in constraints]

    assert "game_sessions" in table_names, "No foreign keys on game_sessions table"
    assert "game_participants" in table_names, "No foreign keys on game_participants table"
    assert "notification_schedule" in table_names, "No foreign keys on notification_schedule table"


def test_database_connection_healthy(db_session):
    """Verify basic database connectivity and query execution."""
    result = db_session.execute(text("SELECT 1 AS health_check")).fetchone()
    assert result[0] == 1, "Database health check failed"


def test_primary_keys_exist(db_session):
    """Verify all tables have primary key constraints."""
    result = db_session.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'alembic_version'
            ORDER BY tablename
            """
        )
    )

    tables = [row[0] for row in result.fetchall()]

    for table_name in tables:
        pk_result = db_session.execute(
            text(
                """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = :table_name
                AND constraint_type = 'PRIMARY KEY'
                """
            ),
            {"table_name": table_name},
        )

        pk = pk_result.fetchone()
        assert pk is not None, f"Table {table_name} is missing a primary key"
