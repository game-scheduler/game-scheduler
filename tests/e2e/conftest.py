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


"""
pytest configuration for E2E tests.

Provides fixtures for Discord credentials, database sessions,
and HTTP clients needed by E2E tests.
"""

import asyncio
import os
from collections.abc import Callable
from enum import StrEnum
from typing import Any, TypeVar

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

T = TypeVar("T")


class TimeoutType(StrEnum):
    """E2E test timeout operation types."""

    MESSAGE_CREATE = "message_create"
    MESSAGE_UPDATE = "message_update"
    DM_IMMEDIATE = "dm_immediate"
    DM_SCHEDULED = "dm_scheduled"
    STATUS_TRANSITION = "status_transition"
    DB_WRITE = "db_write"


@pytest.fixture(scope="session")
def e2e_timeouts() -> dict[TimeoutType, int]:
    """
    Standard timeout values for E2E test polling operations.

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


async def wait_for_db_condition(
    db_session: AsyncSession,
    query: str,
    params: dict,
    predicate: Callable[[Any], bool],
    timeout: int = 10,
    interval: float = 0.5,
    description: str = "database condition",
) -> Any:
    """
    Poll database query until predicate satisfied.

    Args:
        db_session: SQLAlchemy async session
        query: SQL query string
        params: Query parameters
        predicate: Function returning True when result matches expectation
        timeout: Maximum seconds to wait
        interval: Seconds between queries
        description: Human-readable description

    Returns:
        Query result when predicate satisfied

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        # Wait for message_id to be populated
        result = await wait_for_db_condition(
            db_session,
            "SELECT message_id FROM game_sessions WHERE id = :game_id",
            {"game_id": game_id},
            lambda row: row[0] is not None,
            description="message_id population"
        )
        message_id = result[0]
    """
    start_time = asyncio.get_event_loop().time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = asyncio.get_event_loop().time() - start_time

        result = await db_session.execute(text(query), params)
        row = result.fetchone()

        if row and predicate(row):
            print(f"[WAIT] ✓ {description} met after {elapsed:.1f}s (attempt {attempt})")
            return row

        if elapsed >= timeout:
            raise AssertionError(
                f"{description} not met within {timeout}s timeout ({attempt} attempts)"
            )

        if attempt == 1:
            print(f"[WAIT] Waiting for {description} (timeout: {timeout}s, interval: {interval}s)")
        elif attempt % 5 == 0:
            print(
                f"[WAIT] Still waiting for {description}... "
                f"({elapsed:.0f}s elapsed, attempt {attempt})"
            )

        await asyncio.sleep(interval)


async def wait_for_game_message_id(
    db_session: AsyncSession,
    game_id: str,
    timeout: int = 5,
) -> str:
    """
    Poll database until message_id is populated for a game session.

    Game announcement messages are posted asynchronously via RabbitMQ,
    so message_id may not be immediately available after game creation.

    Args:
        db_session: SQLAlchemy async session
        game_id: UUID of the game session
        timeout: Maximum seconds to wait (default: 5)

    Returns:
        Discord message_id string

    Raises:
        AssertionError: If message_id not populated within timeout

    Example:
        game_id = response.json()["id"]
        message_id = await wait_for_game_message_id(db_session, game_id)
    """
    row = await wait_for_db_condition(
        db_session,
        "SELECT message_id FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] is not None,
        timeout=timeout,
        interval=0.5,
        description=f"message_id population for game {game_id}",
    )
    return row[0]


@pytest.fixture(scope="session")
def discord_token():
    """Provide Discord admin bot token for E2E tests."""
    return os.environ["DISCORD_ADMIN_BOT_TOKEN"]


@pytest.fixture(scope="session")
def discord_main_bot_token():
    """Provide Discord main bot token (sends notifications)."""
    return os.environ["DISCORD_TOKEN"]


@pytest.fixture(scope="session")
def discord_guild_id():
    """Provide test Discord guild ID from environment."""
    return os.environ["DISCORD_GUILD_ID"]


@pytest.fixture(scope="session")
def discord_channel_id():
    """Provide test Discord channel ID from environment."""
    return os.environ["DISCORD_CHANNEL_ID"]


@pytest.fixture(scope="session")
def discord_user_id():
    """Provide test Discord user ID from environment."""
    return os.environ["DISCORD_USER_ID"]


@pytest.fixture(scope="session")
def database_url():
    """Construct database URL from environment variables."""
    return (
        f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


@pytest.fixture(scope="function")
async def db_engine(database_url):
    """Create async database engine for E2E tests."""
    engine = create_async_engine(database_url, future=True)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Provide async database session for individual tests."""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest.fixture(scope="session")
def api_base_url():
    """Provide API base URL for E2E tests."""
    return "http://api:8000"


@pytest.fixture(scope="function")
def http_client(api_base_url):
    """Provide HTTP client for API requests."""
    client = httpx.Client(base_url=api_base_url, timeout=10.0)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def discord_helper(discord_token):
    """Create and connect Discord test helper."""
    from tests.e2e.helpers.discord import DiscordTestHelper

    helper = DiscordTestHelper(discord_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


@pytest.fixture(scope="session")
def bot_discord_id(discord_token):
    """Extract bot Discord ID from token."""
    from tests.e2e.utils.tokens import extract_bot_discord_id

    return extract_bot_discord_id(discord_token)


@pytest.fixture(scope="function")
async def authenticated_admin_client(api_base_url, bot_discord_id, discord_token):
    """HTTP client authenticated as admin bot."""
    import uuid
    from datetime import UTC, datetime, timedelta

    import httpx

    from services.api.auth.tokens import encrypt_token
    from shared.cache.client import RedisClient

    client = httpx.AsyncClient(base_url=api_base_url, timeout=10.0)

    redis_client = RedisClient()
    await redis_client.connect()

    session_token = str(uuid.uuid4())
    encrypted_access = encrypt_token(discord_token)
    encrypted_refresh = encrypt_token("e2e_bot_refresh")
    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=604800)

    session_data = {
        "user_id": bot_discord_id,
        "access_token": encrypted_access,
        "refresh_token": encrypted_refresh,
        "expires_at": expiry.isoformat(),
    }

    session_key = f"session:{session_token}"
    await redis_client.set_json(session_key, session_data, ttl=604800)

    client.cookies.set("session_token", session_token)

    yield client

    await redis_client.delete(session_key)
    await redis_client.disconnect()
    await client.aclose()


@pytest.fixture(scope="function")
async def synced_guild(authenticated_admin_client, discord_guild_id):
    """
    Sync guilds using the API endpoint and return sync results.

    Calls /api/v1/guilds/sync with the admin bot token.
    Returns the sync response containing new_guilds and new_channels counts.
    """
    print("\n[synced_guild fixture] Calling /api/v1/guilds/sync")
    print(f"[synced_guild fixture] Client: {authenticated_admin_client}")
    print(f"[synced_guild fixture] Cookies: {authenticated_admin_client.cookies}")

    response = await authenticated_admin_client.post("/api/v1/guilds/sync")

    print(f"[synced_guild fixture] Response status: {response.status_code}")
    print(f"[synced_guild fixture] Response text: {response.text[:200]}")

    assert response.status_code == 200, (
        f"Guild sync failed: {response.status_code} - {response.text}"
    )

    sync_results = response.json()
    print(f"[synced_guild fixture] Sync results: {sync_results}")
    return sync_results
