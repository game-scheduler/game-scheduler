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


"""End-to-end tests for signup method Discord button behavior validation.

Tests the complete flow:
1. POST /games with different signup methods → Bot posts announcement to Discord
2. Verification that Discord message join button enabled/disabled state matches signup method
3. Verification that button state persists after fetching message again

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)

Signup Method Behavior:
- SELF_SIGNUP: Join button ENABLED (players can join via Discord)
- HOST_SELECTED: Join button DISABLED (only host can add players)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.models.signup_method import SignupMethod
from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e


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
async def test_self_signup_enables_join_button(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_template_id,
    discord_channel_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Game with SELF_SIGNUP method has enabled join button.

    Verifies:
    - Game created with signup_method=SELF_SIGNUP
    - Discord message posted with join button enabled
    - Button state persists when re-fetching message
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Self Signup Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing SELF_SIGNUP join button enabled",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}, signup_method: SELF_SIGNUP")

    db_session.expire_all()
    await db_session.commit()

    message_id = await wait_for_game_message_id(
        db_session, game_id, e2e_timeouts[TimeoutType.MESSAGE_CREATE]
    )
    print(f"[TEST] Message ID retrieved: {message_id}")

    message = await discord_helper.wait_for_message(
        discord_channel_id,
        message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    print("[TEST] Message fetched, checking button state")

    assert message.components, "Message should have button components"
    assert len(message.components) > 0, "Message should have at least one action row"

    action_row = message.components[0]
    assert len(action_row.children) >= 2, "Action row should have Join and Leave buttons"

    join_button = action_row.children[0]
    assert join_button.label == "Join Game", (
        f"First button should be Join Game: {join_button.label}"
    )
    assert not join_button.disabled, "Join button should be ENABLED for SELF_SIGNUP games"
    print(f"[TEST] ✓ Join button is enabled (disabled={join_button.disabled})")

    # Verify button state persists by re-fetching message
    refetched_message = await discord_helper.get_message(discord_channel_id, message_id)
    refetched_join_button = refetched_message.components[0].children[0]
    assert not refetched_join_button.disabled, "Join button should remain ENABLED after re-fetch"
    print("[TEST] ✓ Join button state persisted after re-fetch")


@pytest.mark.asyncio
async def test_host_selected_disables_join_button(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_template_id,
    discord_channel_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Game with HOST_SELECTED method has disabled join button.

    Verifies:
    - Game created with signup_method=HOST_SELECTED
    - Discord message posted with join button disabled
    - Button state persists when re-fetching message
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Host Selected Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing HOST_SELECTED join button disabled",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "signup_method": SignupMethod.HOST_SELECTED.value,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}, signup_method: HOST_SELECTED")

    db_session.expire_all()
    await db_session.commit()

    message_id = await wait_for_game_message_id(
        db_session, game_id, e2e_timeouts[TimeoutType.MESSAGE_CREATE]
    )
    print(f"[TEST] Message ID retrieved: {message_id}")

    message = await discord_helper.wait_for_message(
        discord_channel_id,
        message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    print("[TEST] Message fetched, checking button state")

    assert message.components, "Message should have button components"
    assert len(message.components) > 0, "Message should have at least one action row"

    action_row = message.components[0]
    assert len(action_row.children) >= 2, "Action row should have Join and Leave buttons"

    join_button = action_row.children[0]
    assert join_button.label == "Join Game", (
        f"First button should be Join Game: {join_button.label}"
    )
    assert join_button.disabled, "Join button should be DISABLED for HOST_SELECTED games"
    print(f"[TEST] ✓ Join button is disabled (disabled={join_button.disabled})")

    leave_button = action_row.children[1]
    assert leave_button.label == "Leave Game", (
        f"Second button should be Leave Game: {leave_button.label}"
    )
    assert not leave_button.disabled, "Leave button should be ENABLED even for HOST_SELECTED games"
    print(f"[TEST] ✓ Leave button is enabled (disabled={leave_button.disabled})")

    # Verify button state persists by re-fetching message
    refetched_message = await discord_helper.get_message(discord_channel_id, message_id)
    refetched_join_button = refetched_message.components[0].children[0]
    refetched_leave_button = refetched_message.components[0].children[1]
    assert refetched_join_button.disabled, "Join button should remain DISABLED after re-fetch"
    assert not refetched_leave_button.disabled, "Leave button should remain ENABLED after re-fetch"
    print("[TEST] ✓ Join button state persisted after re-fetch")
    print("[TEST] ✓ Leave button state persisted after re-fetch")


@pytest.mark.asyncio
async def test_signup_method_defaults_to_self_signup(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_template_id,
    discord_channel_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Game without explicit signup_method defaults to SELF_SIGNUP with enabled button.

    Verifies:
    - Game created without signup_method parameter
    - Database defaults to SELF_SIGNUP
    - Discord message has enabled join button
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Default Signup Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing default signup method behavior",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        # Note: No signup_method specified - should default to SELF_SIGNUP
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}, no signup_method specified")

    db_session.expire_all()
    await db_session.commit()

    # Verify database stored SELF_SIGNUP as default
    result = await db_session.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row, "Game should exist in database"
    assert row[0] == SignupMethod.SELF_SIGNUP.value, (
        f"signup_method should default to SELF_SIGNUP: {row[0]}"
    )
    print(f"[TEST] ✓ Database signup_method defaulted to: {row[0]}")

    message_id = await wait_for_game_message_id(
        db_session, game_id, e2e_timeouts[TimeoutType.MESSAGE_CREATE]
    )

    message = await discord_helper.wait_for_message(
        discord_channel_id,
        message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    join_button = message.components[0].children[0]
    assert not join_button.disabled, "Join button should be ENABLED when defaulting to SELF_SIGNUP"
    print("[TEST] ✓ Join button is enabled with default signup method")


@pytest.mark.asyncio
async def test_edit_game_signup_method_self_to_host(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_template_id,
    discord_channel_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Editing game from SELF_SIGNUP to HOST_SELECTED updates button state.

    Verifies:
    - Game created with SELF_SIGNUP (button enabled)
    - Game edited to HOST_SELECTED via API
    - Database updated correctly
    - Discord message button state changes to disabled
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Edit Signup Test {uuid4().hex[:8]}"

    # Create game with SELF_SIGNUP
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing signup method edit",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}, signup_method: SELF_SIGNUP")

    db_session.expire_all()
    await db_session.commit()

    message_id = await wait_for_game_message_id(
        db_session, game_id, e2e_timeouts[TimeoutType.MESSAGE_CREATE]
    )

    # Verify initial button state is enabled
    initial_message = await discord_helper.wait_for_message(
        discord_channel_id,
        message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    initial_button = initial_message.components[0].children[0]
    assert not initial_button.disabled, "Initial button should be ENABLED"
    print("[TEST] ✓ Initial button state: enabled")

    # Edit game to HOST_SELECTED
    update_data = {
        "signup_method": SignupMethod.HOST_SELECTED.value,
    }
    response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data=update_data,
    )
    assert response.status_code == 200, f"Failed to update game: {response.text}"
    print("[TEST] Game updated to signup_method: HOST_SELECTED")

    db_session.expire_all()
    await db_session.commit()

    # Verify database updated
    result = await db_session.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row, "Game should exist in database"
    assert row[0] == SignupMethod.HOST_SELECTED.value, (
        f"signup_method should be HOST_SELECTED after edit: {row[0]}"
    )
    print(f"[TEST] ✓ Database updated to: {row[0]}")

    # Wait for Discord message update
    updated_message = await discord_helper.wait_for_message_update(
        discord_channel_id,
        message_id,
        lambda msg: msg.components[0].children[0].disabled,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="button disabled after signup method change",
    )

    updated_button = updated_message.components[0].children[0]
    assert updated_button.disabled, "Button should be DISABLED after edit to HOST_SELECTED"
    print("[TEST] ✓ Discord button updated to disabled")


@pytest.mark.asyncio
async def test_edit_game_signup_method_host_to_self(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_template_id,
    discord_channel_id,
    clean_test_data,
    e2e_timeouts,
):
    """
    E2E: Editing game from HOST_SELECTED to SELF_SIGNUP enables button.

    Verifies:
    - Game created with HOST_SELECTED (button disabled)
    - Game edited to SELF_SIGNUP via API
    - Database updated correctly
    - Discord message button state changes to enabled
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Edit Signup Reverse {uuid4().hex[:8]}"

    # Create game with HOST_SELECTED
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing reverse signup method edit",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "signup_method": SignupMethod.HOST_SELECTED.value,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}, signup_method: HOST_SELECTED")

    db_session.expire_all()
    await db_session.commit()

    message_id = await wait_for_game_message_id(
        db_session, game_id, e2e_timeouts[TimeoutType.MESSAGE_CREATE]
    )

    # Verify initial button state is disabled
    initial_message = await discord_helper.wait_for_message(
        discord_channel_id,
        message_id,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    initial_button = initial_message.components[0].children[0]
    assert initial_button.disabled, "Initial button should be DISABLED"
    print("[TEST] ✓ Initial button state: disabled")

    # Edit game to SELF_SIGNUP
    update_data = {
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }
    response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data=update_data,
    )
    assert response.status_code == 200, f"Failed to update game: {response.text}"
    print("[TEST] Game updated to signup_method: SELF_SIGNUP")

    db_session.expire_all()
    await db_session.commit()

    # Verify database updated
    result = await db_session.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row, "Game should exist in database"
    assert row[0] == SignupMethod.SELF_SIGNUP.value, (
        f"signup_method should be SELF_SIGNUP after edit: {row[0]}"
    )
    print(f"[TEST] ✓ Database updated to: {row[0]}")

    # Wait for Discord message update
    updated_message = await discord_helper.wait_for_message_update(
        discord_channel_id,
        message_id,
        lambda msg: not msg.components[0].children[0].disabled,
        timeout=e2e_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="button enabled after signup method change",
    )

    updated_button = updated_message.components[0].children[0]
    assert not updated_button.disabled, "Button should be ENABLED after edit to SELF_SIGNUP"
    print("[TEST] ✓ Discord button updated to enabled")
