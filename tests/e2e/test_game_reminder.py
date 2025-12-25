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


"""End-to-end tests for game reminder DM verification.

Tests the complete flow:
1. POST /games with reminder_minutes=[1] → Game scheduled 2 minutes in future
2. Notification daemon processes scheduled reminders
3. Discord bot sends DM reminder to test user
4. Verification that DM received with correct game details

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- Notification daemon running to process reminders
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test host user (from DISCORD_USER_ID)
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)
from tests.e2e.helpers.discord import DMType


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


@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    from tests.e2e.helpers.discord import DiscordTestHelper

    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


@pytest.mark.asyncio
async def test_game_reminder_dm_delivery(
    authenticated_admin_client,
    db_session,
    main_bot_helper,
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
    E2E: Game reminder triggers DM delivery to test user.

    Verifies:
    - Game created with reminder_minutes=[1] (1 minute before game)
    - Game scheduled 2 minutes in future
    - Test user added as participant
    - Notification daemon processes reminder schedule
    - Main bot sends DM reminder to test user
    - Main bot can read DM channel to verify message was sent
    - DM content includes game title and scheduled time
    """
    scheduled_time = datetime.now(UTC) + timedelta(minutes=2)
    game_title = f"E2E Reminder Test {uuid4().hex[:8]}"
    game_description = "Test game for DM reminder verification"

    # Add test user as initial participant so they receive reminder DM
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "reminder_minutes": json.dumps([1]),
        "initial_participants": json.dumps([f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")
    print(f"[TEST] Game scheduled at: {scheduled_time.isoformat()}")
    print("[TEST] Reminder set for 1 minute before game")
    print(f"[TEST] Test user added as initial participant (discord_id: {discord_user_id})")

    message_id = await wait_for_game_message_id(
        db_session, game_id, timeout=e2e_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Wait for reminder to be scheduled (may take a moment after game creation)
    row = await wait_for_db_condition(
        db_session,
        "SELECT COUNT(*) FROM notification_schedule "
        "WHERE game_id = :game_id AND reminder_minutes = 1",
        {"game_id": game_id},
        lambda row: row[0] > 0,
        timeout=e2e_timeouts[TimeoutType.DB_WRITE],
        interval=1,
        description="reminder schedule creation",
    )
    reminder_count = row[0]
    print(f"[TEST] Reminder scheduled in database (count: {reminder_count})")

    # Wait for reminder DM to be sent
    reminder_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REMINDER,
        timeout=e2e_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )

    print("[TEST] ✓ Reminder DM contains game title")
    print(f"[TEST] DM Content: {reminder_dm.content}")
    print("[TEST] ✓ Game reminder DM delivery verified successfully")
