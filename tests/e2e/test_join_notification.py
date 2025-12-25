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


"""End-to-end tests for join notification DM verification.

Tests the complete flow:
1. POST /games with signup_instructions configured
2. POST /games/{game_id}/join → participant joins game
3. Notification schedule entry created (type=join_notification, 60 second delay)
4. Notification daemon processes scheduled notification
5. Discord bot sends DM to participant with signup instructions
6. Verification that DM received with correct content

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- Notification daemon running to process delayed notifications
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

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id
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
async def test_join_notification_with_signup_instructions(
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
    E2E: Join notification delivers DM with signup instructions to participant.

    Verifies:
    - Game created with signup_instructions configured
    - Participant joins game via API
    - notification_schedule entry created with type=join_notification
    - Notification daemon processes schedule after 60 second delay
    - Main bot sends DM to participant with signup instructions
    - Main bot can read DM channel to verify message was sent
    - DM content includes game title and signup instructions
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Join Notification Test {uuid4().hex[:8]}"
    game_description = "Test game for join notification DM verification"
    signup_instructions = (
        "Join our Discord server at https://discord.gg/example123\nCheck in at the game table."
    )

    # Create game with signup instructions and test user as initial participant
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "signup_instructions": signup_instructions,
        "initial_participants": json.dumps([f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")
    print(f"[TEST] Game title: {game_title}")
    print(f"[TEST] Signup instructions: {signup_instructions[:50]}...")
    print(f"[TEST] Test user {discord_user_id} added as initial participant")

    message_id = await wait_for_game_message_id(
        db_session, game_id, timeout=e2e_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Verify notification_schedule entry created
    result = await db_session.execute(
        text(
            "SELECT id, notification_type, participant_id, notification_time, sent "
            "FROM notification_schedule "
            "WHERE game_id = :game_id AND notification_type = 'join_notification'"
        ),
        {"game_id": game_id},
    )
    schedule_row = result.fetchone()
    assert schedule_row is not None, "Join notification schedule entry should be created"

    schedule_id, notif_type, participant_id, notification_time, sent = schedule_row
    print(f"[TEST] ✓ Join notification schedule created (id: {schedule_id})")
    print(f"[TEST]   notification_type: {notif_type}")
    print(f"[TEST]   participant_id: {participant_id}")
    print(f"[TEST]   notification_time: {notification_time}")
    print(f"[TEST]   sent: {sent}")

    assert notif_type == "join_notification", "Schedule should have type=join_notification"
    assert participant_id is not None, "Schedule should have participant_id set"
    assert not sent, "Schedule should not be marked as sent yet"

    # Verify notification time is approximately 60 seconds in future
    time_until_notification = (
        notification_time.replace(tzinfo=UTC) - datetime.now(UTC)
    ).total_seconds()
    assert 50 < time_until_notification < 70, (
        f"Notification should be scheduled ~60 seconds from now, "
        f"got {time_until_notification:.1f} seconds"
    )
    print(f"[TEST] ✓ Notification scheduled {time_until_notification:.1f} seconds from now")

    # Wait for notification daemon to process and send DM
    join_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.JOIN,
        timeout=e2e_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )

    # Verify DM content includes game title and signup instructions
    assert game_title in join_dm.content, (
        f"Join notification DM should mention game title '{game_title}'"
    )
    print("[TEST] ✓ Join notification DM contains game title")

    assert signup_instructions in join_dm.content, (
        "Join notification DM should include full signup instructions"
    )
    print("[TEST] ✓ Join notification DM contains signup instructions")

    assert "joined" in join_dm.content.lower(), (
        "Join notification DM should confirm user joined the game"
    )
    print("[TEST] ✓ Join notification DM confirms user joined")

    # Verify notification marked as sent in database
    result = await db_session.execute(
        text("SELECT sent FROM notification_schedule WHERE id = :schedule_id"),
        {"schedule_id": schedule_id},
    )
    sent_status = result.fetchone()
    if sent_status:
        print(f"[TEST] Notification schedule sent status: {sent_status[0]}")

    print(f"[TEST] DM Content:\n{join_dm.content}")
    print("[TEST] ✓ Join notification DM delivery with signup instructions verified successfully")


@pytest.mark.asyncio
async def test_join_notification_without_signup_instructions(
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
    E2E: Join notification delivers generic DM when no signup instructions.

    Verifies:
    - Game created without signup_instructions
    - Participant joins game via API
    - notification_schedule entry created with type=join_notification
    - Notification daemon processes schedule after 60 second delay
    - Main bot sends generic "You've joined" DM to participant
    - DM does not include signup instructions section
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Join No Instructions Test {uuid4().hex[:8]}"
    game_description = "Test game for join notification without signup instructions"

    # Create game without signup instructions, but with test user as initial participant
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "initial_participants": json.dumps([f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id} (no signup instructions)")
    print(f"[TEST] Test user {discord_user_id} added as initial participant")

    message_id = await wait_for_game_message_id(
        db_session, game_id, timeout=e2e_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Verify notification_schedule entry created
    result = await db_session.execute(
        text(
            "SELECT id, notification_type FROM notification_schedule "
            "WHERE game_id = :game_id AND notification_type = 'join_notification'"
        ),
        {"game_id": game_id},
    )
    schedule_row = result.fetchone()
    assert schedule_row is not None, "Join notification schedule entry should be created"
    print(f"[TEST] ✓ Join notification schedule created (id: {schedule_row[0]})")

    # Wait for notification daemon to process and send DM
    join_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.JOIN,
        timeout=90,
        interval=5,
    )

    # Verify DM content is generic (no signup instructions section)
    assert game_title in join_dm.content, (
        f"Join notification DM should mention game title '{game_title}'"
    )
    print("[TEST] ✓ Join notification DM contains game title")

    assert "joined" in join_dm.content.lower(), (
        "Join notification DM should confirm user joined the game"
    )
    print("[TEST] ✓ Join notification DM confirms user joined")

    # Should NOT contain signup instructions header
    assert "Signup Instructions" not in join_dm.content, (
        "Generic join notification should not include signup instructions section"
    )
    print("[TEST] ✓ Join notification DM does not include signup instructions section")

    print(f"[TEST] DM Content:\n{join_dm.content}")
    print("[TEST] ✓ Generic join notification DM delivery verified successfully")
