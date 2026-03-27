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


"""E2E tests for ROLE_BASED signup method join path.

Verifies that role priority is resolved at join time and stored in
position_type / position on the participant row.  Uses the API join path only.

Requires two roles in DISCORD_GUILD_A_ID:
  DISCORD_TEST_ROLE_A_ID  — held by Admin Bot A
  DISCORD_TEST_ROLE_B_ID  — NOT held by Admin Bot A

See docs/developer/TESTING.md § "Role-Based Signup E2E Test Roles" for setup.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.models.template import GameTemplate

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def role_a_id() -> str:
    """Discord role ID held by Admin Bot A in Guild A."""
    value = os.environ.get("DISCORD_TEST_ROLE_A_ID", "")
    if not value:
        pytest.fail(
            "DISCORD_TEST_ROLE_A_ID not set — see TESTING.md 'Role-Based Signup E2E Test Roles'"
        )
    return value


@pytest.fixture(scope="session")
def role_b_id() -> str:
    """Discord role ID NOT held by Admin Bot A in Guild A."""
    value = os.environ.get("DISCORD_TEST_ROLE_B_ID", "")
    if not value:
        pytest.fail(
            "DISCORD_TEST_ROLE_B_ID not set — see TESTING.md 'Role-Based Signup E2E Test Roles'"
        )
    return value


# ---------------------------------------------------------------------------
# Parametrize cases
# ---------------------------------------------------------------------------
# priority_role_ids_factory receives (role_a_id, role_b_id) and returns the
# list to store on the template.  Admin Bot A holds role_a but NOT role_b.

_CASES = [
    pytest.param(
        lambda a, b: [a, b],
        ParticipantType.ROLE_MATCHED,
        0,
        id="bot_has_role_at_index_0",
    ),
    pytest.param(
        lambda a, b: [b, a],
        ParticipantType.ROLE_MATCHED,
        1,
        id="bot_has_role_at_index_1",
    ),
    pytest.param(
        lambda a, b: [b],
        ParticipantType.SELF_ADDED,
        0,
        id="bot_has_no_matching_role",
    ),
    pytest.param(
        lambda a, b: [],
        ParticipantType.SELF_ADDED,
        0,
        id="template_priority_roles_empty",
    ),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _create_role_based_template(
    admin_db,
    discord_guild_id: str,
    priority_role_ids: list[str],
) -> str:
    """Insert a ROLE_BASED game template and return its UUID string."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Guild {discord_guild_id} not found in DB"
    guild_db_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM channel_configurations WHERE guild_id = :guild_id LIMIT 1"),
        {"guild_id": guild_db_id},
    )
    row = result.fetchone()
    assert row, f"No channel found for guild {guild_db_id}"
    channel_db_id = row[0]

    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=guild_db_id,
        channel_id=channel_db_id,
        name="E2E Role-Based Test Template",
        description="Auto-created by role-based signup E2E tests",
        order=0,
        is_default=False,
        max_players=4,
        allowed_host_role_ids=[],
        signup_priority_role_ids=priority_role_ids if priority_role_ids else None,
    )
    admin_db.add(template)
    await admin_db.commit()
    return str(template.id)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("priority_roles_factory", "expected_position_type", "expected_position"),
    _CASES,
)
async def test_role_based_join_stores_correct_position(
    priority_roles_factory,
    expected_position_type: ParticipantType,
    expected_position: int,
    authenticated_admin_client,
    admin_db,
    discord_guild_id,
    synced_guild,
    role_a_id,
    role_b_id,
):
    """Join via API stores correct position_type and position based on role priority.

    Uses Admin Bot A as the joining user.  Admin Bot A holds role_a but NOT role_b.
    Template is configured with ROLE_BASED signup method and the appropriate
    priority_role_ids for each parametrized case.
    """
    priority_role_ids = priority_roles_factory(role_a_id, role_b_id)

    template_id = await _create_role_based_template(admin_db, discord_guild_id, priority_role_ids)

    try:
        game_data = {
            "template_id": template_id,
            "title": f"E2E Role Test {uuid.uuid4().hex[:8]}",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "signup_method": SignupMethod.ROLE_BASED.value,
        }

        create_resp = await authenticated_admin_client.post("/api/v1/games", data=game_data)
        assert create_resp.status_code == 201, f"Failed to create game: {create_resp.text}"
        game_id = create_resp.json()["id"]

        join_resp = await authenticated_admin_client.post(f"/api/v1/games/{game_id}/join")
        assert join_resp.status_code == 200, f"Failed to join game: {join_resp.text}"

        participant = join_resp.json()
        assert participant["position_type"] == expected_position_type, (
            f"Expected position_type={expected_position_type}, got {participant['position_type']}"
        )
        assert participant["position"] == expected_position, (
            f"Expected position={expected_position}, got {participant['position']}"
        )

        # Confirm the DB row matches the API response
        admin_db.expire_all()
        result = await admin_db.execute(
            text(
                "SELECT position_type, position FROM game_participants "
                "WHERE game_session_id = :game_id"
            ),
            {"game_id": game_id},
        )
        db_row = result.fetchone()
        assert db_row is not None, "Participant row not found in DB"
        assert db_row[0] == expected_position_type, (
            f"DB position_type={db_row[0]} does not match expected {expected_position_type}"
        )
        assert db_row[1] == expected_position, (
            f"DB position={db_row[1]} does not match expected {expected_position}"
        )

    finally:
        # Clean up game sessions and template created by this test case
        await admin_db.execute(
            text("DELETE FROM game_sessions WHERE template_id = :id"),
            {"id": template_id},
        )
        await admin_db.execute(
            text("DELETE FROM game_templates WHERE id = :id"),
            {"id": template_id},
        )
        await admin_db.commit()
