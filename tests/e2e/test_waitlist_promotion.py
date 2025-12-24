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


"""E2E test for waitlist promotion notification flow."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text


@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    from tests.e2e.helpers.discord import DiscordTestHelper

    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


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
        pytest.fail(
            f"Test guild {discord_guild_id} not found - init seed may have failed"
        )
    return row[0]


@pytest.fixture
def test_template_id(db_session, test_guild_id, synced_guild):
    """Get default template ID for test guild (created by guild sync)."""
    result = db_session.execute(
        text(
            "SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"
        ),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(
            f"Default template not found for guild {test_guild_id} - "
            "guild sync may not have created default template"
        )
    return row[0]


async def trigger_promotion_via_removal(
    authenticated_admin_client,
    db_session,
    game_id: str,
    placeholder_participant_id: str,
) -> str:
    """Trigger promotion by removing placeholder participant."""
    update_data = {
        "removed_participant_ids": json.dumps([placeholder_participant_id]),
    }

    response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}", data=update_data
    )
    assert response.status_code == 200, f"Failed to remove placeholder: {response.text}"
    return "Removed placeholder participant to trigger promotion"


async def trigger_promotion_via_max_players_increase(
    authenticated_admin_client,
    db_session,
    game_id: str,
    placeholder_participant_id: str,
) -> str:
    """Trigger promotion by increasing max_players."""
    update_data = {
        "max_players": "2",
    }

    response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}", data=update_data
    )
    assert (
        response.status_code == 200
    ), f"Failed to increase max_players: {response.text}"
    return "Increased max_players from 1 to 2 to trigger promotion"


@pytest.mark.parametrize(
    "trigger_func,expected_player_count,test_desc",
    [
        (trigger_promotion_via_removal, "1/1", "participant removal"),
        (trigger_promotion_via_max_players_increase, "2/2", "max_players increase"),
    ],
    ids=["via_removal", "via_max_players_increase"],
)
@pytest.mark.asyncio
async def test_waitlist_promotion_sends_dm(
    trigger_func: Callable,
    expected_player_count: str,
    test_desc: str,
    authenticated_admin_client,
    db_session,
    discord_helper,
    main_bot_helper,
    test_template_id,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    clean_test_data,
):
    """
    E2E: Waitlist user promoted via trigger and receives DM.

    Verifies:
    - Game created at max capacity with placeholder participant
    - Real test user added to waitlist
    - Trigger (removal or max_players increase) causes promotion
    - Test user receives promotion DM
    - Discord message updated with new participant count
    """
    game_title = f"E2E Promotion ({test_desc}) {datetime.now(UTC).isoformat()}"
    scheduled_at = datetime.now(UTC) + timedelta(hours=2)

    # Create game with max_players=1 and both placeholder and test user
    # Test user will be in overflow (waitlist) since max is 1
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": f"Testing promotion via {test_desc}",
        "scheduled_at": scheduled_at.isoformat(),
        "max_players": 1,
        "initial_participants": json.dumps(["Reserved", f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"

    game_id = response.json()["id"]
    print(f"✓ Created game {game_id} with placeholder + test user (overflow)")

    # Wait for initial announcement
    await asyncio.sleep(2)

    # Get message_id and verify initial state
    result = db_session.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    )
    message_id = result.scalar_one()
    assert message_id is not None

    # Verify initial message shows 1/1 confirmed with test user in overflow
    initial_message = await discord_helper.get_message(discord_channel_id, message_id)
    assert initial_message is not None
    initial_embed = initial_message.embeds[0]

    # Find participants field
    participants_field = None
    for field in initial_embed.fields:
        if field.name and "Participants" in field.name:
            participants_field = field
            break

    assert participants_field is not None, "Participants field not found"
    assert (
        "1/1" in participants_field.name
    ), f"Expected 1/1 in field name, got: {participants_field.name}"
    assert (
        "Reserved" in participants_field.value
    ), f"Expected 'Reserved' in participants, got: {participants_field.value}"
    print("✓ Initial message shows 1/1 with Reserved, test user in overflow")

    # Get placeholder participant ID for removal trigger
    result = db_session.execute(
        text(
            """
            SELECT id FROM game_participants
            WHERE game_session_id = :game_id AND display_name = 'Reserved'
            """
        ),
        {"game_id": game_id},
    )
    placeholder_participant_id = result.scalar_one()
    print(f"✓ Found placeholder participant ID: {placeholder_participant_id}")

    # Trigger promotion using provided strategy
    trigger_message = await trigger_func(
        authenticated_admin_client, db_session, game_id, placeholder_participant_id
    )
    print(f"✓ {trigger_message}")

    # Wait for bot to process promotion event and send DM
    await asyncio.sleep(6)

    # Verify Discord message shows expected player count after promotion
    promoted_message = await discord_helper.get_message(discord_channel_id, message_id)
    assert promoted_message is not None
    promoted_embed = promoted_message.embeds[0]

    # Find participants field
    participants_field = None
    for field in promoted_embed.fields:
        if field.name and "Participants" in field.name:
            participants_field = field
            break

    assert participants_field is not None, "Participants field not found"
    assert (
        expected_player_count in participants_field.name
    ), f"Expected {expected_player_count} in field name after promotion, got: {participants_field.name}"
    print(f"✓ Discord message shows {expected_player_count} with test user promoted")

    # Verify test user received promotion DM (use main_bot_helper since it sends DMs)
    recent_dms = await main_bot_helper.get_user_recent_dms(discord_user_id, limit=10)
    print(f"[TEST] Found {len(recent_dms)} DMs for user {discord_user_id}")
    for i, dm in enumerate(recent_dms):
        content_preview = dm.content[:120] if dm.content else "(no content)"
        print(f"[TEST] DM {i}: {content_preview}")
    
    promotion_dm = None
    for dm in recent_dms:
        if (
            game_title in dm.content
            and "A spot opened up" in dm.content
            and "moved from the waitlist" in dm.content
        ):
            promotion_dm = dm
            break

    print(f"[TEST] Looking for promotion DM with game_title='{game_title}'")
    print(f"[TEST] Looking for phrases: 'A spot opened up', 'moved from the waitlist'")
    
    assert promotion_dm is not None, (
        f"Test user should have received promotion DM. "
        f"Recent DMs: {[dm.content[:100] for dm in recent_dms]}"
    )
    print(f"✓ Test user received promotion DM: {promotion_dm.content[:100]}...")
    print(f"✓ Test complete: Waitlist promotion via {test_desc} validated")
