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


"""Integration tests for game creation with signup methods.

Tests verify the complete API → Database → RabbitMQ flow for signup method
propagation. These tests ensure that signup_method values flow correctly
through the entire HTTP/auth/service/messaging stack.

Uses fake Discord credentials since integration tests don't connect to Discord.
"""

import asyncio
import json
import os
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

# Test Discord token (format valid but doesn't need to work - no Discord connection)
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
    # Collect host user IDs from test game sessions before deleting them
    host_ids_result = db_session.execute(
        text("SELECT DISTINCT host_id FROM game_sessions WHERE title LIKE 'INT_TEST%'")
    )
    host_ids = [row[0] for row in host_ids_result.fetchall()]

    # Delete test game sessions (cascades to participants via FK)
    db_session.execute(text("DELETE FROM game_sessions WHERE title LIKE 'INT_TEST%'"))
    # Delete test templates
    db_session.execute(text("DELETE FROM game_templates WHERE name LIKE 'INT_TEST%'"))
    # Delete test users - host users from games plus the bot user
    if host_ids:
        placeholders = ",".join([f":id{i}" for i in range(len(host_ids))])
        params = {f"id{i}": host_id for i, host_id in enumerate(host_ids)}
        params["discord_id"] = TEST_BOT_DISCORD_ID
        db_session.execute(
            text(f"DELETE FROM users WHERE id IN ({placeholders}) OR discord_id = :discord_id"),
            params,
        )
    else:
        db_session.execute(
            text("DELETE FROM users WHERE discord_id = :discord_id"),
            {"discord_id": TEST_BOT_DISCORD_ID},
        )
    db_session.commit()

    yield

    # Same cleanup after test
    host_ids_result = db_session.execute(
        text("SELECT DISTINCT host_id FROM game_sessions WHERE title LIKE 'INT_TEST%'")
    )
    host_ids = [row[0] for row in host_ids_result.fetchall()]

    db_session.execute(text("DELETE FROM game_sessions WHERE title LIKE 'INT_TEST%'"))
    db_session.execute(text("DELETE FROM game_templates WHERE name LIKE 'INT_TEST%'"))
    if host_ids:
        placeholders = ",".join([f":id{i}" for i in range(len(host_ids))])
        params = {f"id{i}": host_id for i, host_id in enumerate(host_ids)}
        params["discord_id"] = TEST_BOT_DISCORD_ID
        db_session.execute(
            text(f"DELETE FROM users WHERE id IN ({placeholders}) OR discord_id = :discord_id"),
            params,
        )
    else:
        db_session.execute(
            text("DELETE FROM users WHERE discord_id = :discord_id"),
            {"discord_id": TEST_BOT_DISCORD_ID},
        )
    db_session.commit()


@pytest.fixture
def test_user(db_session, clean_test_data):
    """Create test user for API requests."""
    user_id = "test-user-signup-int"

    db_session.execute(
        text(
            "INSERT INTO users (id, discord_id, created_at, updated_at) "
            "VALUES (:id, :discord_id, :created_at, :updated_at)"
        ),
        {
            "id": user_id,
            "discord_id": TEST_BOT_DISCORD_ID,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    db_session.commit()

    return {"id": user_id, "discord_id": TEST_BOT_DISCORD_ID}


@pytest.fixture
def test_template(db_session, redis_client, test_user):
    """Create test template with signup method configuration."""
    template_id = "test-template-signup-int"
    guild_config_id = "test-guild-signup-int"
    guild_id = "123456789012345678"
    channel_config_id = "test-channel-signup-int"
    channel_id = "987654321098765432"
    bot_manager_role_id = "999888777666555444"

    # Ensure guild exists with bot_manager_role_ids
    db_session.execute(
        text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, bot_manager_role_ids, created_at, updated_at) "
            "VALUES (:id, :guild_id, :bot_manager_role_ids, :created_at, :updated_at) "
            "ON CONFLICT (guild_id) DO UPDATE SET "
            "bot_manager_role_ids = EXCLUDED.bot_manager_role_ids"
        ),
        {
            "id": guild_config_id,
            "guild_id": guild_id,
            "bot_manager_role_ids": json.dumps([bot_manager_role_id]),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )

    # Seed Redis cache with all test data in single event loop
    async def seed_cache():
        # User roles for bot manager permission
        user_roles_key = CacheKeys.user_roles(test_user["discord_id"], guild_id)
        await redis_client.set_json(user_roles_key, [bot_manager_role_id, guild_id], ttl=3600)

        # Channel metadata to bypass Discord API calls
        channel_cache_key = CacheKeys.discord_channel(channel_id)
        await redis_client.set_json(
            channel_cache_key,
            {"id": channel_id, "name": "test-channel", "type": 0, "guild_id": guild_id},
            ttl=3600,
        )

        # Guild metadata to bypass Discord API calls
        guild_cache_key = CacheKeys.discord_guild(guild_id)
        await redis_client.set_json(
            guild_cache_key,
            {"id": guild_id, "name": "Test Guild", "icon": None},
            ttl=3600,
        )

    asyncio.run(seed_cache())

    # Ensure channel exists (guild_id FK references guild_configurations.id)
    db_session.execute(
        text(
            "INSERT INTO channel_configurations (id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at) "
            "ON CONFLICT (channel_id) DO NOTHING"
        ),
        {
            "id": channel_config_id,
            "channel_id": channel_id,
            "guild_id": guild_config_id,  # FK to guild_configurations.id
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )

    # Create template with both signup methods allowed, HOST_SELECTED default
    db_session.execute(
        text(
            "INSERT INTO game_templates "
            "(id, guild_id, name, description, channel_id, "
            "allowed_signup_methods, default_signup_method, created_at, updated_at) "
            "VALUES (:id, :guild_id, :name, :description, :channel_id, "
            ":allowed_signup_methods, :default_signup_method, :created_at, :updated_at)"
        ),
        {
            "id": template_id,
            "guild_id": guild_config_id,  # FK to guild_configurations.id
            "name": "INT_TEST Template",
            "description": "Integration test template",
            "channel_id": channel_config_id,  # FK to channel_configurations.id
            "allowed_signup_methods": json.dumps(
                [SignupMethod.SELF_SIGNUP.value, SignupMethod.HOST_SELECTED.value]
            ),
            "default_signup_method": SignupMethod.HOST_SELECTED.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    db_session.commit()

    return {
        "id": template_id,
        "guild_id": guild_id,  # Discord guild ID
        "channel_id": channel_id,  # Discord channel ID
        "guild_config_id": guild_config_id,  # UUID FK
        "channel_config_id": channel_config_id,  # UUID FK
    }


@pytest.fixture
def authenticated_client(api_base_url, test_user):
    """Create authenticated HTTP client for API requests."""
    session_token = None

    def _create_client():
        nonlocal session_token
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            session_token, session_data = loop.run_until_complete(
                create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
            )
        finally:
            loop.close()

        client = httpx.Client(
            base_url=api_base_url,
            timeout=30.0,
            cookies={"session_token": session_token},
        )
        return client

    client = _create_client()
    yield client

    client.close()

    if session_token:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cleanup_test_session(session_token))
        finally:
            loop.close()


def consume_one_message(channel, queue_name, timeout=5):
    """Consume one message from queue with timeout."""
    for method, properties, body in channel.consume(
        queue_name, auto_ack=False, inactivity_timeout=timeout
    ):
        if method is None:
            return None, None, None
        channel.basic_ack(method.delivery_tag)
        channel.cancel()
        return method, properties, body
    return None, None, None


def test_api_creates_game_with_explicit_signup_method_in_rabbitmq_message(
    db_session,
    rabbitmq_channel,
    test_user,
    test_template,
    authenticated_client,
):
    """
    Verify API game creation with explicit signup method produces correct RabbitMQ message.

    Flow: HTTP POST → API (authenticated) → Database → RabbitMQ → Bot Queue
    Validates that signup_method flows through entire stack including HTTP layer.
    """
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Game with Self Signup",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.SELF_SIGNUP.value,
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.SELF_SIGNUP.value
    game_id = game_data["id"]

    # Verify database record
    result = db_session.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    ).fetchone()
    assert result is not None, "Game not found in database"
    assert result[0] == SignupMethod.SELF_SIGNUP.value

    # Verify RabbitMQ message
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None, "No message found in bot_events queue"
    assert body is not None, "Message body is None"
    message = json.loads(body)

    assert "data" in message, "Message missing 'data' field"
    assert "signup_method" in message["data"], "Message missing 'signup_method' in event data"
    assert message["data"]["signup_method"] == SignupMethod.SELF_SIGNUP.value


def test_api_uses_template_default_signup_method_when_not_specified(
    db_session,
    rabbitmq_channel,
    test_user,
    test_template,
    authenticated_client,
):
    """
    Verify API game creation without explicit signup method uses template default.

    Template has default_signup_method=HOST_SELECTED, should be used automatically.
    """
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Game with Template Default",
            "scheduled_at": scheduled_at,
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.HOST_SELECTED.value

    game_id = game_data["id"]

    # Verify database
    result = db_session.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    ).fetchone()
    assert result[0] == SignupMethod.HOST_SELECTED.value

    # Verify RabbitMQ message
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None
    assert body is not None, "Message body is None"
    message = json.loads(body)
    assert message["data"]["signup_method"] == SignupMethod.HOST_SELECTED.value


def test_api_creates_host_selected_game_with_initial_participants(
    db_session,
    rabbitmq_channel,
    test_user,
    test_template,
    authenticated_client,
):
    """
    Verify HOST_SELECTED games can be created with pre-populated participants.

    Tests integration between signup_method and initial_participants features.
    Validates that HOST_SELECTED mode works correctly with participant pre-population.
    """
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    # Create game with HOST_SELECTED and two placeholder participants
    # Using placeholders (not @mentions) to avoid Discord API calls
    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Host Selected with Participants",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED.value,
            "initial_participants": json.dumps(["Player One", "Player Two"]),
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.HOST_SELECTED.value
    assert game_data["participant_count"] == 2, "Should have 2 pre-populated participants"

    game_id = game_data["id"]

    # Verify database has participants with correct position_type
    results = db_session.execute(
        text(
            "SELECT position_type, position, display_name FROM game_participants "
            "WHERE game_session_id = :game_id ORDER BY position"
        ),
        {"game_id": game_id},
    ).fetchall()

    assert len(results) == 2, "Should have 2 participants in database"
    for result in results:
        assert result[0] == ParticipantType.HOST_ADDED, (
            "Participants should have HOST_ADDED position_type"
        )
        assert result[1] > 0, "Participants should have positive positions"
        assert result[2] in [
            "Player One",
            "Player Two",
        ], f"Unexpected participant: {result[2]}"

    # Verify RabbitMQ message has correct signup_method
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None
    assert body is not None, "Message body is None"
    message = json.loads(body)
    assert message["data"]["signup_method"] == SignupMethod.HOST_SELECTED.value
