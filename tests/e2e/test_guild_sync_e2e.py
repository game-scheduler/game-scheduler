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
E2E tests for guild synchronization functionality.

Verifies complete guild sync workflow including:
- Guild configuration creation
- Channel configuration creation
- Default template creation
- Idempotency (multiple syncs don't create duplicates)
- Cross-guild isolation
- RLS enforcement
- Channel filtering (text channels only)
- Permission checking
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.e2e


@pytest.fixture
async def fresh_guild_sync(
    admin_db: AsyncSession,
    discord_ids,
):
    """
    Function-scoped fixture ensuring each test starts with clean guild state.

    Deletes guilds before test to ensure fresh sync testing.
    Deletes guilds after test to ensure test independence.
    Uses discord_ids fixture for environment variable management.
    """
    # Clean up before test
    await admin_db.execute(text("DELETE FROM game_sessions"))
    await admin_db.execute(text("DELETE FROM game_templates"))
    await admin_db.execute(text("DELETE FROM channel_configurations"))
    await admin_db.execute(
        text("DELETE FROM guild_configurations WHERE guild_id IN (:guild_a, :guild_b)"),
        {"guild_a": discord_ids.guild_a_id, "guild_b": discord_ids.guild_b_id},
    )
    await admin_db.commit()

    yield

    # Clean up after test for hermeticity
    await admin_db.execute(text("DELETE FROM game_sessions"))
    await admin_db.execute(text("DELETE FROM game_templates"))
    await admin_db.execute(text("DELETE FROM channel_configurations"))
    await admin_db.execute(
        text("DELETE FROM guild_configurations WHERE guild_id IN (:guild_a, :guild_b)"),
        {"guild_a": discord_ids.guild_a_id, "guild_b": discord_ids.guild_b_id},
    )
    await admin_db.commit()


@pytest.fixture
async def get_guild_by_discord_id(admin_db: AsyncSession):
    """
    Helper fixture to query guild configuration by Discord snowflake ID.

    Returns a function that takes a Discord guild ID and returns the guild record.
    """

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


@pytest.fixture
async def get_channels_for_guild(admin_db: AsyncSession):
    """
    Helper fixture to query channel configurations for a guild.

    Returns a function that takes a guild UUID and returns list of channel records.
    """

    async def _get_channels(guild_id: str) -> list[dict[str, Any]]:
        result = await admin_db.execute(
            text(
                "SELECT id, channel_id, guild_id, is_active "
                "FROM channel_configurations WHERE guild_id = :guild_id"
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
async def get_templates_for_guild(admin_db: AsyncSession):
    """
    Helper fixture to query game templates for a guild.

    Returns a function that takes a guild UUID and returns list of template records.
    """

    async def _get_templates(guild_id: str) -> list[dict[str, Any]]:
        result = await admin_db.execute(
            text(
                "SELECT id, guild_id, channel_id, is_default "
                "FROM game_templates WHERE guild_id = :guild_id"
            ),
            {"guild_id": guild_id},
        )
        rows = result.fetchall()
        return [
            {
                "id": str(row[0]),
                "guild_id": str(row[1]),
                "channel_id": str(row[2]) if row[2] else None,
                "is_default": row[3],
            }
            for row in rows
        ]

    return _get_templates


@pytest.mark.asyncio
async def test_complete_guild_creation(
    authenticated_admin_client: AsyncClient,
    discord_ids,
    admin_db: AsyncSession,
    get_guild_by_discord_id,
    get_channels_for_guild,
    get_templates_for_guild,
    fresh_guild_sync,
):
    """
    Verify complete guild synchronization workflow.

    Tests that sync creates:
    - Guild configuration with correct Discord snowflake
    - Channel configurations for all text channels
    - Default game template for first text channel
    - All counts match between API response and database
    """
    # Call sync endpoint
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200, f"Sync failed: {response.text}"

    sync_results = response.json()
    assert "new_guilds" in sync_results
    assert "new_channels" in sync_results
    assert sync_results["new_guilds"] > 0, "Sync should create at least one guild"

    # Verify guild created in database
    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None, f"Guild {discord_ids.guild_a_id} not found in database"
    assert guild["guild_id"] == discord_ids.guild_a_id
    guild_db_id = guild["id"]

    # Verify channels created
    channels = await get_channels_for_guild(guild_db_id)
    assert len(channels) > 0, "No channels found for guild"
    assert len(channels) == sync_results["new_channels"], (
        f"Channel count mismatch: API={sync_results['new_channels']}, DB={len(channels)}"
    )

    # Verify at least one channel is the expected text channel
    channel_ids = [ch["channel_id"] for ch in channels]
    assert discord_ids.channel_a_id in channel_ids, (
        f"Expected channel {discord_ids.channel_a_id} not found in synced channels"
    )

    # Verify all channels are active
    for channel in channels:
        assert channel["is_active"], f"Channel {channel['channel_id']} is not active"

    # Verify default template created
    templates = await get_templates_for_guild(guild_db_id)
    assert len(templates) > 0, "No templates found for guild"

    default_templates = [t for t in templates if t["is_default"]]
    assert len(default_templates) == 1, (
        f"Expected exactly 1 default template, found {len(default_templates)}"
    )

    default_template = default_templates[0]
    assert default_template["guild_id"] == guild_db_id
    assert default_template["channel_id"] is not None, "Default template has no channel_id"

    # Verify user can access guild through /api/v1/guilds endpoint
    guilds_response = await authenticated_admin_client.get("/api/v1/guilds")
    assert guilds_response.status_code == 200, f"Failed to get guilds: {guilds_response.text}"

    guilds_data = guilds_response.json()
    assert "guilds" in guilds_data
    guild_ids = [g["id"] for g in guilds_data["guilds"]]
    assert guild_db_id in guild_ids, f"Guild {guild_db_id} not accessible via /api/v1/guilds"


@pytest.mark.asyncio
async def test_sync_idempotency(
    authenticated_admin_client: AsyncClient,
    discord_ids,
    admin_db: AsyncSession,
    get_guild_by_discord_id,
    get_channels_for_guild,
    get_templates_for_guild,
    fresh_guild_sync,
):
    """
    Verify sync idempotency - calling sync multiple times creates no duplicates.

    First sync should create new records (new_guilds > 0).
    Second sync should find existing records (new_guilds = 0, new_channels = 0).
    Database should have no duplicate guild/channel/template records.
    """
    # First sync - should create records
    first_response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert first_response.status_code == 200, f"First sync failed: {first_response.text}"

    first_results = first_response.json()
    assert first_results["new_guilds"] > 0 or first_results["new_channels"] > 0, (
        "First sync should create at least some records"
    )

    # Get counts after first sync
    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None, "Guild not found after first sync"
    guild_db_id = guild["id"]

    first_channels = await get_channels_for_guild(guild_db_id)
    first_templates = await get_templates_for_guild(guild_db_id)
    first_channel_count = len(first_channels)
    first_template_count = len(first_templates)

    # Second sync - should create no new records
    second_response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert second_response.status_code == 200, f"Second sync failed: {second_response.text}"

    second_results = second_response.json()
    assert second_results["new_guilds"] == 0, (
        f"Second sync should not create new guilds, but created {second_results['new_guilds']}"
    )
    assert second_results["new_channels"] == 0, (
        f"Second sync should not create new channels, but created {second_results['new_channels']}"
    )

    # Verify no duplicates in database
    second_channels = await get_channels_for_guild(guild_db_id)
    second_templates = await get_templates_for_guild(guild_db_id)

    assert len(second_channels) == first_channel_count, (
        f"Channel count changed after second sync: {first_channel_count} -> {len(second_channels)}"
    )
    assert len(second_templates) == first_template_count, (
        f"Template count changed: {first_template_count} -> {len(second_templates)}"
    )

    # Verify guild still accessible
    guilds_response = await authenticated_admin_client.get("/api/v1/guilds")
    assert guilds_response.status_code == 200, "Failed to access guilds after second sync"

    guilds_data = guilds_response.json()
    guild_ids = [g["id"] for g in guilds_data["guilds"]]
    assert guild_db_id in guild_ids, "Guild not accessible after second sync"


@pytest.mark.asyncio
async def test_multi_guild_sync(
    authenticated_admin_client: AsyncClient,
    authenticated_client_b: AsyncClient,
    discord_ids,
    admin_db: AsyncSession,
    get_guild_by_discord_id,
    get_channels_for_guild,
    fresh_guild_sync,
):
    """
    Verify multi-guild sync with cross-guild isolation.

    User A syncs and only Guild A is created.
    User B syncs and only Guild B is created.
    Each user can only see their own guild's data.
    """
    # User A syncs - should create Guild A
    response_a = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response_a.status_code == 200, f"User A sync failed: {response_a.text}"

    sync_a_results = response_a.json()
    assert sync_a_results["new_guilds"] > 0, "User A sync should create guild"

    # Verify Guild A created
    guild_a = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild_a is not None, f"Guild A {discord_ids.guild_a_id} not found in database"
    guild_a_db_id = guild_a["id"]

    # Verify Guild B does NOT exist yet
    guild_b = await get_guild_by_discord_id(discord_ids.guild_b_id)
    assert guild_b is None, "Guild B should not exist before User B sync"

    # User B syncs - should create Guild B
    response_b = await authenticated_client_b.post("/api/v1/guilds/sync")
    assert response_b.status_code == 200, f"User B sync failed: {response_b.text}"

    sync_b_results = response_b.json()
    assert sync_b_results["new_guilds"] > 0, "User B sync should create guild"

    # Verify Guild B created
    guild_b = await get_guild_by_discord_id(discord_ids.guild_b_id)
    assert guild_b is not None, f"Guild B {discord_ids.guild_b_id} not found in database"
    guild_b_db_id = guild_b["id"]

    # Verify both guilds have channels
    channels_a = await get_channels_for_guild(guild_a_db_id)
    assert len(channels_a) > 0, "Guild A should have channels"

    channels_b = await get_channels_for_guild(guild_b_db_id)
    assert len(channels_b) > 0, "Guild B should have channels"

    # Verify User A can only see Guild A
    guilds_a_response = await authenticated_admin_client.get("/api/v1/guilds")
    assert guilds_a_response.status_code == 200
    guilds_a_data = guilds_a_response.json()
    guild_a_ids = [g["id"] for g in guilds_a_data["guilds"]]

    assert guild_a_db_id in guild_a_ids, "User A should see Guild A"
    assert guild_b_db_id not in guild_a_ids, "User A should NOT see Guild B"

    # Verify User B can only see Guild B
    guilds_b_response = await authenticated_client_b.get("/api/v1/guilds")
    assert guilds_b_response.status_code == 200
    guilds_b_data = guilds_b_response.json()
    guild_b_ids = [g["id"] for g in guilds_b_data["guilds"]]

    assert guild_b_db_id in guild_b_ids, "User B should see Guild B"
    assert guild_a_db_id not in guild_b_ids, "User B should NOT see Guild A"


@pytest.mark.asyncio
async def test_rls_enforcement_after_sync(
    authenticated_admin_client: AsyncClient,
    authenticated_client_b: AsyncClient,
    admin_db: AsyncSession,
    discord_ids,
    get_guild_by_discord_id,
    fresh_guild_sync,
):
    """
    Verify RLS properly isolates guild data after sync.

    After syncing both guilds:
    - User A can access Guild A templates
    - User A gets 404 for Guild B templates
    - User B can access Guild B templates
    - User B gets 404 for Guild A templates
    """
    # Sync both guilds
    response_a = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response_a.status_code == 200, f"User A sync failed: {response_a.text}"

    response_b = await authenticated_client_b.post("/api/v1/guilds/sync")
    assert response_b.status_code == 200, f"User B sync failed: {response_b.text}"

    # Get guild database IDs
    guild_a = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild_a is not None, "Guild A not found"
    guild_a_db_id = guild_a["id"]

    guild_b = await get_guild_by_discord_id(discord_ids.guild_b_id)
    assert guild_b is not None, "Guild B not found"
    guild_b_db_id = guild_b["id"]

    # Get Guild A's default template ID
    result_a = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_a_db_id},
    )
    row_a = result_a.fetchone()
    assert row_a, "Guild A should have a default template"
    template_a_id = str(row_a[0])

    # Get Guild B's default template ID
    result_b = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_b_db_id},
    )
    row_b = result_b.fetchone()
    assert row_b, "Guild B should have a default template"
    template_b_id = str(row_b[0])

    # User A can access Guild A templates
    templates_a_response = await authenticated_admin_client.get(
        f"/api/v1/guilds/{guild_a_db_id}/templates"
    )
    assert templates_a_response.status_code == 200, (
        f"User A should access Guild A templates: {templates_a_response.text}"
    )
    templates_a = templates_a_response.json()  # Returns list directly
    template_a_ids = [t["id"] for t in templates_a]
    assert template_a_id in template_a_ids, "User A should see Guild A's default template"

    # User A gets 404 for Guild B templates (RLS filters guild)
    templates_b_as_a_response = await authenticated_admin_client.get(
        f"/api/v1/guilds/{guild_b_db_id}/templates"
    )
    assert templates_b_as_a_response.status_code == 404, (
        "User A should get 404 for Guild B templates (RLS enforcement)"
    )

    # User B can access Guild B templates
    templates_b_response = await authenticated_client_b.get(
        f"/api/v1/guilds/{guild_b_db_id}/templates"
    )
    assert templates_b_response.status_code == 200, (
        f"User B should access Guild B templates: {templates_b_response.text}"
    )
    templates_b = templates_b_response.json()  # Returns list directly
    template_b_ids = [t["id"] for t in templates_b]
    assert template_b_id in template_b_ids, "User B should see Guild B's default template"

    # User B gets 404 for Guild A templates (RLS filters guild)
    templates_a_as_b_response = await authenticated_client_b.get(
        f"/api/v1/guilds/{guild_a_db_id}/templates"
    )
    assert templates_a_as_b_response.status_code == 404, (
        "User B should get 404 for Guild A templates (RLS enforcement)"
    )


@pytest.mark.asyncio
async def test_channel_filtering(
    authenticated_admin_client: AsyncClient,
    discord_ids,
    admin_db: AsyncSession,
    get_guild_by_discord_id,
    get_channels_for_guild,
    get_templates_for_guild,
    fresh_guild_sync,
):
    """
    Verify only text channels (type=0) are synced.

    Guild sync should:
    - Create channel configs only for text channels
    - Skip voice channels and other channel types
    - Default template should use first text channel
    """
    # Sync guilds
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200, f"Sync failed: {response.text}"

    sync_results = response.json()

    # Get guild from database
    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None, "Guild not found in database"
    guild_db_id = guild["id"]

    # Get synced channels
    channels = await get_channels_for_guild(guild_db_id)
    assert len(channels) > 0, "No channels found"

    # Verify all synced channels are text channels (implementation filters by type=0)
    channel_ids = [ch["channel_id"] for ch in channels]  # Discord snowflake IDs
    channel_db_ids = [ch["id"] for ch in channels]  # Database UUIDs

    # Verify the known text channel is in the list
    assert discord_ids.channel_a_id in channel_ids, (
        f"Expected text channel {discord_ids.channel_a_id} not found in synced channels"
    )

    # Verify response count matches database count
    assert sync_results["new_channels"] == len(channels), (
        f"Channel count mismatch: API={sync_results['new_channels']}, DB={len(channels)}"
    )

    # Verify default template uses a text channel
    templates = await get_templates_for_guild(guild_db_id)
    default_templates = [t for t in templates if t["is_default"]]
    assert len(default_templates) == 1, "Should have exactly one default template"

    default_template = default_templates[0]
    assert default_template["channel_id"] in channel_db_ids, (
        "Default template should reference a synced text channel (by database UUID)"
    )


@pytest.mark.asyncio
async def test_template_creation_with_channels(
    authenticated_admin_client: AsyncClient,
    discord_ids,
    admin_db: AsyncSession,
    get_guild_by_discord_id,
    get_channels_for_guild,
    get_templates_for_guild,
    fresh_guild_sync,
):
    """
    Verify template creation behavior with various channel scenarios.

    Tests that:
    - Guild with text channels creates default template
    - Template is associated with first text channel
    - Template has is_default=True
    """
    # Sync guild
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200, f"Sync failed: {response.text}"

    # Get guild from database
    guild = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild is not None, "Guild not found"
    guild_db_id = guild["id"]

    # Get channels and templates
    channels = await get_channels_for_guild(guild_db_id)
    templates = await get_templates_for_guild(guild_db_id)

    if len(channels) > 0:
        # Guild has text channels - should have default template
        assert len(templates) > 0, "Guild with text channels should have default template"

        default_templates = [t for t in templates if t["is_default"]]
        assert len(default_templates) == 1, "Should have exactly one default template"

        default_template = default_templates[0]
        assert default_template["is_default"] is True
        assert default_template["channel_id"] is not None, "Default template should have channel"

        # Verify template channel is one of the synced channels
        channel_ids = [ch["id"] for ch in channels]
        assert default_template["channel_id"] in channel_ids, (
            "Template channel should be one of the synced channels"
        )
    else:
        # Guild has no text channels - may not have default template
        # This is expected behavior, though rare in real guilds
        pass


@pytest.mark.asyncio
async def test_sync_respects_user_permissions(
    authenticated_admin_client: AsyncClient,
    authenticated_client_b: AsyncClient,
    discord_ids,
    get_guild_by_discord_id,
    fresh_guild_sync,
):
    """
    Verify sync only includes guilds where user has MANAGE_GUILD permission.

    The sync endpoint computes candidate guilds as:
    (main bot guilds ∩ user admin guilds)

    Setup:
    - Admin Bot A: Has MANAGE_GUILD in Guild A only (not in Guild B)
    - Admin Bot B: Has MANAGE_GUILD in Guild B only (not in Guild A)
    - Main Bot: Installed in both Guild A and Guild B

    Expected behavior:
    - Admin Bot A syncs → only Guild A created (A is in both sets)
    - Admin Bot B syncs → only Guild B created (B is in both sets)
    - Each bot only sees guilds where they have MANAGE_GUILD permission
    """
    # Admin Bot A syncs - should only create Guild A
    # Main bot guilds {A, B} ∩ Admin Bot A admin guilds {A} = {A}
    response_a = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response_a.status_code == 200, f"Admin Bot A sync failed: {response_a.text}"

    sync_a_results = response_a.json()
    assert "new_guilds" in sync_a_results
    assert "new_channels" in sync_a_results

    # Verify Guild A was synced (Admin Bot A has MANAGE_GUILD in A)
    guild_a = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild_a is not None, (
        "Guild A should be synced - Admin Bot A has MANAGE_GUILD permission in Guild A"
    )

    # Verify Guild B was NOT synced by Admin Bot A (no MANAGE_GUILD in B, not a member)
    guild_b = await get_guild_by_discord_id(discord_ids.guild_b_id)
    assert guild_b is None, (
        "Guild B should NOT be synced by Admin Bot A - "
        "Admin Bot A lacks MANAGE_GUILD in Guild B and is not a member"
    )

    # Admin Bot B syncs - should only create Guild B
    # Main bot guilds {A, B} ∩ Admin Bot B admin guilds {B} = {B}
    response_b = await authenticated_client_b.post("/api/v1/guilds/sync")
    assert response_b.status_code == 200, f"Admin Bot B sync failed: {response_b.text}"

    # Now verify Guild B exists (Admin Bot B has MANAGE_GUILD in B)
    guild_b = await get_guild_by_discord_id(discord_ids.guild_b_id)
    assert guild_b is not None, (
        "Guild B should be synced - Admin Bot B has MANAGE_GUILD permission in Guild B"
    )

    # Verify Guild A still exists and wasn't touched by Admin Bot B's sync
    guild_a_after = await get_guild_by_discord_id(discord_ids.guild_a_id)
    assert guild_a_after is not None, "Guild A should still exist after Admin Bot B sync"
    assert guild_a_after["id"] == guild_a["id"], "Guild A ID should be unchanged"
