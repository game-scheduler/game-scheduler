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


"""End-to-end tests for game clone with YES_WITH_DEADLINE carryover.

Tests the complete flow:
1. POST /games → Source game created with test user as participant
2. POST /games/{id}/clone with YES_WITH_DEADLINE → New game created with carryover
3. ParticipantActionSchedule + clone_confirmation NotificationSchedule persisted
4. Notification daemon fires clone_confirmation DM to carried-over participant
5. Participant does NOT confirm → deadline expires
6. Participant action daemon processes expiry → PARTICIPANT_DROP_DUE event
7. Bot removes participant from new game and sends removal DM

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- Notification daemon running to process delayed notifications
- Participant action daemon running to process expiry deadlines
- API service running
- Full stack via compose.e2e.yaml profile

Note: The confirm path (user presses Confirm button) is covered by unit tests
in Phase 4 — real user credentials are not available in the e2e environment.
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

pytestmark = pytest.mark.e2e

_DEADLINE_OFFSET_SECONDS = 120
_CONFIRMATION_NOTIFY_DELAY_SECONDS = 60


@pytest.mark.timeout(420)
@pytest.mark.asyncio
async def test_clone_game_yes_with_deadline_sends_confirmation_dm_and_auto_drops(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: YES_WITH_DEADLINE carryover sends confirmation DM; non-confirming participant is dropped.

    Verifies:
    - Source game created with test user as participant
    - Clone API creates new game with YES_WITH_DEADLINE carryover
    - ParticipantActionSchedule and clone_confirmation NotificationSchedule persist in DB
    - Notification daemon sends clone_confirmation DM to carried-over participant
    - DM contains game title and confirm/decline buttons
    - After deadline expires, participant_action daemon fires PARTICIPANT_DROP_DUE
    - Bot removes the participant from the new game
    - Removed participant receives removal DM
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
    source_title = f"E2E Clone Source {uuid4().hex[:8]}"

    # Create source game with the test user as initial participant
    source_game_data = {
        "template_id": test_template_id,
        "title": source_title,
        "description": "Source game for clone YES_WITH_DEADLINE e2e test",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "initial_participants": json.dumps([f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=source_game_data)
    assert response.status_code == 201, f"Failed to create source game: {response.text}"
    source_game_id = response.json()["id"]
    print(f"\n[TEST] Source game created: {source_game_id}")

    # Wait for Discord message to appear so the game is fully wired
    source_message_id = await wait_for_game_message_id(
        admin_db, source_game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=source_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Clone the game with YES_WITH_DEADLINE; deadline is ~2 minutes from now so
    # the participant action daemon will fire before the general DM_SCHEDULED timeout
    deadline = datetime.now(UTC) + timedelta(seconds=_DEADLINE_OFFSET_SECONDS)
    clone_at = datetime.now(UTC) + timedelta(days=7)
    clone_title = f"E2E Clone Target {uuid4().hex[:8]}"

    clone_response = await authenticated_admin_client.post(
        f"/api/v1/games/{source_game_id}/clone",
        json={
            "scheduled_at": clone_at.isoformat(),
            "player_carryover": "YES_WITH_DEADLINE",
            "player_deadline": deadline.isoformat(),
        },
    )
    assert clone_response.status_code == 201, (
        f"Clone API failed: {clone_response.status_code}: {clone_response.text}"
    )
    clone_data = clone_response.json()
    new_game_id = clone_data["id"]

    # Rename the cloned game so our DM check can find it by title
    rename_response = await authenticated_admin_client.put(
        f"/api/v1/games/{new_game_id}",
        data={"title": clone_title},
    )
    assert rename_response.status_code == 200, (
        f"Failed to rename cloned game: {rename_response.text}"
    )

    print(f"[TEST] Cloned game created: {new_game_id}")
    print(f"[TEST] Deadline: {deadline.isoformat()}")

    # Verify ParticipantActionSchedule was created in DB
    action_row = await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM participant_action_schedule pas "
        "JOIN game_participants gp ON gp.id = pas.participant_id "
        "WHERE gp.game_session_id = :game_id AND pas.action = 'drop'",
        {"game_id": new_game_id},
        lambda row: row[0] > 0,
        timeout=test_timeouts[TimeoutType.DB_WRITE],
        interval=1,
        description="ParticipantActionSchedule creation",
    )
    assert action_row[0] > 0, "ParticipantActionSchedule must be created for carried-over player"
    print("[TEST] ✓ ParticipantActionSchedule created")

    # Verify clone_confirmation NotificationSchedule was created
    notif_row = await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM notification_schedule "
        "WHERE game_id = :game_id AND notification_type = 'clone_confirmation'",
        {"game_id": new_game_id},
        lambda row: row[0] > 0,
        timeout=test_timeouts[TimeoutType.DB_WRITE],
        interval=1,
        description="clone_confirmation NotificationSchedule creation",
    )
    assert notif_row[0] > 0, "clone_confirmation NotificationSchedule must be created"
    print("[TEST] ✓ clone_confirmation NotificationSchedule created")

    # Wait for clone_confirmation DM to be sent (~60s after clone, then daemon polling)
    confirmation_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=clone_title,
        dm_type=DMType.CLONE_CONFIRMATION,
        timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )
    assert confirmation_dm is not None, (
        f"Participant should receive clone_confirmation DM for '{clone_title}'. "
        "Check notification daemon logs."
    )
    assert "confirm" in confirmation_dm.content.lower(), (
        f"Clone confirmation DM should contain 'confirm': {confirmation_dm.content}"
    )
    print(f"[TEST] ✓ Clone confirmation DM received: {confirmation_dm.content[:80]}...")

    # Wait for deadline to trigger auto-drop (participant didn't confirm)
    # The participant_action_daemon wakes when action_time <= now
    drop_timeout = _DEADLINE_OFFSET_SECONDS + test_timeouts[TimeoutType.DM_IMMEDIATE] + 30
    dropped = await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM game_participants WHERE game_session_id = :game_id",
        {"game_id": new_game_id},
        lambda row: row[0] == 0,
        timeout=drop_timeout,
        interval=5,
        description="participant auto-drop after deadline",
    )
    assert dropped[0] == 0, "Participant must be auto-dropped after deadline expires"
    print("[TEST] ✓ Participant auto-dropped after deadline")

    # Verify removal DM was sent to the dropped participant
    removal_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=clone_title,
        dm_type=DMType.REMOVAL,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
        interval=2,
    )
    assert removal_dm is not None, (
        f"Dropped participant should receive removal DM for '{clone_title}'. "
        "Check bot event handler logs."
    )
    print(f"[TEST] ✓ Removal DM received: {removal_dm.content[:80]}...")
    print("[TEST] ✓ Clone YES_WITH_DEADLINE auto-drop flow verified successfully")
