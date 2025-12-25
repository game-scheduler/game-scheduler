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


"""End-to-end tests for game update Discord message refresh validation.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. PUT /games/{game_id} → Bot edits Discord message with new content
3. Verification that message_id unchanged, content updated

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test host user (from DISCORD_USER_ID)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id


@pytest.fixture
async def clean_test_data(db_session):
    """Clean up only game-related test data before and after test."""
    await db_session.execute(text("DELETE FROM notification_schedule"))
    await db_session.execute(text("DELETE FROM game_participants"))
    await db_session.execute(text("DELETE FROM game_sessions"))
    await db_session.commit()

    yield

    await db_session.execute(text("DELETE FROM notification_schedule"))
    await db_session.execute(text("DELETE FROM game_participants"))
    await db_session.execute(text("DELETE FROM game_sessions"))
    await db_session.commit()


@pytest.fixture
async def test_guild_id(db_session, discord_guild_id):
    """Get database ID for test guild (seeded by init service)."""
    result = await db_session.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test guild {discord_guild_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
async def test_channel_id(db_session, discord_channel_id):
    """Get database ID for test channel (seeded by init service)."""
    result = await db_session.execute(
        text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
        {"channel_id": discord_channel_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test channel {discord_channel_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
async def test_host_id(db_session, discord_user_id):
    """Get database ID for test user (seeded by init service)."""
    result = await db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": discord_user_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test user {discord_user_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
async def test_template_id(db_session, test_guild_id, synced_guild):
    """Get default template ID for test guild (created by guild sync)."""
    result = await db_session.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(
            f"Default template not found for guild {test_guild_id} - "
            "guild sync may not have created default template"
        )
    return row[0]


@pytest.mark.asyncio
async def test_game_update_refreshes_message(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_guild_id,
    test_channel_id,
    test_host_id,
    test_template_id,
    discord_channel_id,
    discord_user_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Updating game via API refreshes Discord message with new content.

    Verifies:
    - Game created and message posted to Discord
    - Game updated via PUT /games/{game_id}
    - message_id remains unchanged
    - Discord message content reflects updated title and description
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    original_title = f"E2E Update Test {uuid4().hex[:8]}"
    original_description = "Original game description"

    game_data = {
        "template_id": test_template_id,
        "title": original_title,
        "description": original_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    original_message_id = await wait_for_game_message_id(
        db_session, game_id, timeout=e2e_timeouts[TimeoutType.DB_WRITE]
    )
    print(f"[TEST] Original message_id: {original_message_id}")
    assert original_message_id is not None, "Message ID should be populated after announcement"

    message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert message is not None, "Discord message should exist after creation"
    assert len(message.embeds) == 1, "Message should have one embed"
    original_embed = message.embeds[0]
    assert original_embed.title == original_title, "Embed should have original title"

    updated_title = f"Updated Title {uuid4().hex[:8]}"
    updated_description = "Updated game description with new information"

    update_data = {
        "title": updated_title,
        "description": updated_description,
    }

    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}", data=update_data
    )
    assert update_response.status_code == 200, f"Failed to update game: {update_response.text}"
    print("[TEST] Game updated successfully")

    result = await db_session.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row is not None, "Game session not found after update"
    updated_message_id = row[0]
    print(f"[TEST] Updated message_id: {updated_message_id}")

    assert updated_message_id == original_message_id, (
        "message_id should remain unchanged after update"
    )

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=updated_message_id,
        check_func=lambda msg: msg.embeds and msg.embeds[0].title == updated_title,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="game title update",
    )
    assert updated_message is not None, "Discord message should still exist after update"
    assert len(updated_message.embeds) == 1, "Message should have one embed after update"

    updated_embed = updated_message.embeds[0]
    assert updated_embed.title == updated_title, (
        f"Embed title should be updated to '{updated_title}'"
    )
    assert updated_description in updated_embed.description, (
        f"Embed description should contain '{updated_description}'"
    )

    discord_helper.verify_game_embed(
        embed=updated_embed,
        expected_title=updated_title,
        expected_host_id=discord_user_id,
        expected_max_players=4,
    )

    print("[TEST] ✓ Message refreshed successfully with updated content")
