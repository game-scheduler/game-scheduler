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

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment, converting asyncpg to psycopg2 for sync tests.

    Uses ADMIN_DATABASE_URL for infrastructure tests since these tests query
    metadata (information_schema) and should not be subject to RLS restrictions.
    """
    raw_url = os.getenv(
        "ADMIN_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
        ),
    )
    # Convert postgresql+asyncpg:// to postgresql:// for synchronous tests
    return raw_url.replace("postgresql+asyncpg://", "postgresql://")


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


def test_notification_schedule_schema(db_session):
    """Verify notification_schedule table has required columns with correct types."""
    result = db_session.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'notification_schedule'
            ORDER BY column_name
            """
        )
    )

    columns = {
        row[0]: {"type": row[1], "nullable": row[2], "default": row[3]} for row in result.fetchall()
    }

    # Verify core columns exist
    required_columns = {
        "id": "character varying",
        "game_id": "character varying",
        "reminder_minutes": "integer",
        "notification_time": "timestamp without time zone",
        "game_scheduled_at": "timestamp without time zone",
        "sent": "boolean",
        "created_at": "timestamp without time zone",
        "notification_type": "character varying",
        "participant_id": "character varying",
    }

    for col_name, expected_type in required_columns.items():
        assert col_name in columns, f"Missing column: {col_name}"
        assert columns[col_name]["type"] == expected_type, (
            f"Column {col_name} has type {columns[col_name]['type']}, expected {expected_type}"
        )

    # Verify notification_type has default value
    assert "reminder" in columns["notification_type"]["default"], (
        "notification_type should default to 'reminder'"
    )

    # Verify participant_id is nullable (for game-wide reminders)
    assert columns["participant_id"]["nullable"] == "YES", "participant_id should be nullable"

    # Verify notification_type is not nullable
    assert columns["notification_type"]["nullable"] == "NO", (
        "notification_type should not be nullable"
    )


def test_notification_schedule_indexes(db_session):
    """Verify notification_schedule has required indexes."""
    result = db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'notification_schedule'
            ORDER BY indexname
            """
        )
    )

    indexes = [row[0] for row in result.fetchall()]

    expected_indexes = [
        "ix_notification_schedule_game_id",
        "ix_notification_schedule_notification_time",
        "ix_notification_schedule_participant_id",
        "ix_notification_schedule_type_time",
    ]

    for expected_index in expected_indexes:
        assert expected_index in indexes, f"Missing index: {expected_index}"


def test_notification_schedule_foreign_keys(db_session):
    """Verify notification_schedule foreign key constraints."""
    result = db_session.execute(
        text(
            """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'notification_schedule'
            ORDER BY kcu.column_name
            """
        )
    )

    rows = result.fetchall()

    fks = {row[0]: {"table": row[1], "column": row[2], "delete": row[4]} for row in rows}

    # Verify game_id foreign key with CASCADE delete
    assert "game_id" in fks, "Missing foreign key on game_id"
    assert fks["game_id"]["table"] == "game_sessions"
    assert fks["game_id"]["delete"] == "CASCADE"

    # Verify participant_id foreign key with CASCADE delete
    assert "participant_id" in fks, "Missing foreign key on participant_id"
    assert fks["participant_id"]["table"] == "game_participants"
    assert fks["participant_id"]["delete"] == "CASCADE"


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


def test_game_sessions_image_storage_schema(db_session):
    """Verify game_sessions table has FK references to game_images table."""
    result = db_session.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'game_sessions'
            AND column_name IN ('thumbnail_id', 'banner_image_id')
            ORDER BY column_name
            """
        )
    )

    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

    required_columns = {
        "thumbnail_id": "uuid",
        "banner_image_id": "uuid",
    }

    for col_name, expected_type in required_columns.items():
        assert col_name in columns, f"Missing column: {col_name}"
        assert columns[col_name]["type"] == expected_type, (
            f"Column {col_name} has type {columns[col_name]['type']}, expected {expected_type}"
        )
        assert columns[col_name]["nullable"] == "YES", f"Column {col_name} should be nullable"

    result = db_session.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'game_images'
            AND column_name IN ('content_hash', 'image_data', 'mime_type', 'reference_count')
            ORDER BY column_name
            """
        )
    )

    game_images_columns = {
        row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()
    }

    required_game_images_columns = {
        "content_hash": "character varying",
        "image_data": "bytea",
        "mime_type": "character varying",
        "reference_count": "integer",
    }

    for col_name, expected_type in required_game_images_columns.items():
        assert col_name in game_images_columns, f"Missing game_images column: {col_name}"
        assert game_images_columns[col_name]["type"] == expected_type, (
            f"Column {col_name} has type {game_images_columns[col_name]['type']}, "
            f"expected {expected_type}"
        )


def test_rls_enabled_on_tenant_tables(db_session):
    """Verify Row-Level Security is enabled on all tenant-scoped tables."""
    tenant_tables = [
        "game_sessions",
        "game_templates",
        "game_participants",
        "guild_configurations",
    ]

    for table_name in tenant_tables:
        result = db_session.execute(
            text(
                """
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = :table_name
                """
            ),
            {"table_name": table_name},
        )
        row = result.fetchone()

        assert row is not None, f"Table {table_name} not found"
        assert row[1] is True, f"RLS not enabled on {table_name} (rowsecurity = {row[1]})"


def test_rls_policies_exist_on_tenant_tables(db_session):
    """Verify RLS policies exist for all tenant-scoped tables."""
    expected_policies = {
        "game_sessions": "guild_isolation_games",
        "game_templates": "guild_isolation_templates",
        "game_participants": "guild_isolation_participants",
        "guild_configurations": "guild_isolation_configurations",
    }

    for table_name, policy_name in expected_policies.items():
        result = db_session.execute(
            text(
                """
                SELECT policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                AND tablename = :table_name
                """
            ),
            {"table_name": table_name},
        )
        policies = [row[0] for row in result.fetchall()]

        assert policy_name in policies, (
            f"Policy {policy_name} not found on {table_name}. Found: {policies}"
        )
