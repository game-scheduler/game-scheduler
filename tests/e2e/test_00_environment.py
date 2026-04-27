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
E2E environment validation test.

This test runs FIRST (test_00_*) to verify the E2E environment is properly configured.
If this fails, all other E2E tests will fail with clearer error messages.
"""

import os

import discord
import pytest
from sqlalchemy import select, text

from shared.models.user import User
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.e2e.conftest import GuildContext

pytestmark = pytest.mark.e2e

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_environment_variables():
    """Verify all required E2E environment variables are set."""
    required_vars = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_GUILD_A_ID",
        "DISCORD_GUILD_A_CHANNEL_ID",
        "DISCORD_ARCHIVE_CHANNEL_ID",
        "DISCORD_USER_ID",
        "DATABASE_URL",
        "BACKEND_URL",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    assert not missing, (
        f"Missing required environment variables: {', '.join(missing)}\n"
        f"Check env/env.e2e and TESTING_E2E.md for setup instructions"
    )


@pytest.mark.asyncio
async def test_discord_bot_can_connect(discord_token):
    """Verify Discord bot token is valid and can connect."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)
        assert client.user is not None, "Bot user should exist after login"
    except discord.LoginFailure:
        pytest.fail("Discord bot login failed. Check TEST_DISCORD_TOKEN in env/env.e2e")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_guild_exists(discord_token, discord_guild_id):
    """Verify test guild exists and bot has access."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)
        guild = client.get_guild(int(discord_guild_id))

        if guild is None:
            guild = await client.fetch_guild(int(discord_guild_id))

        assert guild is not None, (
            f"Guild {discord_guild_id} not found or bot not a member. "
            f"Check TEST_DISCORD_GUILD_ID and verify bot is invited to the guild"
        )
    except discord.Forbidden:
        pytest.fail(f"Bot does not have access to guild {discord_guild_id}")
    except discord.NotFound:
        pytest.fail(f"Guild {discord_guild_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_channel_exists(discord_token, discord_guild_id, discord_channel_id):
    """Verify test channel exists and bot has access."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)

        try:
            channel = await client.fetch_channel(int(discord_channel_id))
            assert isinstance(channel, discord.TextChannel), (
                f"Channel {discord_channel_id} is not a text channel"
            )
            assert str(channel.guild.id) == discord_guild_id, (
                f"Channel {discord_channel_id} is not in guild {discord_guild_id}"
            )
        except discord.Forbidden:
            pytest.fail(f"Bot does not have access to channel {discord_channel_id}")
        except discord.NotFound:
            pytest.fail(f"Channel {discord_channel_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_archive_channel_exists(
    discord_token, discord_guild_id, discord_archive_channel_id
):
    """Verify archive test channel exists and bot has access."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)

        try:
            channel = await client.fetch_channel(int(discord_archive_channel_id))
            assert isinstance(channel, discord.TextChannel), (
                f"Archive channel {discord_archive_channel_id} is not a text channel"
            )
            assert str(channel.guild.id) == discord_guild_id, (
                f"Archive channel {discord_archive_channel_id} is not in guild {discord_guild_id}"
            )
        except discord.Forbidden:
            pytest.fail(f"Bot does not have access to archive channel {discord_archive_channel_id}")
        except discord.NotFound:
            pytest.fail(f"Archive channel {discord_archive_channel_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_user_exists(discord_token, discord_user_id):
    """Verify test user exists."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)

        try:
            user = await client.fetch_user(int(discord_user_id))
            assert user is not None, f"User {discord_user_id} not found"
        except discord.NotFound:
            pytest.fail(f"User {discord_user_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_helper_fixture(discord_helper, discord_channel_id):
    """Verify discord_helper fixture connects successfully and can fetch channel."""
    assert discord_helper._connected, "Discord helper should be connected"
    assert discord_helper.client.user is not None, "Bot user should exist after connection"

    channel = await discord_helper.client.fetch_channel(int(discord_channel_id))
    assert channel is not None, "Should be able to fetch test channel using fixture"


async def test_api_accessible(authenticated_admin_client):
    """Verify API service is running and accessible."""
    response = await authenticated_admin_client.get("/health")
    assert response.status_code == 200, (
        f"API health check failed with status {response.status_code}"
    )


# ======================================================================================
# Guild B / User B Environment Tests (Required for cross-guild isolation testing)
# ======================================================================================


@pytest.mark.asyncio
async def test_guild_b_environment_variables(
    discord_guild_b_id, discord_channel_b_id, discord_user_b_id, discord_user_b_token
):
    """Verify all Guild B environment variables are set."""
    assert discord_guild_b_id, (
        "DISCORD_GUILD_B_ID must be set for cross-guild isolation testing. "
        "See TESTING_E2E.md section 6 for setup instructions"
    )
    assert discord_channel_b_id, (
        "DISCORD_CHANNEL_B_ID must be set for cross-guild isolation testing. "
        "See TESTING_E2E.md section 6 for setup instructions"
    )
    assert discord_user_b_id, (
        "DISCORD_USER_B_ID must be set for cross-guild isolation testing. "
        "See TESTING_E2E.md section 6 for setup instructions"
    )
    assert discord_user_b_token, (
        "DISCORD_USER_B_TOKEN must be set for cross-guild isolation testing. "
        "See TESTING_E2E.md section 6 for setup instructions"
    )


@pytest.mark.asyncio
async def test_guild_b_exists(discord_user_b_token, discord_guild_b_id):
    """Verify Guild B exists and Admin Bot B has access."""

    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_user_b_token)
        guild = client.get_guild(int(discord_guild_b_id))

        if guild is None:
            guild = await client.fetch_guild(int(discord_guild_b_id))

        assert guild is not None, (
            f"Guild B {discord_guild_b_id} not found or bot not a member. "
            f"Check DISCORD_GUILD_B_ID and verify bot is invited to Guild B"
        )
    except discord.Forbidden:
        pytest.fail(f"Bot does not have access to Guild B {discord_guild_b_id}")
    except discord.NotFound:
        pytest.fail(f"Guild B {discord_guild_b_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_channel_b_exists(discord_user_b_token, discord_guild_b_id, discord_channel_b_id):
    """Verify Channel B exists and Admin Bot B has access."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_user_b_token)

        try:
            channel = await client.fetch_channel(int(discord_channel_b_id))
            assert isinstance(channel, discord.TextChannel), (
                f"Channel B {discord_channel_b_id} is not a text channel"
            )
            assert str(channel.guild.id) == discord_guild_b_id, (
                f"Channel B {discord_channel_b_id} is not in Guild B {discord_guild_b_id}"
            )
        except discord.Forbidden:
            pytest.fail(f"Bot does not have access to Channel B {discord_channel_b_id}")
        except discord.NotFound:
            pytest.fail(f"Channel B {discord_channel_b_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_user_b_exists(discord_user_b_token, discord_user_b_id):
    """Verify User B (Admin Bot B) exists."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_user_b_token)

        try:
            user = await client.fetch_user(int(discord_user_b_id))
            assert user is not None, f"User B {discord_user_b_id} not found"
        except discord.NotFound:
            pytest.fail(f"User B {discord_user_b_id} does not exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_user_b_not_in_guild_a(discord_user_b_token, discord_guild_id):
    """Verify User B is NOT a member of Guild A (isolation requirement)."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_user_b_token)

        try:
            guild = await client.fetch_guild(int(discord_guild_id))
            # If we can fetch the guild, User B is a member - this violates isolation
            pytest.fail(
                f"User B should NOT have access to Guild A ({discord_guild_id}), "
                f"but successfully fetched guild: {guild.name}"
            )
        except (discord.Forbidden, discord.NotFound):
            # Expected: User B is not a member of Guild A
            # Discord returns NotFound (404) when bot isn't a guild member (privacy)
            assert True  # discord.Forbidden/NotFound confirms User B is not a member of Guild A
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discord_ids_fixture(discord_ids):
    """Verify discord_ids fixture loads all environment variables correctly."""
    assert discord_ids.guild_a_id, "Guild A ID should be loaded"
    assert discord_ids.channel_a_id, "Channel A ID should be loaded"
    assert discord_ids.user_a_id, "User A ID should be loaded"
    assert discord_ids.guild_b_id, "Guild B ID should be loaded"
    assert discord_ids.channel_b_id, "Channel B ID should be loaded"
    assert discord_ids.user_b_id, "User B ID should be loaded"

    # Validate snowflake ID format (17-19 digits)
    for id_name, id_value in [
        ("guild_a_id", discord_ids.guild_a_id),
        ("channel_a_id", discord_ids.channel_a_id),
        ("user_a_id", discord_ids.user_a_id),
        ("guild_b_id", discord_ids.guild_b_id),
        ("channel_b_id", discord_ids.channel_b_id),
        ("user_b_id", discord_ids.user_b_id),
    ]:
        assert id_value.isdigit(), f"{id_name} should be numeric"
        assert 17 <= len(id_value) <= 19, (
            f"{id_name} should be 17-19 digits (Discord snowflake format), got {len(id_value)}"
        )


@pytest.mark.asyncio
async def test_user_a_not_in_guild_b(discord_token, discord_guild_b_id):
    """Verify User A is NOT a member of Guild B (isolation requirement)."""
    client = discord.Client(intents=discord.Intents.default())

    try:
        await client.login(discord_token)

        try:
            guild = await client.fetch_guild(int(discord_guild_b_id))
            # If we can fetch the guild, User A is a member - this violates isolation
            pytest.fail(
                f"User A should NOT have access to Guild B ({discord_guild_b_id}), "
                f"but successfully fetched guild: {guild.name}"
            )
        except (discord.Forbidden, discord.NotFound):
            # Expected: User A is not a member of Guild B
            # Discord returns NotFound (404) when bot isn't a guild member (privacy)
            assert True  # discord.Forbidden/NotFound confirms User A is not a member of Guild B
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_user_a_fixture_creates_and_cleans_up(admin_db, test_user_a, bot_discord_id):
    """Verify test_user_a fixture creates user correctly and cleans up after test."""
    # User should exist during test (fixture yielded)
    assert test_user_a is not None, "test_user_a fixture should yield a User"
    assert test_user_a.discord_id == bot_discord_id, (
        f"User discord_id should match bot_discord_id: "
        f"expected {bot_discord_id}, got {test_user_a.discord_id}"
    )

    # Query database to verify user exists
    result = await admin_db.execute(select(User).where(User.discord_id == bot_discord_id))
    user_in_db = result.scalar_one_or_none()
    assert user_in_db is not None, f"User with discord_id={bot_discord_id} should exist in database"
    assert user_in_db.id == test_user_a.id, "Database user ID should match fixture user ID"


@pytest.mark.asyncio
async def test_user_b_fixture_creates_and_cleans_up(admin_db, test_user_b, discord_user_b_token):
    """Verify test_user_b fixture creates user correctly and cleans up after test."""
    user_b_discord_id = extract_bot_discord_id(discord_user_b_token)

    # User should exist during test (fixture yielded)
    assert test_user_b is not None, "test_user_b fixture should yield a User"
    assert test_user_b.discord_id == user_b_discord_id, (
        f"User discord_id should match user B bot discord_id: "
        f"expected {user_b_discord_id}, got {test_user_b.discord_id}"
    )

    # Query database to verify user exists
    result = await admin_db.execute(select(User).where(User.discord_id == user_b_discord_id))
    user_in_db = result.scalar_one_or_none()
    assert user_in_db is not None, (
        f"User with discord_id={user_b_discord_id} should exist in database"
    )
    assert user_in_db.id == test_user_b.id, "Database user ID should match fixture user ID"


@pytest.mark.asyncio
async def test_user_main_bot_fixture_creates_and_cleans_up(
    admin_db, test_user_main_bot, discord_main_bot_token
):
    """Verify test_user_main_bot fixture creates user correctly and cleans up after test."""
    main_bot_discord_id = extract_bot_discord_id(discord_main_bot_token)

    # User should exist during test (fixture yielded)
    assert test_user_main_bot is not None, "test_user_main_bot fixture should yield a User"
    assert test_user_main_bot.discord_id == main_bot_discord_id, (
        f"User discord_id should match main bot discord_id: "
        f"expected {main_bot_discord_id}, got {test_user_main_bot.discord_id}"
    )

    # Query database to verify user exists
    result = await admin_db.execute(select(User).where(User.discord_id == main_bot_discord_id))
    user_in_db = result.scalar_one_or_none()
    assert user_in_db is not None, (
        f"User with discord_id={main_bot_discord_id} should exist in database"
    )
    assert user_in_db.id == test_user_main_bot.id, "Database user ID should match fixture user ID"


@pytest.mark.asyncio
async def test_user_fixture_cleanup(admin_db, bot_discord_id):
    """Verify user fixtures clean up after themselves (run after other user fixture tests)."""
    # This test intentionally doesn't use test_user_a fixture
    # If cleanup worked correctly, no user should exist with bot_discord_id
    result = await admin_db.execute(select(User).where(User.discord_id == bot_discord_id))
    user_in_db = result.scalar_one_or_none()

    assert user_in_db is None, (
        f"User with discord_id={bot_discord_id} should NOT exist after fixture cleanup, "
        f"but found user with id={user_in_db.id if user_in_db else None}"
    )


@pytest.mark.asyncio
async def test_fresh_guild_fixture_creates_and_cleans_up(admin_db, fresh_guild_a, discord_ids):
    """Verify fresh_guild_a fixture creates guild correctly and cleans up after test."""
    # Guild should exist during test (fixture yielded GuildContext)
    assert fresh_guild_a is not None, "fresh_guild_a fixture should yield a GuildContext"
    assert fresh_guild_a.db_id is not None, "Guild should have a database ID"
    assert fresh_guild_a.discord_id == discord_ids.guild_a_id, (
        f"Guild discord_id should match discord_ids.guild_a_id: "
        f"expected {discord_ids.guild_a_id}, got {fresh_guild_a.discord_id}"
    )
    assert fresh_guild_a.channel_db_id is not None, "Guild should have a channel database ID"
    assert fresh_guild_a.channel_discord_id == discord_ids.channel_a_id, (
        f"Channel discord_id should match discord_ids.channel_a_id: "
        f"expected {discord_ids.channel_a_id}, got {fresh_guild_a.channel_discord_id}"
    )
    assert fresh_guild_a.template_id is not None, "Guild should have a default template ID"

    # Query database to verify guild exists
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_ids.guild_a_id},
    )
    row = result.fetchone()
    assert row is not None, f"Guild with guild_id={discord_ids.guild_a_id} should exist in database"
    assert row[0] == fresh_guild_a.db_id, "Database guild ID should match fixture guild ID"

    # Verify channel exists
    result = await admin_db.execute(
        text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
        {"channel_id": discord_ids.channel_a_id},
    )
    row = result.fetchone()
    assert row is not None, f"Channel with channel_id={discord_ids.channel_a_id} should exist"
    assert row[0] == fresh_guild_a.channel_db_id, (
        "Database channel ID should match fixture channel ID"
    )

    # Verify template exists
    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE id = :template_id"),
        {"template_id": fresh_guild_a.template_id},
    )
    row = result.fetchone()
    assert row is not None, f"Template with id={fresh_guild_a.template_id} should exist in database"


@pytest.mark.asyncio
async def test_fresh_guild_b_fixture_creates_and_cleans_up(admin_db, fresh_guild_b, discord_ids):
    """Verify fresh_guild_b fixture creates guild B correctly and cleans up after test."""
    # Guild B should exist during test (fixture yielded GuildContext)
    assert fresh_guild_b is not None, "fresh_guild_b fixture should yield a GuildContext"
    assert fresh_guild_b.db_id is not None, "Guild B should have a database ID"
    assert fresh_guild_b.discord_id == discord_ids.guild_b_id, (
        f"Guild B discord_id should match discord_ids.guild_b_id: "
        f"expected {discord_ids.guild_b_id}, got {fresh_guild_b.discord_id}"
    )
    assert fresh_guild_b.channel_db_id is not None, "Guild B should have a channel database ID"
    assert fresh_guild_b.channel_discord_id == discord_ids.channel_b_id, (
        f"Channel B discord_id should match discord_ids.channel_b_id: "
        f"expected {discord_ids.channel_b_id}, got {fresh_guild_b.channel_discord_id}"
    )
    assert fresh_guild_b.template_id is not None, "Guild B should have a default template ID"

    # Query database to verify guild B exists
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_ids.guild_b_id},
    )
    row = result.fetchone()
    assert row is not None, (
        f"Guild B with guild_id={discord_ids.guild_b_id} should exist in database"
    )
    assert row[0] == fresh_guild_b.db_id, "Database guild B ID should match fixture guild ID"


@pytest.mark.asyncio
async def test_synced_guild_fixture_returns_guild_context(admin_db, synced_guild, discord_ids):
    """Verify synced_guild fixture returns properly populated GuildContext."""
    # synced_guild should return GuildContext (not dict like old implementation)
    assert synced_guild is not None, "synced_guild fixture should yield a GuildContext"
    assert synced_guild.db_id is not None, "synced_guild should have database ID"
    assert synced_guild.discord_id == discord_ids.guild_a_id, (
        "synced_guild discord_id should match guild_a_id"
    )
    assert synced_guild.channel_db_id is not None, "synced_guild should have channel database ID"
    assert synced_guild.template_id is not None, "synced_guild should have template ID"

    # Verify it's the same structure as fresh_guild_a
    assert isinstance(synced_guild, GuildContext), (
        "synced_guild should return GuildContext instance"
    )
