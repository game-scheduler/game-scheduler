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
E2E environment validation test.

This test runs FIRST (test_00_*) to verify the E2E environment is properly configured.
If this fails, all other E2E tests will fail with clearer error messages.
"""

import os

import discord
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.e2e

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_environment_variables():
    """Verify all required E2E environment variables are set."""
    required_vars = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_GUILD_A_ID",
        "DISCORD_GUILD_A_CHANNEL_ID",
        "DISCORD_USER_ID",
        "DATABASE_URL",
        "API_BASE_URL",
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
async def test_database_seeded(db_session, discord_guild_id, discord_channel_id, discord_user_id):
    """Verify init service seeded the database with test data."""
    result = await db_session.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    guild_row = result.fetchone()
    assert guild_row is not None, (
        f"Guild {discord_guild_id} not found in database. "
        f"Init service may have failed to seed E2E data"
    )

    result = await db_session.execute(
        text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
        {"channel_id": discord_channel_id},
    )
    channel_row = result.fetchone()
    assert channel_row is not None, (
        f"Channel {discord_channel_id} not found in database. "
        f"Init service may have failed to seed E2E data"
    )

    result = await db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": discord_user_id},
    )
    user_row = result.fetchone()
    assert user_row is not None, (
        f"User {discord_user_id} not found in database. "
        f"Init service may have failed to seed E2E data"
    )


@pytest.mark.asyncio
async def test_discord_helper_fixture(discord_helper, discord_channel_id):
    """Verify discord_helper fixture connects successfully and can fetch channel."""
    assert discord_helper._connected, "Discord helper should be connected"
    assert discord_helper.client.user is not None, "Bot user should exist after connection"

    channel = await discord_helper.client.fetch_channel(int(discord_channel_id))
    assert channel is not None, "Should be able to fetch test channel using fixture"


def test_api_accessible(http_client):
    """Verify API service is running and accessible."""
    response = http_client.get("/health")
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
async def test_guild_b_database_seeded(
    db_session, discord_guild_b_id, discord_channel_b_id, discord_user_b_id
):
    """Verify init service seeded Guild B data in database."""
    result = await db_session.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_b_id},
    )
    guild_row = result.fetchone()
    assert guild_row is not None, (
        f"Guild B {discord_guild_b_id} not found in database. "
        f"Init service may have failed to seed Guild B data"
    )

    result = await db_session.execute(
        text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
        {"channel_id": discord_channel_b_id},
    )
    channel_row = result.fetchone()
    assert channel_row is not None, (
        f"Channel B {discord_channel_b_id} not found in database. "
        f"Init service may have failed to seed Guild B data"
    )

    result = await db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": discord_user_b_id},
    )
    user_row = result.fetchone()
    assert user_row is not None, (
        f"User B {discord_user_b_id} not found in database. "
        f"Init service may have failed to seed Guild B data"
    )


@pytest.mark.asyncio
async def test_guild_b_has_default_template(db_session, discord_guild_b_id):
    """Verify Guild B has a default game template."""
    result = await db_session.execute(
        text(
            "SELECT t.id FROM game_templates t "
            "JOIN guild_configurations g ON t.guild_id = g.id "
            "WHERE g.guild_id = :guild_id AND t.is_default = true"
        ),
        {"guild_id": discord_guild_b_id},
    )
    template_row = result.fetchone()
    assert template_row is not None, (
        f"Guild B {discord_guild_b_id} does not have a default template. "
        f"Init service may have failed to seed Guild B template"
    )


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
            pass
    finally:
        await client.close()


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
            pass
    finally:
        await client.close()
