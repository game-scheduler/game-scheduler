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


"""
pytest configuration for E2E tests.

Provides fixtures for Discord credentials, database sessions,
and HTTP clients needed by E2E tests.
"""

import os
import struct
import zlib
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.conftest import TimeoutType  # Re-export for backward compatibility
from tests.e2e.helpers.discord import DiscordTestHelper
from tests.shared.auth_helpers import cleanup_test_session, create_test_session
from tests.shared.polling import wait_for_db_condition_async

# Export TimeoutType so e2e tests can import it from here
__all__ = ["TimeoutType"]

T = TypeVar("T")


@dataclass
class DiscordTestEnvironment:
    """
    Discord IDs from environment variables for E2E testing.

    These point to real Discord entities that must be set up manually
    before running E2E tests (see docs/developer/TESTING.md for setup instructions).
    """

    # Guild A (primary test guild)
    guild_a_id: str
    channel_a_id: str
    user_a_id: str

    # Guild B (for cross-guild isolation tests)
    guild_b_id: str
    channel_b_id: str
    user_b_id: str

    @classmethod
    def from_environment(cls) -> "DiscordTestEnvironment":
        """
        Load Discord IDs from environment variables with validation.

        Raises:
            ValueError: If required environment variables are missing
            ValueError: If Discord IDs have invalid format (not snowflakes)
        """
        required_vars = {
            "DISCORD_GUILD_A_ID": "Guild A ID",
            "DISCORD_GUILD_A_CHANNEL_ID": "Guild A channel ID",
            "DISCORD_USER_ID": "Guild A user ID",
            "DISCORD_GUILD_B_ID": "Guild B ID",
            "DISCORD_GUILD_B_CHANNEL_ID": "Guild B channel ID",
            "DISCORD_ADMIN_BOT_B_CLIENT_ID": "Guild B user ID",
        }

        missing_vars = [
            f"{var} ({desc})" for var, desc in required_vars.items() if not os.getenv(var)
        ]

        if missing_vars:
            error_msg = (
                "Missing required environment variables for E2E tests:\n"
                f"  {', '.join(missing_vars)}\n\n"
                "See docs/developer/TESTING.md for setup instructions."
            )
            raise ValueError(error_msg)

        def validate_snowflake(value: str, name: str) -> str:
            """Validate Discord snowflake ID format (17-19 digit number)."""
            if not value.isdigit() or len(value) < 17 or len(value) > 19:
                error_msg = (
                    f"{name} has invalid Discord ID format: {value}\n"
                    "Expected 17-19 digit snowflake ID"
                )
                raise ValueError(error_msg)
            return value

        return cls(
            guild_a_id=validate_snowflake(os.getenv("DISCORD_GUILD_A_ID"), "DISCORD_GUILD_A_ID"),
            channel_a_id=validate_snowflake(
                os.getenv("DISCORD_GUILD_A_CHANNEL_ID"), "DISCORD_GUILD_A_CHANNEL_ID"
            ),
            user_a_id=validate_snowflake(os.getenv("DISCORD_USER_ID"), "DISCORD_USER_ID"),
            guild_b_id=validate_snowflake(os.getenv("DISCORD_GUILD_B_ID"), "DISCORD_GUILD_B_ID"),
            channel_b_id=validate_snowflake(
                os.getenv("DISCORD_GUILD_B_CHANNEL_ID"), "DISCORD_GUILD_B_CHANNEL_ID"
            ),
            user_b_id=validate_snowflake(
                os.getenv("DISCORD_ADMIN_BOT_B_CLIENT_ID"),
                "DISCORD_ADMIN_BOT_B_CLIENT_ID",
            ),
        )


@pytest.fixture(scope="session")
def discord_ids() -> DiscordTestEnvironment:
    """
    Load and validate Discord IDs from environment variables.

    Session-scoped: Validates once at test session start.
    Provides fail-fast behavior with clear error messages.
    """
    return DiscordTestEnvironment.from_environment()


@dataclass
class GuildContext:
    """Context for a test guild with all related IDs."""

    db_id: str  # Database UUID
    discord_id: str  # Discord snowflake ID
    channel_db_id: str  # Database UUID for channel
    channel_discord_id: str  # Discord channel snowflake
    template_id: str  # Database UUID for default template


@pytest.fixture
async def fresh_guild_a(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
    test_user_a: User,
) -> AsyncGenerator[GuildContext]:
    """
    Create Guild A with automatic cleanup.

    Directly inserts guild, channel, and template records for E2E testing.
    Does not use /api/v1/guilds/sync because that requires OAuth tokens.

    Provides hermetic test isolation with cleanup after each test.
    Depends on test_user_a to ensure user record exists before guild creation.
    """
    guild_db_id = str(uuid4())
    channel_db_id = str(uuid4())
    template_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        # Delete any existing guild record to ensure clean state
        await admin_db.execute(
            text("DELETE FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_a_id},
        )
        await admin_db.commit()

        # Insert guild configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO guild_configurations (id, guild_id, created_at, updated_at)
                VALUES (:id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": guild_db_id,
                "guild_id": discord_ids.guild_a_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert channel configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO channel_configurations
                    (id, channel_id, guild_id, created_at, updated_at)
                VALUES
                    (:id, :channel_id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": channel_db_id,
                "channel_id": discord_ids.channel_a_id,
                "guild_id": guild_db_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert default template
        await admin_db.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, is_default, created_at, updated_at)
                VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)
                """
            ),
            {
                "id": template_id,
                "guild_id": guild_db_id,
                "channel_id": channel_db_id,
                "name": "Default Template",
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
        )

        await admin_db.commit()

        yield GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_a_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_a_id,
            template_id=template_id,
        )

    finally:
        if guild_db_id:
            await admin_db.rollback()
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()


@pytest.fixture
async def fresh_guild_b(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
    test_user_b: User,
) -> AsyncGenerator[GuildContext]:
    """
    Create Guild B with automatic cleanup.

    Directly inserts guild, channel, and template records for E2E testing.
    Does not use /api/v1/guilds/sync because that requires OAuth tokens.

    Provides hermetic test isolation with cleanup after each test.
    Depends on test_user_b to ensure user record exists before guild creation.
    """
    guild_db_id = str(uuid4())
    channel_db_id = str(uuid4())
    template_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        # Delete any existing guild record to ensure clean state
        await admin_db.execute(
            text("DELETE FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_b_id},
        )
        await admin_db.commit()

        # Insert guild configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO guild_configurations (id, guild_id, created_at, updated_at)
                VALUES (:id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": guild_db_id,
                "guild_id": discord_ids.guild_b_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert channel configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO channel_configurations
                    (id, channel_id, guild_id, created_at, updated_at)
                VALUES
                    (:id, :channel_id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": channel_db_id,
                "channel_id": discord_ids.channel_b_id,
                "guild_id": guild_db_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert default template
        await admin_db.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, is_default, created_at, updated_at)
                VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)
                """
            ),
            {
                "id": template_id,
                "guild_id": guild_db_id,
                "channel_id": channel_db_id,
                "name": "Default Template",
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
        )

        await admin_db.commit()

        yield GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_b_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_b_id,
            template_id=template_id,
        )

    finally:
        if guild_db_id:
            await admin_db.rollback()
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()


@pytest.fixture
async def test_user_a(
    admin_db: AsyncSession,
    bot_discord_id: str,
) -> AsyncGenerator[User]:
    """
    Create User A (admin bot) for tests requiring authenticated user.

    Provides hermetic user creation - only tests that need users include this fixture.
    Automatically cleans up after test.
    Uses bot_discord_id to ensure user record matches authenticated_admin_client.
    """
    user = User(discord_id=bot_discord_id)
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    assert user.discord_id is not None
    yield user

    await admin_db.delete(user)
    await admin_db.commit()


@pytest.fixture
async def test_user_b(
    admin_db: AsyncSession,
    discord_user_b_token: str,
) -> AsyncGenerator[User]:
    """
    Create User B (bot B) for tests requiring Guild B authenticated user.

    Provides hermetic user creation - only tests that need users include this fixture.
    Automatically cleans up after test.
    Uses discord_user_b_token to ensure user record matches authenticated_client_b.
    """
    user_b_discord_id = extract_bot_discord_id(discord_user_b_token)
    user = User(discord_id=user_b_discord_id)
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    assert user.discord_id is not None
    yield user

    await admin_db.delete(user)
    await admin_db.commit()


@pytest.fixture
async def test_user_main_bot(
    admin_db: AsyncSession,
    discord_main_bot_token: str,
) -> AsyncGenerator[User]:
    """
    Create main notification bot user for tests requiring notification bot.

    Provides hermetic user creation - only tests that need users include this fixture.
    Automatically cleans up after test.
    """
    main_bot_discord_id = extract_bot_discord_id(discord_main_bot_token)
    user = User(discord_id=main_bot_discord_id)
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    assert user.discord_id is not None
    yield user

    await admin_db.delete(user)
    await admin_db.commit()


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

    This is a convenience wrapper around wait_for_db_condition_async from
    tests.shared.polling that maintains backward compatibility with existing
    e2e tests.

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
    """
    return await wait_for_db_condition_async(
        db_session, query, params, predicate, timeout, interval, description
    )


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
    return os.environ["DISCORD_ADMIN_BOT_A_TOKEN"]


@pytest.fixture(scope="session")
def discord_main_bot_token():
    """Provide Discord main bot token (sends notifications)."""
    return os.environ["DISCORD_BOT_TOKEN"]


@pytest.fixture(scope="session")
def discord_guild_id(discord_ids: DiscordTestEnvironment):
    """Provide test Discord guild ID (backward compatibility)."""
    return discord_ids.guild_a_id


@pytest.fixture(scope="session")
def discord_channel_id(discord_ids: DiscordTestEnvironment):
    """Provide test Discord channel ID (backward compatibility)."""
    return discord_ids.channel_a_id


@pytest.fixture(scope="session")
def discord_user_id(discord_ids: DiscordTestEnvironment):
    """Provide test Discord user ID (backward compatibility)."""
    return discord_ids.user_a_id


@pytest.fixture(scope="session")
def discord_guild_b_id(discord_ids: DiscordTestEnvironment):
    """Guild B for cross-guild isolation testing (backward compatibility)."""
    return discord_ids.guild_b_id


@pytest.fixture(scope="session")
def discord_channel_b_id(discord_ids: DiscordTestEnvironment):
    """Channel in Guild B for isolation tests (backward compatibility)."""
    return discord_ids.channel_b_id


@pytest.fixture(scope="session")
def discord_user_b_id(discord_ids: DiscordTestEnvironment):
    """User B (member of Guild B only, backward compatibility)."""
    return discord_ids.user_b_id


@pytest.fixture(scope="session")
def discord_archive_channel_id():
    """Provide Discord archive channel ID for E2E tests."""
    return os.environ["DISCORD_ARCHIVE_CHANNEL_ID"]


@pytest.fixture(scope="session")
def discord_user_b_token():
    """Bot token for User B (Admin Bot B acting as authenticated user in Guild B)."""
    user_b_token = os.environ.get("DISCORD_ADMIN_BOT_B_TOKEN")
    if not user_b_token:
        pytest.fail(
            "DISCORD_ADMIN_BOT_B_TOKEN environment variable not set. "
            "Guild B is required for cross-guild isolation testing. "
            "See TESTING_E2E.md section 6 for setup instructions."
        )
    return user_b_token


@pytest.fixture
async def discord_helper(discord_token):
    """Create and connect Discord test helper."""

    helper = DiscordTestHelper(discord_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


@pytest.fixture(scope="session")
def bot_discord_id(discord_token):
    """Extract bot Discord ID from token."""

    return extract_bot_discord_id(discord_token)


@pytest.fixture
async def authenticated_admin_client(
    api_base_url, bot_discord_id, discord_token, test_user_a: User
):
    """
    HTTP client authenticated as admin bot.

    Depends on test_user_a to ensure user record exists before authentication.
    """

    client = httpx.AsyncClient(base_url=api_base_url, timeout=10.0)

    session_token, _ = await create_test_session(discord_token, bot_discord_id)
    client.cookies.set("session_token", session_token)

    yield client

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def guild_a_db_id(fresh_guild_a: GuildContext) -> str:
    """Provide Guild A database ID (passthrough to fresh_guild_a)."""
    return fresh_guild_a.db_id


@pytest.fixture
async def guild_b_db_id(fresh_guild_b: GuildContext) -> str:
    """Provide Guild B database ID (passthrough to fresh_guild_b)."""
    return fresh_guild_b.db_id


@pytest.fixture
async def guild_a_template_id(fresh_guild_a: GuildContext) -> str:
    """Provide Guild A default template ID (passthrough to fresh_guild_a)."""
    return fresh_guild_a.template_id


@pytest.fixture
async def guild_b_template_id(fresh_guild_b: GuildContext) -> str:
    """Provide Guild B default template ID (passthrough to fresh_guild_b)."""
    return fresh_guild_b.template_id


@pytest.fixture
async def synced_guild(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
    test_user_a: User,
) -> AsyncGenerator[GuildContext]:
    """
    Create Guild A with automatic cleanup.

    Directly inserts guild, channel, and template records for E2E testing.
    Does not use /api/v1/guilds/sync because that requires OAuth tokens,
    not bot tokens.

    Provides hermetic test isolation with cleanup after each test.
    Depends on test_user_a to ensure user record exists before guild creation.
    """
    guild_db_id = str(uuid4())
    channel_db_id = str(uuid4())
    template_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        # Delete any existing guild record to ensure clean state
        await admin_db.execute(
            text("DELETE FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_a_id},
        )
        await admin_db.commit()

        # Insert guild configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO guild_configurations (id, guild_id, created_at, updated_at)
                VALUES (:id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": guild_db_id,
                "guild_id": discord_ids.guild_a_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert channel configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO channel_configurations
                    (id, channel_id, guild_id, created_at, updated_at)
                VALUES
                    (:id, :channel_id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": channel_db_id,
                "channel_id": discord_ids.channel_a_id,
                "guild_id": guild_db_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert default template
        await admin_db.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, is_default, created_at, updated_at)
                VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)
                """
            ),
            {
                "id": template_id,
                "guild_id": guild_db_id,
                "channel_id": channel_db_id,
                "name": "Default Template",
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
        )

        await admin_db.commit()

        yield GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_a_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_a_id,
            template_id=template_id,
        )

    finally:
        if guild_db_id:
            await admin_db.rollback()
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()


@pytest.fixture
async def synced_guild_b(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
    test_user_b: User,
) -> AsyncGenerator[GuildContext]:
    """
    Create Guild B with automatic cleanup.

    Directly inserts guild, channel, and template records for E2E testing.
    Does not use /api/v1/guilds/sync because that requires OAuth tokens,
    not bot tokens.

    Provides hermetic test isolation with cleanup after each test.
    Depends on test_user_b to ensure user record exists before guild creation.
    """
    guild_db_id = str(uuid4())
    channel_db_id = str(uuid4())
    template_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        # Delete any existing guild record to ensure clean state
        await admin_db.execute(
            text("DELETE FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_b_id},
        )
        await admin_db.commit()

        # Insert guild configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO guild_configurations (id, guild_id, created_at, updated_at)
                VALUES (:id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": guild_db_id,
                "guild_id": discord_ids.guild_b_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert channel configuration
        await admin_db.execute(
            text(
                """
                INSERT INTO channel_configurations
                    (id, channel_id, guild_id, created_at, updated_at)
                VALUES
                    (:id, :channel_id, :guild_id, :created_at, :updated_at)
                """
            ),
            {
                "id": channel_db_id,
                "channel_id": discord_ids.channel_b_id,
                "guild_id": guild_db_id,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Insert default template
        await admin_db.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, is_default, created_at, updated_at)
                VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)
                """
            ),
            {
                "id": template_id,
                "guild_id": guild_db_id,
                "channel_id": channel_db_id,
                "name": "Default Template",
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
        )

        await admin_db.commit()

        yield GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_b_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_b_id,
            template_id=template_id,
        )

    finally:
        if guild_db_id:
            await admin_db.rollback()
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()


@pytest.fixture
async def authenticated_client_b(
    api_base_url, discord_user_b_id, discord_user_b_token, test_user_b: User
):
    """
    HTTP client authenticated as User B (Guild B member).

    Depends on test_user_b to ensure user record exists before authentication.
    """

    client = httpx.AsyncClient(base_url=api_base_url, timeout=10.0)

    session_token, _ = await create_test_session(discord_user_b_token, discord_user_b_id)
    client.cookies.set("session_token", session_token)

    yield client

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


@pytest.fixture(autouse=True)
async def cleanup_startup_sync_guilds(
    request: pytest.FixtureRequest,
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
) -> AsyncGenerator[None]:
    """
    Remove guilds created by bot startup sync after test_00_bot_startup_sync.

    This fixture automatically runs after the startup sync E2E test completes,
    ensuring hermetic test isolation for subsequent E2E tests. Only activates
    for the specific test that verifies bot startup behavior.
    """
    yield

    if request.node.name == "test_bot_startup_sync_creates_guilds":
        await admin_db.execute(
            text(
                """
                DELETE FROM guild_configurations
                WHERE guild_id IN (:guild_a_id, :guild_b_id)
                """
            ),
            {
                "guild_a_id": discord_ids.guild_a_id,
                "guild_b_id": discord_ids.guild_b_id,
            },
        )
        await admin_db.commit()


def _make_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    """Build a minimal valid RGB PNG of the given dimensions and solid color."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def valid_png_data() -> bytes:
    """10x10 red PNG for thumbnail upload tests."""
    return _make_png(10, 10, (255, 0, 0))


@pytest.fixture
def valid_jpeg_data() -> bytes:
    """20x20 blue PNG for banner upload tests.

    Uploaded with content-type image/jpeg; the API validates the header, not
    the bytes, so a PNG payload is fine here.  The different size (20x20 vs
    10x10 for the thumbnail) lets tests distinguish which image Discord is
    rendering.
    """
    return _make_png(20, 20, (0, 0, 255))
