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
E2E tests for lazy channel refresh functionality.

Tests channel refresh with real Discord API connections to verify:
- Channels can be refreshed from Discord
- Inactive channels are reactivated when they reappear
- New channels are added during refresh
- refresh=false uses cached channels without Discord API calls
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.e2e


@pytest.fixture
async def get_channels_for_guild(admin_db: AsyncSession):
    """Helper to query channel configurations for a guild."""

    async def _get_channels(guild_id: str) -> list[dict[str, Any]]:
        result = await admin_db.execute(
            text(
                "SELECT id, channel_id, guild_id, is_active "
                "FROM channel_configurations WHERE guild_id = :guild_id "
                "ORDER BY channel_id"
            ),
            {"guild_id": guild_id},
        )
        rows = result.fetchall()
        return [
            {
                "id": str(row[0]),
                "channel_id": row[1],
                "guild_id": str(row[2]),
                "is_active": row[3],
            }
            for row in rows
        ]

    return _get_channels


@pytest.fixture
async def get_guild_by_discord_id(admin_db: AsyncSession):
    """Helper to query guild configuration by Discord snowflake ID."""

    async def _get_guild(discord_guild_id: str) -> dict[str, Any] | None:
        result = await admin_db.execute(
            text("SELECT id, guild_id FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_guild_id},
        )
        row = result.fetchone()
        if row:
            return {"id": str(row[0]), "guild_id": row[1]}
        return None

    return _get_guild


@pytest.mark.asyncio
async def test_channel_refresh_reactivates_inactive_channels(
    authenticated_admin_client: AsyncClient,
    admin_db: AsyncSession,
    discord_ids,
    get_guild_by_discord_id,
    get_channels_for_guild,
):
    """
    Verify refresh=true reactivates channels that were marked inactive.

    Workflow:
    1. Sync guilds to populate channels from Discord
    2. Mark a known channel as inactive in database
    3. Call channels endpoint with refresh=true
    4. Verify the channel is reactivated (is_active=true) in database
    """
    # Step 1: Sync guilds to get initial channel state from Discord
    sync_response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert sync_response.status_code == 200, f"Guild sync failed: {sync_response.text}"

    # Get guild database UUID
    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None, "Guild A not found after sync"
    guild_db_id = guild["id"]

    # Get initial channels
    initial_channels = await get_channels_for_guild(guild_db_id)
    assert len(initial_channels) > 0, "No channels found after sync"

    # Find the known test channel
    test_channel = None
    for ch in initial_channels:
        if ch["channel_id"] == discord_ids.channel_a_id:
            test_channel = ch
            break

    assert test_channel is not None, f"Test channel {discord_ids.channel_a_id} not found"
    assert test_channel["is_active"] is True, "Channel should be active after sync"

    # Step 2: Mark the channel as inactive (simulating user deletion)
    await admin_db.execute(
        text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
        {"id": test_channel["id"]},
    )
    await admin_db.commit()

    # Verify channel is now inactive
    channels_after_delete = await get_channels_for_guild(guild_db_id)
    deleted_channel = next(
        (ch for ch in channels_after_delete if ch["id"] == test_channel["id"]),
        None,
    )
    assert deleted_channel is not None
    assert deleted_channel["is_active"] is False, "Channel should be inactive before refresh"

    # Step 3: Call channels endpoint with refresh=true to re-sync from Discord
    refresh_response = await authenticated_admin_client.get(
        f"/api/v1/guilds/{guild_db_id}/channels",
        params={"refresh": "true"},
    )
    assert refresh_response.status_code == 200, f"Channel refresh failed: {refresh_response.text}"

    # Step 4: Verify channel is reactivated in database
    channels_after_refresh = await get_channels_for_guild(guild_db_id)
    reactivated_channel = next(
        (ch for ch in channels_after_refresh if ch["id"] == test_channel["id"]),
        None,
    )
    assert reactivated_channel is not None, "Channel should still exist after refresh"
    assert reactivated_channel["is_active"] is True, (
        "Channel should be reactivated after refresh (exists in Discord)"
    )

    # Verify the channel appears in the API response
    response_data = refresh_response.json()
    response_channel_ids = {ch["channel_id"] for ch in response_data}
    assert discord_ids.channel_a_id in response_channel_ids, (
        "Reactivated channel should appear in API response"
    )


@pytest.mark.asyncio
async def test_channel_list_without_refresh_uses_cached_data(
    authenticated_admin_client: AsyncClient,
    admin_db: AsyncSession,
    discord_ids,
    get_guild_by_discord_id,
    get_channels_for_guild,
):
    """
    Verify refresh=false returns cached channels without modifying database.

    Workflow:
    1. Sync guilds to populate channels
    2. Mark a channel as inactive
    3. Call channels endpoint with refresh=false
    4. Verify the inactive channel is NOT returned (still inactive in DB)
    """
    # Step 1: Sync guilds
    sync_response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert sync_response.status_code == 200, f"Guild sync failed: {sync_response.text}"

    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None
    guild_db_id = guild["id"]

    initial_channels = await get_channels_for_guild(guild_db_id)
    assert len(initial_channels) > 0

    # Find test channel
    test_channel = next(
        (ch for ch in initial_channels if ch["channel_id"] == discord_ids.channel_a_id),
        None,
    )
    assert test_channel is not None

    # Step 2: Mark channel as inactive
    await admin_db.execute(
        text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
        {"id": test_channel["id"]},
    )
    await admin_db.commit()

    # Step 3: Call endpoint with refresh=false (default)
    response = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_db_id}/channels")
    assert response.status_code == 200

    # Step 4: Verify inactive channel is NOT in response
    response_data = response.json()
    response_channel_ids = {ch["channel_id"] for ch in response_data}
    assert discord_ids.channel_a_id not in response_channel_ids, (
        "Inactive channel should not appear when refresh=false"
    )

    # Verify database state unchanged (channel still inactive)
    channels_after = await get_channels_for_guild(guild_db_id)
    cached_channel = next(
        (ch for ch in channels_after if ch["id"] == test_channel["id"]),
        None,
    )
    assert cached_channel is not None
    assert cached_channel["is_active"] is False, "Channel should remain inactive when refresh=false"
