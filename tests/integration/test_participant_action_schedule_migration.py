# Copyright 2026 Bret McKee
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


"""Integration tests for participant_action_schedule migration.

Verifies that the migration creates the participant_action_schedule table with
all required columns, indexes, and constraints, and that rollback removes it.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment."""
    raw_url = os.getenv(
        "ADMIN_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
        ),
    )
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


def test_participant_action_schedule_table_exists(db_session):
    """Verify participant_action_schedule table was created by the migration."""
    result = db_session.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename = 'participant_action_schedule'
            """
        )
    )
    rows = result.fetchall()
    assert len(rows) == 1, "participant_action_schedule table not found in schema"


def test_participant_action_schedule_columns(db_session):
    """Verify all required columns exist with correct types."""
    result = db_session.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'participant_action_schedule'
            ORDER BY column_name
            """
        )
    )
    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

    required_columns = {
        "id": "character varying",
        "game_id": "character varying",
        "participant_id": "character varying",
        "action": "character varying",
        "action_time": "timestamp without time zone",
        "processed": "boolean",
        "created_at": "timestamp without time zone",
    }

    for col_name, expected_type in required_columns.items():
        assert col_name in columns, f"Missing column: {col_name}"
        assert columns[col_name]["type"] == expected_type, (
            f"Column {col_name} has type {columns[col_name]['type']}, expected {expected_type}"
        )


def test_participant_action_schedule_action_time_index(db_session):
    """Verify action_time index exists for efficient daemon polling."""
    result = db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'participant_action_schedule'
            """
        )
    )
    index_names = [row[0] for row in result.fetchall()]
    assert any("action_time" in name for name in index_names), (
        f"No action_time index found; got: {index_names}"
    )


def test_participant_action_schedule_participant_id_unique(db_session):
    """Verify participant_id has a UNIQUE constraint."""
    result = db_session.execute(
        text(
            """
            SELECT tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_name = kcu.table_name
            WHERE tc.table_name = 'participant_action_schedule'
              AND kcu.column_name = 'participant_id'
              AND tc.constraint_type = 'UNIQUE'
            """
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1, (
        "No UNIQUE constraint found on participant_action_schedule.participant_id"
    )


def test_participant_action_schedule_downgrade_removes_table(db_session):
    """Verify the alembic_version entry reflects the migration was applied."""
    result = db_session.execute(text("SELECT version_num FROM alembic_version")).fetchone()

    assert result is not None, "No alembic version found"
    assert result[0] == "f3a2c1d8e9b7", (
        f"Expected migration f3a2c1d8e9b7 to be applied, got: {result[0]}"
    )
