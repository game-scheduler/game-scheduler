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


"""E2E tests for game authorization flows.

Tests game creation and deletion authorization using real API infrastructure.
Uses E2E guild/channel/user data seeded by init service.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.e2e


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
    """Get database ID for test host user (seeded by init service)."""
    result = await db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": discord_user_id},
    )
    row = result.fetchone()
    if not row:
        pytest.fail(f"Test user {discord_user_id} not found - init seed may have failed")
    return row[0]


@pytest.fixture
async def template_id(db_session, test_guild_id, test_channel_id):
    """Create test template for E2E guild with no role restrictions.

    Creates a template that allows any guild member to host games,
    ensuring real E2E user can successfully create games without mocking roles.
    """
    import uuid

    from shared.models.template import GameTemplate

    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=test_guild_id,
        channel_id=test_channel_id,
        name="E2E Authorization Test Template",
        description="Auto-created template for E2E authorization tests",
        order=0,
        is_default=False,
        max_players=4,
        allowed_host_role_ids=[],  # Empty = anyone in guild can host
    )
    db_session.add(template)
    await db_session.commit()

    yield str(template.id)

    # Cleanup - delete any games using this template first
    await db_session.execute(
        text("DELETE FROM game_sessions WHERE template_id = :id"),
        {"id": str(template.id)},
    )
    await db_session.execute(
        text("DELETE FROM game_templates WHERE id = :id"), {"id": str(template.id)}
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_create_game_with_authorization(
    authenticated_admin_client, template_id, test_host_id, discord_user_id
):
    """Verify game creation succeeds with real user authorization.

    Uses:
    - Real authenticated admin client (with session token)
    - Real E2E user from init service seeding
    - Real template with guild/channel from init service
    - No mocks - full authorization flow through role service
    """
    game_data = {
        "template_id": template_id,
        "title": "E2E Authorization Test Game",
        "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)

    assert response.status_code == 201
    game = response.json()
    assert game["title"] == "E2E Authorization Test Game"
    assert "id" in game
    assert "guild_id" in game
    # Verify game has host information (authenticated_admin_client uses bot, not test_host)
    assert "host" in game
    assert "id" in game["host"]
    assert "discord_id" in game["host"]


@pytest.mark.asyncio
async def test_delete_game_authorization(
    authenticated_admin_client, template_id, db_session, test_host_id, discord_user_id
):
    """Verify game deletion authorization with real user and roles.

    Uses:
    - Real authenticated admin client
    - Real E2E user as game host
    - Real Discord roles checked via role service
    - No mocks - full stack including cache and Discord API
    """
    # Create a game first
    game_data = {
        "template_id": template_id,
        "title": "Game to Delete",
        "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    create_response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert create_response.status_code == 201
    game_id = create_response.json()["id"]

    # Delete the game successfully
    delete_response = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert delete_response.status_code == 204

    # Verify game status is CANCELED (not physically deleted)
    result = await db_session.execute(
        text("SELECT id, status FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row is not None, "Game should still exist in database"
    assert row[1] == "CANCELLED", f"Game status should be CANCELLED, got {row[1]}"

    # Try to delete the same game again - should still return 204 (idempotent)
    second_delete = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert second_delete.status_code == 204

    # Try to delete a non-existent game ID - should return 404
    fake_game_id = "00000000-0000-0000-0000-000000000000"
    fake_response = await authenticated_admin_client.delete(f"/api/v1/games/{fake_game_id}")
    assert fake_response.status_code == 404
    error = fake_response.json()
    assert "detail" in error


@pytest.mark.e2e
async def test_delete_game_authorization_forbidden(
    authenticated_admin_client, template_id, test_host_id, discord_user_id
):
    """Verify 403 when guild member without permission tries to delete game.

    LIMITATION: Current E2E infrastructure only has one authenticated user (bot with
    admin privileges). To properly test 403, we'd need:
    - A second user account (non-admin)
    - That user is a guild member
    - That user is NOT the game host
    - That user does NOT have bot manager role
    - That user does NOT have MANAGE_GUILD permission

    This test documents the expected behavior and verifies the bot CAN delete
    (authorized path). To test unauthorized 403, we need to extend E2E fixtures
    with a second non-admin user account.

    Expected behavior (not testable with current fixtures):
    - Non-admin user tries to delete someone else's game → 403
    - User not in guild tries to delete game → 404 (prevents info disclosure)
    """
    # Create a game hosted by test_host_id
    game_data = {
        "template_id": template_id,
        "title": "Another User's Game",
        "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    create_response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert create_response.status_code == 201
    game_id = create_response.json()["id"]

    # Bot (authenticated_admin_client) CAN delete because it has admin privileges
    # In real scenario with second non-admin user, this would be 403
    delete_response = await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")
    assert delete_response.status_code == 204, (
        "Bot can delete (has admin privileges). "
        "With second non-admin user fixture, this should return 403."
    )

    # TODO: Add second user fixture to test:
    # 1. Guild member without permission → 403
    # 2. Non-guild member → 404 (prevents information disclosure per API security guidelines)
