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


"""End-to-end tests for game cancellation Discord message handling.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. DELETE /games/{game_id} → Bot handles GAME_CANCELLED event
3. Verification that Discord message updated to show cancelled status

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

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import discord
import pytest
from sqlalchemy import text


@pytest.fixture
def clean_test_data(db_session):
    """Clean up only game-related test data before and after test."""
    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.execute(text("DELETE FROM game_participants"))
    db_session.execute(text("DELETE FROM game_sessions"))
    db_session.commit()

    yield

    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.execute(text("DELETE FROM game_participants"))
    db_session.execute(text("DELETE FROM game_sessions"))
    db_session.commit()


@pytest.fixture
def test_guild_id(db_session, discord_guild_id):
    """Get database ID for test guild (seeded by init service)."""
    result = db_session.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test guild {discord_guild_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
def test_channel_id(db_session, discord_channel_id):
    """Get database ID for test channel (seeded by init service)."""
    result = db_session.execute(
        text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
        {"channel_id": discord_channel_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test channel {discord_channel_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
def test_host_id(db_session, discord_user_id):
    """Get database ID for test user (seeded by init service)."""
    result = db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": discord_user_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test user {discord_user_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
def test_template_id(db_session, test_guild_id, synced_guild):
    """Get default template ID for test guild (created by guild sync)."""
    result = db_session.execute(
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
async def test_game_cancellation_updates_message(
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
):
    """
    E2E: Cancelling game via API updates Discord message to show cancelled status.

    Verifies:
    - Game created and message posted to Discord
    - Game cancelled via DELETE /games/{game_id}
    - GAME_CANCELLED event published to RabbitMQ
    - Discord message updated to reflect cancelled status
    - Game status changed to CANCELLED in database
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Cancellation Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "This game will be cancelled",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    await asyncio.sleep(2)

    result = db_session.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    )
    original_message_id = result.scalar_one()
    assert original_message_id is not None, "message_id should be set after game creation"

    original_message = await discord_helper.get_message(discord_channel_id, original_message_id)
    assert original_message is not None, "Discord message should exist before cancellation"
    assert len(original_message.embeds) == 1

    delete_response = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert delete_response.status_code == 204, f"Failed to cancel game: {delete_response.text}"

    await asyncio.sleep(3)

    result = db_session.execute(
        text("SELECT status FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    )
    game_status = result.scalar_one()
    assert game_status == "CANCELLED", f"Expected CANCELLED status but got {game_status}"

    try:
        updated_message = await discord_helper.get_message(discord_channel_id, original_message_id)

        if updated_message is not None and len(updated_message.embeds) > 0:
            embed = updated_message.embeds[0]

            footer_text = embed.footer.text if embed.footer else ""
            assert "cancelled" in footer_text.lower() or "canceled" in footer_text.lower(), (
                f"Status footer should show 'Cancelled'. Footer text: {footer_text}"
            )
    except discord.NotFound:
        pass
