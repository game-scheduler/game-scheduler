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

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_a_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_a_id,
            template_id=template_id,
        )

        yield guild_context

    finally:
        if guild_db_id:
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

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_b_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_b_id,
            template_id=template_id,
        )

        yield guild_context

    finally:
        if guild_db_id:
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

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_a_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_a_id,
            template_id=template_id,
        )

        yield guild_context

    finally:
        if guild_db_id:
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

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_b_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_b_id,
            template_id=template_id,
        )

        yield guild_context

    finally:
        if guild_db_id:
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


@pytest.fixture
def valid_png_data() -> bytes:
    """
    Return minimal valid PNG data for testing image uploads.

    Creates a 1x1 pixel transparent PNG image.
    """
    return bytes([
        0x89,
        0x50,
        0x4E,
        0x47,
        0x0D,
        0x0A,
        0x1A,
        0x0A,
        0x00,
        0x00,
        0x00,
        0x0D,
        0x49,
        0x48,
        0x44,
        0x52,
        0x00,
        0x00,
        0x00,
        0x01,
        0x00,
        0x00,
        0x00,
        0x01,
        0x08,
        0x06,
        0x00,
        0x00,
        0x00,
        0x1F,
        0x15,
        0xC4,
        0x89,
        0x00,
        0x00,
        0x00,
        0x0A,
        0x49,
        0x44,
        0x41,
        0x54,
        0x78,
        0x9C,
        0x63,
        0x00,
        0x01,
        0x00,
        0x00,
        0x05,
        0x00,
        0x01,
        0x0D,
        0x0A,
        0x2D,
        0xB4,
        0x00,
        0x00,
        0x00,
        0x00,
        0x49,
        0x45,
        0x4E,
        0x44,
        0xAE,
        0x42,
        0x60,
        0x82,
    ])


@pytest.fixture
def valid_jpeg_data() -> bytes:
    """
    Return minimal valid JPEG data for testing image uploads.

    Creates a properly-formatted 1x1 pixel JPEG image that Discord can render.
    Includes all required JPEG markers: SOI, APP0, SOF0, DQT, DHT, SOS, EOI.
    """
    return bytes([
        0xFF,
        0xD8,
        0xFF,
        0xE0,
        0x00,
        0x10,
        0x4A,
        0x46,
        0x49,
        0x46,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
        0x01,
        0x00,
        0x01,
        0x00,
        0x00,
        0xFF,
        0xC0,
        0x00,
        0x11,
        0x08,
        0x00,
        0x01,
        0x00,
        0x01,
        0x03,
        0x01,
        0x11,
        0x00,
        0x02,
        0x11,
        0x01,
        0x03,
        0x11,
        0x01,
        0xFF,
        0xDB,
        0x00,
        0x43,
        0x00,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0xFF,
        0xDB,
        0x00,
        0x43,
        0x01,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0x10,
        0xFF,
        0xC4,
        0x00,
        0x1F,
        0x00,
        0x00,
        0x01,
        0x05,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0xFF,
        0xC4,
        0x00,
        0xB5,
        0x10,
        0x00,
        0x02,
        0x01,
        0x03,
        0x03,
        0x02,
        0x04,
        0x03,
        0x05,
        0x05,
        0x04,
        0x04,
        0x00,
        0x00,
        0x01,
        0x7D,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x18,
        0x19,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
        0x20,
        0x21,
        0x22,
        0x23,
        0x24,
        0x25,
        0x26,
        0x27,
        0x28,
        0x29,
        0x2A,
        0x2B,
        0x2C,
        0x2D,
        0x2E,
        0x2F,
        0x30,
        0x31,
        0x32,
        0x33,
        0x34,
        0x35,
        0x36,
        0x37,
        0x38,
        0x39,
        0x3A,
        0x3B,
        0x3C,
        0x3D,
        0x3E,
        0x3F,
        0x40,
        0x41,
        0x42,
        0x43,
        0x44,
        0x45,
        0x46,
        0x47,
        0x48,
        0x49,
        0x4A,
        0x4B,
        0x4C,
        0x4D,
        0x4E,
        0x4F,
        0x50,
        0x51,
        0x52,
        0x53,
        0x54,
        0x55,
        0x56,
        0x57,
        0x58,
        0x59,
        0x5A,
        0x5B,
        0x5C,
        0x5D,
        0x5E,
        0x5F,
        0x60,
        0x61,
        0x62,
        0x63,
        0x64,
        0x65,
        0x66,
        0x67,
        0x68,
        0x69,
        0x6A,
        0x6B,
        0x6C,
        0x6D,
        0x6E,
        0x6F,
        0x70,
        0x71,
        0x72,
        0x73,
        0x74,
        0x75,
        0x76,
        0x77,
        0x78,
        0x79,
        0x7A,
        0x7B,
        0x7C,
        0x7D,
        0x7E,
        0x7F,
        0x80,
        0x81,
        0x82,
        0x83,
        0x84,
        0x85,
        0x86,
        0x87,
        0x88,
        0x89,
        0x8A,
        0x8B,
        0x8C,
        0x8D,
        0x8E,
        0x8F,
        0x90,
        0x91,
        0x92,
        0x93,
        0x94,
        0x95,
        0x96,
        0x97,
        0x98,
        0x99,
        0x9A,
        0x9B,
        0x9C,
        0x9D,
        0x9E,
        0x9F,
        0xA0,
        0xA1,
        0xA2,
        0xFF,
        0xC4,
        0x00,
        0x1F,
        0x01,
        0x00,
        0x03,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0xFF,
        0xC4,
        0x00,
        0xB5,
        0x11,
        0x00,
        0x02,
        0x01,
        0x02,
        0x04,
        0x04,
        0x03,
        0x04,
        0x07,
        0x05,
        0x04,
        0x04,
        0x00,
        0x01,
        0x02,
        0x77,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x18,
        0x19,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
        0x20,
        0x21,
        0x22,
        0x23,
        0x24,
        0x25,
        0x26,
        0x27,
        0x28,
        0x29,
        0x2A,
        0x2B,
        0x2C,
        0x2D,
        0x2E,
        0x2F,
        0x30,
        0x31,
        0x32,
        0x33,
        0x34,
        0x35,
        0x36,
        0x37,
        0x38,
        0x39,
        0x3A,
        0x3B,
        0x3C,
        0x3D,
        0x3E,
        0x3F,
        0x40,
        0x41,
        0x42,
        0x43,
        0x44,
        0x45,
        0x46,
        0x47,
        0x48,
        0x49,
        0x4A,
        0x4B,
        0x4C,
        0x4D,
        0x4E,
        0x4F,
        0x50,
        0x51,
        0x52,
        0x53,
        0x54,
        0x55,
        0x56,
        0x57,
        0x58,
        0x59,
        0x5A,
        0x5B,
        0x5C,
        0x5D,
        0x5E,
        0x5F,
        0x60,
        0x61,
        0x62,
        0x63,
        0x64,
        0x65,
        0x66,
        0x67,
        0x68,
        0x69,
        0x6A,
        0x6B,
        0x6C,
        0x6D,
        0x6E,
        0x6F,
        0x70,
        0x71,
        0x72,
        0x73,
        0x74,
        0x75,
        0x76,
        0x77,
        0x78,
        0x79,
        0x7A,
        0x7B,
        0x7C,
        0x7D,
        0x7E,
        0x7F,
        0x80,
        0x81,
        0x82,
        0x83,
        0x84,
        0x85,
        0x86,
        0x87,
        0x88,
        0x89,
        0x8A,
        0x8B,
        0x8C,
        0x8D,
        0x8E,
        0x8F,
        0x90,
        0x91,
        0x92,
        0x93,
        0x94,
        0x95,
        0x96,
        0x97,
        0x98,
        0x99,
        0x9A,
        0x9B,
        0x9C,
        0x9D,
        0x9E,
        0x9F,
        0xA0,
        0xA1,
        0xA2,
        0xFF,
        0xDA,
        0x00,
        0x0C,
        0x03,
        0x01,
        0x00,
        0x02,
        0x11,
        0x03,
        0x11,
        0x00,
        0x3F,
        0x00,
        0xF0,
        0x00,
        0xFF,
        0xD9,
    ])
