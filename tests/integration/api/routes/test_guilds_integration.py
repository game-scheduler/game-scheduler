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
Integration tests for guild channel endpoints.

Tests HTTP API behavior without mocking internal Discord API calls.
Full refresh behavior is tested in E2E tests with real Discord connections.
"""

import httpx
import pytest
from sqlalchemy import text

from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_BOT_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_tests"
TEST_USER_DISCORD_ID = "test_user_123456789"


@pytest.fixture
async def authenticated_client(
    api_base_url,
    create_guild,
    create_user,
    seed_redis_cache,
):
    """Authenticated HTTP client for guild endpoint tests."""
    guild = create_guild()
    create_user(discord_user_id=TEST_USER_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_BOT_TOKEN, TEST_USER_DISCORD_ID)

    await seed_redis_cache(
        user_discord_id=TEST_USER_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    client = httpx.AsyncClient(base_url=api_base_url, timeout=30.0)
    client.cookies.set("session_token", session_token)

    yield client, guild

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.mark.asyncio
async def test_list_channels_returns_database_channels(
    authenticated_client,
    create_channel,
):
    """Verify endpoint returns channels from database."""
    client, guild = authenticated_client
    guild_id = guild["id"]

    _ = create_channel(guild_id=guild_id, discord_channel_id="111111")
    _ = create_channel(guild_id=guild_id, discord_channel_id="222222")

    response = await client.get(f"/api/v1/guilds/{guild_id}/channels")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    channel_ids = {ch["channel_id"] for ch in data}
    assert "111111" in channel_ids
    assert "222222" in channel_ids


@pytest.mark.asyncio
async def test_list_channels_accepts_refresh_parameter(
    authenticated_client,
    create_channel,
):
    """Verify refresh query parameter is accepted by endpoint."""
    client, guild = authenticated_client
    guild_id = guild["id"]

    create_channel(guild_id=guild_id, discord_channel_id="333333")

    # Test that refresh=false works (uses cached channels)
    response = await client.get(
        f"/api/v1/guilds/{guild_id}/channels",
        params={"refresh": "false"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_channels_returns_only_active_channels(
    authenticated_client,
    create_channel,
    admin_db_sync,
):
    """Verify only active channels are returned."""
    client, guild = authenticated_client
    guild_id = guild["id"]

    _ = create_channel(guild_id=guild_id, discord_channel_id="444444")
    inactive_channel = create_channel(guild_id=guild_id, discord_channel_id="555555")

    # Mark second channel as inactive
    admin_db_sync.execute(
        text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
        {"id": inactive_channel["id"]},
    )
    admin_db_sync.commit()

    response = await client.get(f"/api/v1/guilds/{guild_id}/channels")

    assert response.status_code == 200
    data = response.json()

    channel_ids = {ch["channel_id"] for ch in data}
    assert "444444" in channel_ids
    assert "555555" not in channel_ids


@pytest.mark.asyncio
async def test_list_channels_returns_channels_sorted_by_name(
    authenticated_client,
    create_channel,
    redis_client_async,
):
    """Verify channels are returned sorted alphabetically by name."""
    client, guild = authenticated_client
    guild_id = guild["id"]
    guild_discord_id = guild["guild_id"]

    ch_z = create_channel(guild_id=guild_id, discord_channel_id="777771")
    ch_a = create_channel(guild_id=guild_id, discord_channel_id="777772")
    ch_m = create_channel(guild_id=guild_id, discord_channel_id="777773")

    # Seed Discord channel names in reverse alphabetical order to confirm sorting
    await redis_client_async.set_json(
        f"discord:guild_channels:{guild_discord_id}",
        [
            {"id": ch_z["channel_id"], "name": "zebra-games", "type": 0},
            {"id": ch_a["channel_id"], "name": "alpha-games", "type": 0},
            {"id": ch_m["channel_id"], "name": "middle-games", "type": 0},
        ],
        ttl=300,
    )

    response = await client.get(f"/api/v1/guilds/{guild_id}/channels")

    assert response.status_code == 200
    data = response.json()
    names = [ch["channel_name"] for ch in data]
    assert names == sorted(names)
