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

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_game_cancellation_updates_message(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Cancelling game via API deletes the Discord message and removes the game row.

    Verifies:
    - Game created and message posted to Discord
    - Game cancelled via DELETE /games/{game_id}
    - GAME_CANCELLED event published to RabbitMQ
    - Discord announcement message deleted
    - Game row absent from database
    """
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Test guild {discord_guild_id} not found"
    test_guild_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {test_guild_id}"
    test_template_id = row[0]

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

    original_message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert original_message_id is not None, "message_id should be populated after announcement"

    original_message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert original_message is not None, "Discord message should exist before cancellation"
    assert len(original_message.embeds) == 1

    delete_response = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert delete_response.status_code == 204, f"Failed to cancel game: {delete_response.text}"

    result = await admin_db.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    )
    assert result.scalar_one_or_none() is None, (
        "Game row should be absent from DB after cancellation"
    )

    await discord_helper.wait_for_message_deleted(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
    )


@pytest.mark.asyncio
async def test_game_cancellation_with_participant_updates_message(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Cancelling a game that has a participant via DELETE /games/{id} succeeds.

    Reproduces the production bug where SQLAlchemy tried to SET game_session_id=NULL
    on loaded participant rows, which was blocked by the RLS WITH CHECK policy.
    """
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Test guild {discord_guild_id} not found"
    test_guild_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {test_guild_id}"
    test_template_id = row[0]

    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Cancellation With Participant {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "This game has a participant and will be cancelled",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "initial_participants": f'["<@{discord_user_id}>"]',
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    original_message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert original_message_id is not None, "message_id should be populated after announcement"

    await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    delete_response = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert delete_response.status_code == 204, f"Failed to cancel game: {delete_response.text}"

    result = await admin_db.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    )
    assert result.scalar_one_or_none() is None, (
        "Game row should be absent from DB after cancellation"
    )

    await discord_helper.wait_for_message_deleted(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
    )
