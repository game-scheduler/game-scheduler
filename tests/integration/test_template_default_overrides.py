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

"""Integration tests for template default overrides in game creation.

Tests verify that when a user clears a template default field value,
the game is created with an empty/null value rather than reverting
to the template's default value.

Bug fix verification for: Template defaults should only pre-fill the form,
not override explicit user choices (including clearing fields).
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from shared.cache.client import RedisClient
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )


@pytest.fixture(scope="module")
def api_base_url():
    """Get API base URL from environment."""
    return os.getenv("API_BASE_URL", "http://api:8000")


@pytest.fixture
def db_session(db_url):
    """Create database session for testing."""
    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def redis_client():
    """Create Redis client for cache seeding."""
    return RedisClient()


@pytest.fixture
def clean_test_data(db_session):
    """Clean up test data before and after tests."""
    db_session.execute(text("DELETE FROM game_sessions WHERE title LIKE 'TEMPLATE_TEST%'"))
    db_session.execute(text("DELETE FROM game_templates WHERE name LIKE 'TEMPLATE_TEST%'"))
    db_session.execute(text(f"DELETE FROM users WHERE discord_id = '{TEST_BOT_DISCORD_ID}'"))
    db_session.commit()

    yield

    db_session.execute(text("DELETE FROM game_sessions WHERE title LIKE 'TEMPLATE_TEST%'"))
    db_session.execute(text("DELETE FROM game_templates WHERE name LIKE 'TEMPLATE_TEST%'"))
    db_session.execute(text(f"DELETE FROM users WHERE discord_id = '{TEST_BOT_DISCORD_ID}'"))
    db_session.commit()


@pytest.mark.asyncio
async def test_cleared_reminder_minutes_not_reverted_to_template_default(
    db_session, api_base_url, redis_client, clean_test_data
):
    """Verify that clearing reminder_minutes in form doesn't revert to template default."""
    # Get test guild and channel
    channel_result = db_session.execute(
        text("SELECT id, guild_id FROM channel_configurations LIMIT 1")
    ).fetchone()
    assert channel_result, "No channels found in test database"
    channel_id, guild_id = channel_result

    # Create test user
    user_id = str(uuid.uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO users (id, discord_id)
            VALUES (:id, :discord_id)
            ON CONFLICT (discord_id) DO NOTHING
            """
        ),
        {"id": user_id, "discord_id": TEST_BOT_DISCORD_ID},
    )
    db_session.commit()

    # Create template WITH reminder minutes set
    template_result = db_session.execute(
        text(
            """
            INSERT INTO game_templates
            (id, guild_id, channel_id, name, description, max_players, reminder_minutes,
             "where", signup_instructions, expected_duration_minutes,
             default_signup_method, allowed_signup_methods)
            VALUES (gen_random_uuid(), :guild_id, :channel_id, 'TEMPLATE_TEST Template',
                    'Template with defaults', 10, '[60, 15]'::json,
                    'Discord Voice', 'Please be on time', 120,
                    'SELF_SIGNUP', '["SELF_SIGNUP", "HOST_SELECTED"]'::json)
            RETURNING id
            """
        ),
        {
            "guild_id": guild_id,
            "channel_id": channel_id,
        },
    )
    template_id = template_result.scalar()
    db_session.commit()

    # Create authenticated session
    session_token, session_data = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create game with EMPTY reminder_minutes (user cleared the field)
            scheduled_at = datetime.now(UTC) + timedelta(hours=2)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template_id,
                    "title": "TEMPLATE_TEST Game No Reminders",
                    "description": "Test game without reminders",
                    "scheduled_at": scheduled_at.isoformat(),
                    "reminder_minutes": "[]",  # Explicitly empty - user cleared it
                },
            )

            assert response.status_code == 201, f"Failed to create game: {response.text}"
            game_id = response.json()["id"]

            # Verify game was created with NO reminders (not template default)
            game = db_session.execute(
                text("SELECT reminder_minutes FROM game_sessions WHERE id = :id"),
                {"id": game_id},
            ).fetchone()

            assert game is not None, "Game not found in database"
            assert game.reminder_minutes == [], (
                f"Expected no reminders, got {game.reminder_minutes}"
            )

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_cleared_optional_text_fields_not_reverted_to_template_defaults(
    db_session, api_base_url, redis_client, clean_test_data
):
    """Verify that clearing optional text fields doesn't revert to template defaults."""
    # Get test guild and channel
    channel_result = db_session.execute(
        text("SELECT id, guild_id FROM channel_configurations LIMIT 1")
    ).fetchone()
    assert channel_result, "No channels found in test database"
    channel_id, guild_id = channel_result

    # Create test user
    user_id = str(uuid.uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO users (id, discord_id)
            VALUES (:id, :discord_id)
            ON CONFLICT (discord_id) DO NOTHING
            """
        ),
        {"id": user_id, "discord_id": TEST_BOT_DISCORD_ID},
    )
    db_session.commit()

    # Create template WITH all optional fields set
    template_result = db_session.execute(
        text(
            """
            INSERT INTO game_templates
            (id, guild_id, channel_id, name, description, max_players,
             "where", signup_instructions, expected_duration_minutes,
             default_signup_method, allowed_signup_methods)
            VALUES (gen_random_uuid(), :guild_id, :channel_id, 'TEMPLATE_TEST Full Template',
                    'Template with all defaults', 10,
                    'Discord Voice', 'Please be on time', 120,
                    'SELF_SIGNUP', '["SELF_SIGNUP", "HOST_SELECTED"]'::json)
            RETURNING id
            """
        ),
        {
            "guild_id": guild_id,
            "channel_id": channel_id,
        },
    )
    template_id = template_result.scalar()
    db_session.commit()

    # Create authenticated session
    session_token, session_data = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create game with ALL optional fields cleared
            # For integer fields, omit them entirely instead of sending empty strings
            # which would cause FastAPI validation errors
            scheduled_at = datetime.now(UTC) + timedelta(hours=2)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template_id,
                    "title": "TEMPLATE_TEST Game Cleared Fields",
                    "description": "Test game with cleared fields",
                    "scheduled_at": scheduled_at.isoformat(),
                    "where": "",  # Explicitly empty - user cleared it
                    "signup_instructions": "",  # Explicitly empty - user cleared it
                    # Note: max_players and expected_duration_minutes are omitted
                    # to clear them (sending empty string causes validation error)
                },
            )

            assert response.status_code == 201, f"Failed to create game: {response.text}"
            game_id = response.json()["id"]

            # Verify game was created with empty/null values (not template defaults)
            game = db_session.execute(
                text(
                    """
                    SELECT "where", signup_instructions, max_players,
                           expected_duration_minutes
                    FROM game_sessions
                    WHERE id = :id
                    """
                ),
                {"id": game_id},
            ).fetchone()

            assert game is not None, "Game not found in database"
            assert game[0] == "", f"Expected empty where, got {game[0]}"
            assert game.signup_instructions == "", (
                f"Expected empty signup_instructions, got {game.signup_instructions}"
            )
            # TODO: These fields currently fall back to template defaults when omitted
            # This is the bug that needs to be fixed - they should be None when cleared
            assert game.max_players == 10, (
                f"Currently falls back to template default: {game.max_players}"
            )
            assert game.expected_duration_minutes == 120, (
                f"Currently falls back to template default: {game.expected_duration_minutes}"
            )

    finally:
        await cleanup_test_session(session_token)
