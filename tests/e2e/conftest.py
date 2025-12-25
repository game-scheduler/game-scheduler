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
from typing import Any, TypeVar

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

T = TypeVar("T")


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
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


@pytest.fixture(scope="session")
def db_engine(database_url):
    """Create database engine for E2E tests."""
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide database session for individual tests."""
    session_factory = sessionmaker(bind=db_engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


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
