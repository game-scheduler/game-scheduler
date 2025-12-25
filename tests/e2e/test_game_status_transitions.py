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

from shared.models.game import GameStatus
from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)


@pytest.fixture
async def clean_test_data(db_session):
    """Clean up only game-related test data before and after test."""
    await db_session.execute(text("DELETE FROM game_status_schedule"))
    await db_session.execute(text("DELETE FROM notification_schedule"))
    await db_session.execute(text("DELETE FROM game_participants"))
    await db_session.execute(text("DELETE FROM game_sessions"))
    await db_session.commit()

    yield

    await db_session.execute(text("DELETE FROM game_status_schedule"))
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
async def test_game_status_transitions_update_message(
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
    E2E: Game status transitions trigger Discord message updates.

    Verifies:
    - Game created scheduled 1 minute in future with 2 minute duration
    - game_status_schedule populated with IN_PROGRESS and COMPLETED entries
    - Status transition daemon processes SCHEDULED→IN_PROGRESS (waits up to 150s)
    - Game status updated to IN_PROGRESS in database
    - Discord message refreshed to show IN_PROGRESS status
    - Status transition daemon processes IN_PROGRESS→COMPLETED (waits up to 180s)
    - Game status updated to COMPLETED in database
    - Discord message refreshed to show COMPLETED status
    - Total test duration: ~5-6 minutes (1 min + 150s + 2 min + 180s)
    """
    scheduled_time = datetime.now(UTC) + timedelta(minutes=1)
    game_title = f"E2E Status Transition Test {uuid4().hex[:8]}"
    game_description = "Test game for status transition verification"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "expected_duration_minutes": "2",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_response_data = response.json()
    game_id = game_response_data["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    db_session.expire_all()

    result = await db_session.execute(
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

    result = await db_session.execute(
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
        db_session, game_id, timeout=e2e_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"

    result = await db_session.execute(
        text("SELECT status FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    initial_status = result.scalar_one()
    assert initial_status == GameStatus.SCHEDULED.value, "Initial game status should be SCHEDULED"

    message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
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
        db_session,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.IN_PROGRESS.value,
        timeout=e2e_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="game status transition to IN_PROGRESS",
    )

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should still exist after IN_PROGRESS transition"
    assert len(message.embeds) == 1, "Message should have one embed"
    embed = message.embeds[0]

    has_in_progress_indicator = False
    if embed.fields:
        for field in embed.fields:
            if GameStatus.IN_PROGRESS.display_name in field.value:
                has_in_progress_indicator = True
                break

    if not has_in_progress_indicator and embed.description:
        if GameStatus.IN_PROGRESS.display_name in embed.description:
            has_in_progress_indicator = True

    if not has_in_progress_indicator and embed.footer:
        if GameStatus.IN_PROGRESS.display_name in embed.footer.text:
            has_in_progress_indicator = True

    assert has_in_progress_indicator, "Discord message should display IN_PROGRESS status indicator"

    print(
        "[TEST] Waiting up to 180 seconds for COMPLETED transition "
        "(2 min duration + 60s daemon polling + margin)"
    )

    await wait_for_db_condition(
        db_session,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.COMPLETED.value,
        timeout=e2e_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="game status transition to COMPLETED",
    )

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should still exist after COMPLETED transition"
    assert len(message.embeds) == 1, "Message should have one embed"
    embed = message.embeds[0]

    has_completed_indicator = False
    if embed.fields:
        for field in embed.fields:
            if GameStatus.COMPLETED.display_name in field.value:
                has_completed_indicator = True
                break

    if not has_completed_indicator and embed.description:
        if GameStatus.COMPLETED.display_name in embed.description:
            has_completed_indicator = True

    if not has_completed_indicator and embed.footer:
        if GameStatus.COMPLETED.display_name in embed.footer.text:
            has_completed_indicator = True

    assert has_completed_indicator, "Discord message should display COMPLETED status indicator"

    print("[TEST] ✓ Game status transition test completed successfully")
    print("[TEST] ✓ Both SCHEDULED→IN_PROGRESS and IN_PROGRESS→COMPLETED verified")
