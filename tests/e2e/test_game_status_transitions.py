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


"""End-to-end tests for game status transitions and Discord message updates.

Tests the complete flow:
1. POST /games scheduled 1 minute in future with 2 minute duration
2. Status transition daemon processes SCHEDULED→IN_PROGRESS transition
3. Verify game status updated in database
4. Verify Discord message refreshed with IN_PROGRESS status
5. Status transition daemon processes IN_PROGRESS→COMPLETED transition
6. Verify game status updated to COMPLETED
7. Verify Discord message refreshed with COMPLETED status

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- Status transition daemon running to process transitions
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

from shared.models import GameStatus
from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)

pytestmark = pytest.mark.e2e


@pytest.mark.timeout(240)
@pytest.mark.asyncio
async def test_game_status_transitions_update_message(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Game status transitions trigger Discord message updates.

    Verifies:
    - Game created scheduled 1 minute in future with 1 minute duration
    - game_status_schedule populated with IN_PROGRESS and COMPLETED entries
    - Status transition daemon processes SCHEDULED→IN_PROGRESS (waits up to 150s)
    - Game status updated to IN_PROGRESS in database
    - Discord message refreshed to show IN_PROGRESS status
    - Status transition daemon processes IN_PROGRESS→COMPLETED (waits up to 150s)
    - Game status updated to COMPLETED in database
    - Discord message refreshed to show COMPLETED status
    - Total test duration: ~4-5 minutes (1 min + 150s + 1 min + 150s)
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

    scheduled_time = datetime.now(UTC) + timedelta(minutes=1)
    game_title = f"E2E Status Transition Test {uuid4().hex[:8]}"
    game_description = "Test game for status transition verification"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "expected_duration_minutes": "1",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_response_data = response.json()
    game_id = game_response_data["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    admin_db.expire_all()

    result = await admin_db.execute(
        text(
            "SELECT COUNT(*) FROM game_status_schedule "
            "WHERE game_id = :game_id AND target_status IN ('IN_PROGRESS', 'COMPLETED')"
        ),
        {"game_id": game_id},
    )
    schedule_count = result.fetchone()[0]

    assert schedule_count == 2, (
        f"Should have 2 status schedule entries (IN_PROGRESS and COMPLETED), found {schedule_count}"
    )

    result = await admin_db.execute(
        text(
            "SELECT target_status, transition_time FROM game_status_schedule "
            "WHERE game_id = :game_id ORDER BY transition_time"
        ),
        {"game_id": game_id},
    )
    schedules = result.fetchall()
    assert schedules[0][0] == "IN_PROGRESS", "First schedule should be IN_PROGRESS"
    assert schedules[1][0] == "COMPLETED", "Second schedule should be COMPLETED"

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"

    result = await admin_db.execute(
        text("SELECT status FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    initial_status = result.scalar_one()
    assert initial_status == GameStatus.SCHEDULED.value, "Initial game status should be SCHEDULED"

    message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert message is not None, "Discord message should exist after game creation"
    assert len(message.embeds) == 1, "Message should have one embed"
    initial_embed = message.embeds[0]
    assert initial_embed.footer is not None, "Embed should have a footer"
    assert GameStatus.SCHEDULED.display_name in initial_embed.footer.text, (
        f"Initial status should be '{GameStatus.SCHEDULED.display_name}'"
    )

    print(
        "[TEST] Waiting up to 150 seconds for IN_PROGRESS transition "
        "(1 min scheduled time + 60s daemon polling + margin)"
    )

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.IN_PROGRESS.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="game status transition to IN_PROGRESS",
    )

    message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: (
            msg.embeds
            and msg.embeds[0].footer
            and GameStatus.IN_PROGRESS.display_name in msg.embeds[0].footer.text
        ),
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 10,
        interval=2.0,
        description="message update with IN_PROGRESS status",
    )
    assert message is not None, "Discord message should still exist after IN_PROGRESS transition"
    assert len(message.embeds) == 1, "Message should have one embed"

    print("[TEST] ✓ Discord message updated with IN_PROGRESS status")

    print(
        "[TEST] Waiting up to 150 seconds for COMPLETED transition "
        "(1 min duration + 60s daemon polling + margin)"
    )

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.COMPLETED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="game status transition to COMPLETED",
    )

    message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: (
            msg.embeds
            and msg.embeds[0].footer
            and GameStatus.COMPLETED.display_name in msg.embeds[0].footer.text
        ),
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 10,
        interval=2.0,
        description="message update with COMPLETED status",
    )
    assert message is not None, "Discord message should still exist after COMPLETED transition"
    assert len(message.embeds) == 1, "Message should have one embed"

    print("[TEST] ✓ Discord message updated with COMPLETED status")

    print("[TEST] ✓ Game status transition test completed successfully")
    print("[TEST] ✓ Both SCHEDULED→IN_PROGRESS and IN_PROGRESS→COMPLETED verified")
