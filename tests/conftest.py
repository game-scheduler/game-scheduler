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


"""
Shared test fixtures for all test suites.

This module provides consolidated fixtures for:
- Integration test fixtures: Database connections, RabbitMQ, Redis (session scope)
- Unit test fixtures: Mocks for external services (function scope)
- Factory fixtures for data creation (guild, channel, user, template, game)
- Composite fixtures for common test patterns

Fixture Organization:
- tests/conftest.py (this file) - Shared fixtures for ALL tests
  * Integration test fixtures: db sessions, redis, factories
  * Unit test mocks: mock_db_unit, mock_discord_api_client,
    mock_current_user_unit, mock_role_service
- tests/services/api/services/conftest.py - Game service cluster fixtures
  * Used by test_games.py, test_games_promotion.py, etc.
- Test files - Test-specific fixtures
  * Only when unique to one test file

Unit Test Fixture Naming Convention:
- Fixtures ending in _unit are for unit tests (no DB/infrastructure)
- Regular fixtures are for integration tests (require DB/RabbitMQ/Redis)

Examples:
    # Unit test - uses mocks, no infrastructure
    def test_something(mock_db_unit, mock_discord_api_client):
        pass

    # Integration test - uses real DB/Redis connections
    def test_something_integration(admin_db, redis_client):
        pass

Architecture:
- Factory pattern: Fixtures return functions, not data
- Sync-first: Primary implementation is sync, async is wrapper
- Hermetic: Automatic cleanup via admin_db_sync
- RLS safe: Always use admin user for fixture creation
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from services.api.auth.tokens import encrypt_token
from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.discord import client as discord_client_module
from shared.schemas import auth as auth_schemas
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

logger = logging.getLogger(__name__)

# Disable OpenTelemetry during tests to prevent background threads
# from persisting after pytest exits
os.environ["PYTEST_RUNNING"] = "1"


# ============================================================================
# Auto-use Fixtures (Apply to all tests)
# ============================================================================


@pytest.fixture(autouse=True)
def mock_oauth2_get_user_guilds() -> AsyncMock:
    """
    Auto-mock oauth2.get_user_guilds for all tests.

    This allows require_guild_by_id to work in tests without making real API calls.
    Returns guilds with common test IDs that tests use.
    """
    with patch("services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock) as mock:
        # Default: return multiple common test guild IDs so most tests pass
        mock.return_value = [
            {"id": "123456789012345678", "name": "Test Guild"},
            {"id": "guild123", "name": "Test Guild 2"},
            {"id": "guild_id_from_env", "name": "Test Guild 3"},
        ]
        yield mock


# ============================================================================
# Test Timeout Configuration (Session Scope)
# ============================================================================


class TimeoutType(StrEnum):
    """Test timeout operation types for polling operations."""

    MESSAGE_CREATE = "message_create"
    MESSAGE_UPDATE = "message_update"
    DM_IMMEDIATE = "dm_immediate"
    DM_SCHEDULED = "dm_scheduled"
    STATUS_TRANSITION = "status_transition"
    DB_WRITE = "db_write"


@pytest.fixture(scope="session")
def test_timeouts() -> dict[TimeoutType, int]:
    """
    Standard timeout values for test polling operations.

    Used by both integration and E2E tests for consistent timeout handling.

    Returns dict with TimeoutType keys and timeout values (in seconds):
    - MESSAGE_CREATE: Discord message creation (10s)
    - MESSAGE_UPDATE: Discord message edit/refresh (10s)
    - DM_IMMEDIATE: DMs sent immediately by API events (10s)
    - DM_SCHEDULED: DMs sent by notification daemon polling (150s)
    - STATUS_TRANSITION: Status transitions via daemon polling (150s)
    - DB_WRITE: Database write operations (5s)

    These values balance reliability (generous timeouts for daemon operations)
    with test speed (short timeouts for immediate operations).

    Can be overridden in CI environments by adjusting values here.
    """
    return {
        TimeoutType.MESSAGE_CREATE: 10,
        TimeoutType.MESSAGE_UPDATE: 10,
        TimeoutType.DM_IMMEDIATE: 10,
        TimeoutType.DM_SCHEDULED: 150,
        TimeoutType.STATUS_TRANSITION: 150,
        TimeoutType.DB_WRITE: 5,
    }


# ============================================================================
# Database URL Fixtures (Session Scope)
# ============================================================================


@pytest.fixture(scope="session")
def admin_db_url_sync():
    """Synchronous admin database URL (psycopg2)."""
    raw_url = os.getenv("ADMIN_DATABASE_URL")
    if not raw_url:
        msg = "ADMIN_DATABASE_URL environment variable not set"
        raise ValueError(msg)
    # Ensure it's a sync URL by removing any async drivers
    return raw_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def admin_db_url():
    """Async admin database URL (asyncpg)."""
    raw_url = os.getenv("ADMIN_DATABASE_URL")
    if not raw_url:
        msg = "ADMIN_DATABASE_URL environment variable not set"
        raise ValueError(msg)
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def app_db_url():
    """Async app user database URL (asyncpg, RLS enforced)."""
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        msg = "DATABASE_URL environment variable not set"
        raise ValueError(msg)
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def bot_db_url():
    """Async bot user database URL (asyncpg, BYPASSRLS)."""
    raw_url = os.getenv("BOT_DATABASE_URL")
    if not raw_url:
        msg = "BOT_DATABASE_URL environment variable not set"
        raise ValueError(msg)
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


# ============================================================================
# Database Session Fixtures (Function Scope)
# ============================================================================


@pytest.fixture
def admin_db_sync(admin_db_url_sync):
    """
    Synchronous admin session with cleanup at START (not end).

    Use for: Daemon tests, raw SQL operations, fixture creation
    Cleanup: DELETE all test data BEFORE test starts (from previous runs)

    This pattern leaves data in database after test failure for debugging.
    """
    print("[FIXTURE] admin_db_sync: Creating cleanup session")
    cleanup_engine = create_engine(admin_db_url_sync)
    cleanup_session = sessionmaker(bind=cleanup_engine)()

    try:
        # Clean up any leftover data from previous test runs
        print("[FIXTURE] admin_db_sync: Cleaning up previous test data")
        cleanup_session.execute(text("DELETE FROM game_sessions"))
        print("[FIXTURE] admin_db_sync: Deleted game_sessions")
        cleanup_session.execute(text("DELETE FROM game_images"))
        print("[FIXTURE] admin_db_sync: Deleted game_images")
        cleanup_session.execute(text("DELETE FROM game_templates"))
        print("[FIXTURE] admin_db_sync: Deleted game_templates")
        cleanup_session.execute(text("DELETE FROM channel_configurations"))
        print("[FIXTURE] admin_db_sync: Deleted channel_configurations")
        cleanup_session.execute(text("DELETE FROM users"))
        print("[FIXTURE] admin_db_sync: Deleted users")
        cleanup_session.execute(text("DELETE FROM guild_configurations"))
        print("[FIXTURE] admin_db_sync: Deleted guild_configurations")
        cleanup_session.commit()
        print("[FIXTURE] admin_db_sync: Cleanup committed")

        # Show database state after cleanup
        result = cleanup_session.execute(text("SELECT COUNT(*) FROM guild_configurations"))
        guild_count = result.scalar()
        result = cleanup_session.execute(text("SELECT COUNT(*) FROM game_templates"))
        template_count = result.scalar()
        result = cleanup_session.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        print(
            f"[FIXTURE] admin_db_sync: Database state - guilds: {guild_count}, "
            f"templates: {template_count}, users: {user_count}"
        )
    finally:
        cleanup_session.close()
        cleanup_engine.dispose()

    # Now create the session for the test to use
    print("[FIXTURE] admin_db_sync: Creating test session")
    engine = create_engine(admin_db_url_sync)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    print("[FIXTURE] admin_db_sync: Yielding session to test")
    yield session

    print("[FIXTURE] admin_db_sync: Test complete, closing session (data remains for debugging)")
    session.close()
    engine.dispose()
    print("[FIXTURE] admin_db_sync: Teardown complete")


@pytest.fixture
async def admin_db(admin_db_url):
    """Async admin session (no automatic cleanup - test controls commit/rollback)."""
    engine = create_async_engine(admin_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def app_db(app_db_url):
    """Async app user session (RLS enforced)."""
    engine = create_async_engine(app_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def bot_db(bot_db_url):
    """Async bot user session (BYPASSRLS)."""
    engine = create_async_engine(bot_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# ============================================================================
# Redis Client Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def api_base_url():
    """Get API base URL from environment."""
    return os.getenv("BACKEND_URL", "http://api:8000")


@pytest.fixture
def create_authenticated_client(api_base_url):
    """
    Factory to create authenticated HTTP clients.

    Creates sync httpx.Client instances with session authentication.
    Automatically manages session creation and cleanup.

    Usage:
        client = create_authenticated_client(discord_token, discord_id)
        response = client.get("/api/v1/...")
        # Cleanup happens automatically

    Args:
        discord_token: Discord bot/user token to authenticate with
        discord_id: Discord ID to associate with the session

    Returns:
        Configured httpx.Client with session cookie set
    """
    clients_to_cleanup = []

    def _create(discord_token: str, discord_id: str) -> httpx.Client:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            session_token, session_data = loop.run_until_complete(
                create_test_session(discord_token, discord_id)
            )
        finally:
            loop.close()

        client = httpx.Client(
            base_url=api_base_url,
            timeout=30.0,
            cookies={"session_token": session_token},
        )
        clients_to_cleanup.append((client, session_token))
        return client

    yield _create

    # Cleanup all created clients
    for client, session_token in clients_to_cleanup:
        client.close()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cleanup_test_session(session_token))
        finally:
            loop.close()


@pytest.fixture
def redis_client():
    """
    Sync Redis client for cache operations.

    Primary implementation - most tests are sync and need Redis seeding.
    Manages its own event loop to avoid conflicts with pytest-asyncio.

    Used for:
    - Seeding user permissions (bot_manager_role_ids)
    - Caching Discord guild/channel/user metadata
    - Storing session tokens for authentication
    - Bypassing Discord API calls in tests

    Automatically connects and disconnects.

    Note: This is the sync version. For async tests, use redis_client_async.
    """
    client = RedisClient()

    # Create a new event loop for this fixture to avoid conflicts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Connect using the new loop
        loop.run_until_complete(client.connect())

        yield client

        # Disconnect using the loop
        loop.run_until_complete(client.disconnect())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture
async def redis_client_async():
    """
    Async Redis client for async integration tests.

    For tests that are already async and can await operations.
    Most tests should use redis_client (sync version) instead.
    """
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


# ============================================================================
# Redis Cache Seeding Fixture
# ============================================================================


@pytest.fixture
def seed_redis_cache():
    """
    Factory fixture to seed Redis cache with Discord metadata.

    Returns async function that seeds multiple cache keys at once.
    Designed to bypass Discord API calls in tests.

    Creates its own Redis connection to avoid event loop conflicts.

    Cache Keys Seeded:
    1. CacheKeys.user_guilds(user_discord_id) - RLS context
    2. CacheKeys.user_roles(user_discord_id, guild_id) - Permissions
    3. CacheKeys.discord_channel(channel_id) - Channel metadata
    4. CacheKeys.discord_guild(guild_id) - Guild metadata
    5. CacheKeys.session(session_token) - Authentication (optional)

    Usage (sync tests with asyncio.run):
        asyncio.run(seed_redis_cache(
            user_discord_id="123",
            guild_discord_id="456",
            channel_discord_id="789",
            bot_manager_roles=["999888777666555444"]
        ))

    Usage (async tests with await):
        await seed_redis_cache(
            user_discord_id=user["discord_id"],
            guild_discord_id=guild["guild_id"],
            channel_discord_id=channel["channel_id"]
        )
    """

    async def _seed(
        user_discord_id: str,
        guild_discord_id: str,
        channel_discord_id: str | None = None,
        user_roles: list[str] | None = None,
        bot_manager_roles: list[str] | None = None,
        session_token: str | None = None,
        session_user_id: str | None = None,
        session_access_token: str | None = None,
    ):
        """
        Seed Redis cache with Discord metadata to bypass API calls.

        Args:
            user_discord_id: Discord user ID (18-digit string)
            guild_discord_id: Discord guild ID (18-digit string)
            channel_discord_id: Discord channel ID (optional)
            user_roles: User's role IDs (defaults to [guild_discord_id] for membership)
            bot_manager_roles: Bot manager role IDs (appended to user_roles)
            session_token: Session token for auth (optional)
            session_user_id: User database UUID for session (optional)
            session_access_token: Discord access token for session (optional)
        """
        # Create fresh Redis connection in current event loop
        redis_client = RedisClient()
        await redis_client.connect()

        try:
            # User guilds (RLS context) - Required for guild isolation
            user_guilds_key = CacheKeys.user_guilds(user_discord_id)
            guilds_data = [
                {
                    "id": guild_discord_id,
                    "name": f"Test Guild {guild_discord_id[:8]}",
                    "permissions": "2147483647",  # Administrator permissions
                }
            ]
            await redis_client.set_json(user_guilds_key, guilds_data, ttl=300)

            # User roles (permissions) - Default to guild membership
            if user_roles is None:
                # Discord convention: guild membership = guild_id role
                user_roles = [guild_discord_id]
            if bot_manager_roles:
                user_roles = user_roles + bot_manager_roles

            user_roles_key = CacheKeys.user_roles(user_discord_id, guild_discord_id)
            await redis_client.set_json(user_roles_key, user_roles, ttl=3600)

            # Channel metadata (if channel interactions needed)
            if channel_discord_id:
                channel_key = CacheKeys.discord_channel(channel_discord_id)
                await redis_client.set_json(
                    channel_key,
                    {
                        "id": channel_discord_id,
                        "name": "test-channel",
                        "type": 0,  # GUILD_TEXT
                        "guild_id": guild_discord_id,
                    },
                    ttl=3600,
                )

            # Guild metadata (always seed for guild name/icon)
            guild_key = CacheKeys.discord_guild(guild_discord_id)
            await redis_client.set_json(
                guild_key,
                {
                    "id": guild_discord_id,
                    "name": "Test Guild",
                    "icon": None,
                },
                ttl=3600,
            )

            # Session (if authentication needed)
            if session_token and session_user_id and session_access_token:
                session_key = CacheKeys.session(session_token)
                session_data = {
                    "user_id": session_user_id,
                    "access_token": encrypt_token(session_access_token),
                    "refresh_token": encrypt_token("mock_refresh_token"),
                    "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                }
                await redis_client.set_json(session_key, session_data, ttl=3600)
        finally:
            await redis_client.disconnect()

    def _sync_wrapper(*args, **kwargs):
        """Wrapper that runs seed in the redis_client's event loop for sync tests."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In async context, return the coroutine
            return _seed(*args, **kwargs)
        # In sync context, run in the fixture's loop
        return loop.run_until_complete(_seed(*args, **kwargs))

    return _sync_wrapper


# ============================================================================
# Factory Fixtures for Data Creation (Synchronous - Primary Implementation)
# ============================================================================


@pytest.fixture
def create_guild(admin_db_sync):
    """
    Factory to create guild configurations.

    Returns function that creates guild and returns dict:
    - id: str (database UUID)
    - guild_id: str (Discord guild ID, 18 digits)
    - bot_manager_role_ids: list[str]

    Example:
        guild = create_guild(
            discord_guild_id="123456789012345678",
            bot_manager_roles=["999888777666555444"]
        )
        template = create_template(guild_id=guild["id"], ...)
    """

    def _create(
        discord_guild_id: str | None = None, bot_manager_roles: list[str] | None = None
    ) -> dict:
        guild_db_id = str(uuid.uuid4())
        guild_discord_id = discord_guild_id or str(uuid.uuid4())[:18]

        print(
            f"[FACTORY] create_guild: Creating guild db_id={guild_db_id} "
            f"discord_id={guild_discord_id}"
        )
        admin_db_sync.execute(
            text(
                "INSERT INTO guild_configurations "
                "(id, guild_id, bot_manager_role_ids, created_at, updated_at) "
                "VALUES (:id, :guild_id, :bot_manager_role_ids, :created_at, :updated_at)"
            ),
            {
                "id": guild_db_id,
                "guild_id": guild_discord_id,
                "bot_manager_role_ids": json.dumps(bot_manager_roles or []),
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        print("[FACTORY] create_guild: INSERT executed, calling commit()")
        admin_db_sync.commit()
        print(f"[FACTORY] create_guild: Committed guild {guild_db_id}")

        return {
            "id": guild_db_id,
            "guild_id": guild_discord_id,
            "bot_manager_role_ids": bot_manager_roles or [],
        }

    return _create


@pytest.fixture
def create_channel(admin_db_sync):
    """Factory to create channel configurations."""

    def _create(
        guild_id: str,
        discord_channel_id: str | None = None,  # Database UUID
    ) -> dict:
        channel_db_id = str(uuid.uuid4())
        channel_discord_id = discord_channel_id or str(uuid.uuid4())[:18]

        print(
            f"[FACTORY] create_channel: Creating channel db_id={channel_db_id} "
            f"discord_id={channel_discord_id}"
        )
        admin_db_sync.execute(
            text(
                "INSERT INTO channel_configurations "
                "(id, channel_id, guild_id, created_at, updated_at) "
                "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
            ),
            {
                "id": channel_db_id,
                "channel_id": channel_discord_id,
                "guild_id": guild_id,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        print("[FACTORY] create_channel: INSERT executed, calling commit()")
        admin_db_sync.commit()
        print(f"[FACTORY] create_channel: Committed channel {channel_db_id}")

        return {
            "id": channel_db_id,
            "channel_id": channel_discord_id,
            "guild_id": guild_id,
        }

    return _create


@pytest.fixture
def create_user(admin_db_sync):
    """Factory to create users."""

    def _create(discord_user_id: str | None = None) -> dict:
        user_db_id = str(uuid.uuid4())
        user_discord_id = discord_user_id or str(uuid.uuid4())[:18]

        print(
            f"[FACTORY] create_user: Creating user db_id={user_db_id} discord_id={user_discord_id}"
        )
        admin_db_sync.execute(
            text(
                "INSERT INTO users (id, discord_id, created_at, updated_at) "
                "VALUES (:id, :discord_id, :created_at, :updated_at)"
            ),
            {
                "id": user_db_id,
                "discord_id": user_discord_id,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        print("[FACTORY] create_user: INSERT executed, calling commit()")
        admin_db_sync.commit()
        print(f"[FACTORY] create_user: Committed user {user_db_id}")

        return {"id": user_db_id, "discord_id": user_discord_id}

    return _create


@pytest.fixture
def create_template(admin_db_sync):
    """Factory to create game templates."""

    def _create(
        guild_id: str,
        channel_id: str,
        name: str = "Test Template",
        description: str | None = None,
        max_players: int = 4,
        allowed_signup_methods: list[str] | None = None,
        default_signup_method: str = "SELF_SIGNUP",
        reminder_minutes: list[int] | None = None,
        expected_duration_minutes: int | None = None,
        where: str | None = None,
        signup_instructions: str | None = None,
        **kwargs,
    ) -> dict:
        template_db_id = str(uuid.uuid4())

        admin_db_sync.execute(
            text(
                "INSERT INTO game_templates "
                "(id, guild_id, channel_id, name, description, max_players, "
                "allowed_signup_methods, default_signup_method, reminder_minutes, "
                'expected_duration_minutes, "where", signup_instructions, created_at, updated_at) '
                "VALUES (:id, :guild_id, :channel_id, :name, :description, "
                ":max_players, :allowed_signup_methods, :default_signup_method, "
                ":reminder_minutes, :expected_duration_minutes, :where, "
                ":signup_instructions, :created_at, :updated_at)"
            ),
            {
                "id": template_db_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "name": name,
                "description": description or f"Test template: {name}",
                "max_players": max_players,
                "allowed_signup_methods": json.dumps(allowed_signup_methods or ["SELF_SIGNUP"]),
                "default_signup_method": default_signup_method,
                "reminder_minutes": (json.dumps(reminder_minutes) if reminder_minutes else None),
                "expected_duration_minutes": expected_duration_minutes,
                "where": where,
                "signup_instructions": signup_instructions,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        print(f"[FACTORY] create_template: INSERT executed for {template_db_id}, calling commit()")
        admin_db_sync.commit()
        print(f"[FACTORY] create_template: Committed template {template_db_id}")

        return {
            "id": template_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "name": name,
            "max_players": max_players,
        }

    return _create


@pytest.fixture
def create_game(admin_db_sync):
    """Factory to create game sessions."""

    def _create(
        guild_id: str,
        channel_id: str,
        host_id: str,
        template_id: str | None = None,
        title: str = "Test Game",
        description: str | None = None,
        scheduled_at: datetime | None = None,
        max_players: int = 4,
        status: str = "scheduled",
        **kwargs,
    ) -> dict:
        game_db_id = str(uuid.uuid4())

        admin_db_sync.execute(
            text(
                "INSERT INTO game_sessions "
                "(id, guild_id, channel_id, host_id, template_id, title, description, "
                "scheduled_at, max_players, status, created_at, updated_at) "
                "VALUES (:id, :guild_id, :channel_id, :host_id, :template_id, :title, "
                ":description, :scheduled_at, :max_players, :status, :created_at, :updated_at)"
            ),
            {
                "id": game_db_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "host_id": host_id,
                "template_id": template_id,
                "title": title,
                "description": description or f"Test game: {title}",
                "scheduled_at": scheduled_at or datetime.now(UTC) + timedelta(hours=2),
                "max_players": max_players,
                "status": status,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        admin_db_sync.commit()

        return {
            "id": game_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": host_id,
            "title": title,
            "status": status,
        }

    return _create


# ============================================================================
# Composite Fixtures for Common Patterns
# ============================================================================


@pytest.fixture
def test_environment(create_guild, create_channel, create_user):
    """
    Create complete test environment (guild + channel + user).

    Returns dict with all three objects for convenience.

    Example:
        env = test_environment()
        game = create_game(
            guild_id=env["guild"]["id"],
            channel_id=env["channel"]["id"],
            host_id=env["user"]["id"]
        )
    """

    def _create(
        discord_guild_id: str | None = None,
        discord_channel_id: str | None = None,
        discord_user_id: str | None = None,
        bot_manager_roles: list[str] | None = None,
    ) -> dict:
        guild = create_guild(discord_guild_id=discord_guild_id, bot_manager_roles=bot_manager_roles)
        channel = create_channel(guild_id=guild["id"], discord_channel_id=discord_channel_id)
        user = create_user(discord_user_id=discord_user_id)

        return {"guild": guild, "channel": channel, "user": user}

    return _create


@pytest.fixture
def test_game_environment(test_environment, create_template, create_game):
    """
    Create complete test environment with game (guild + channel + user + game).

    Returns dict with all objects for daemon/integration tests that need a game.

    Example:
        env = test_game_environment()
        notification_id = insert_notification(game_id=env["game"]["id"])

    Customization:
        env = test_game_environment(title="Custom Game", max_players=6)
        env = test_game_environment(with_template=True)  # Include template
        env = test_game_environment(with_template=True, with_game=False)  # Template only, no game
    """

    def _create(
        discord_guild_id: str | None = None,
        discord_channel_id: str | None = None,
        discord_user_id: str | None = None,
        bot_manager_roles: list[str] | None = None,
        with_template: bool = False,
        with_game: bool = True,
        **game_kwargs,
    ) -> dict:
        env = test_environment(
            discord_guild_id=discord_guild_id,
            discord_channel_id=discord_channel_id,
            discord_user_id=discord_user_id,
            bot_manager_roles=bot_manager_roles,
        )

        template = None
        if with_template:
            template = create_template(
                guild_id=env["guild"]["id"],
                channel_id=env["channel"]["id"],
            )
            game_kwargs.setdefault("template_id", template["id"])

        game = None
        if with_game:
            game = create_game(
                guild_id=env["guild"]["id"],
                channel_id=env["channel"]["id"],
                host_id=env["user"]["id"],
                **game_kwargs,
            )

        result = {
            "guild": env["guild"],
            "channel": env["channel"],
            "user": env["user"],
        }

        if game:
            result["game"] = game

        if template:
            result["template"] = template

        return result

    return _create


# ============================================================================
# Unit Test Mock Fixtures
# ============================================================================
#
# These fixtures provide mocks for external services to enable fast,
# isolated unit tests without requiring database, Redis, or RabbitMQ.
#
# Naming Convention: Fixtures ending in _unit are for unit tests only
# - mock_db_unit: Mock database session (unit tests)
# - admin_db_sync: Real database session (integration tests)
#
# When to use:
# - Unit tests: Test single functions/classes in isolation
# - Integration tests: Test service interactions with infrastructure


@pytest.fixture
def mock_db_unit():
    """
    Mock AsyncSession database for unit tests.

    Differs from admin_db_sync/admin_db which are real database connections
    for integration tests. This is a pure mock for isolated unit tests.

    Use when testing business logic without database interactions.

    Returns AsyncMock with AsyncSession spec.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_discord_api_client():
    """
    Mock Discord REST API client (shared.discord.client.DiscordAPIClient).

    Use for testing services that make Discord API calls without hitting
    the real Discord API. For bot commands/events using discord.py Bot,
    you'll need a different mock.

    Returns MagicMock configured with DiscordAPIClient spec.
    """
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def mock_current_user_unit():
    """
    Mock authenticated user for unit tests.

    Use for testing authenticated API endpoints without running through
    the full OAuth2 authentication flow.

    Returns CurrentUser schema with mock user object containing:
    - discord_id: "123456789"
    - access_token: "test_access_token"
    Override properties in individual tests as needed:
        current_user.user.discord_id = "custom_id"
    """
    mock_user = MagicMock()
    mock_user.discord_id = "123456789"
    return auth_schemas.CurrentUser(
        user=mock_user,
        access_token="test_access_token",
        session_token="test-session-token",
    )


@pytest.fixture
def mock_role_service():
    """
    Mock role checking service for permission tests.

    Default behavior: All permission checks return True.
    Override in specific tests to test authorization logic.

    Available methods:
    - check_game_host_permission(token, guild_id, channel_id) -> bool
    - check_bot_manager_permission(token, guild_id) -> bool
    - has_any_role(token, guild_id, role_ids) -> bool
    - has_permissions(token, guild_id, permissions) -> bool

    Example override:
        mock_role_service.check_game_host_permission.return_value = False
        # Test unauthorized access handling
    """
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    role_service.has_any_role = AsyncMock(return_value=True)
    role_service.has_permissions = AsyncMock(return_value=True)
    return role_service
