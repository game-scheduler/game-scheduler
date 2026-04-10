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


"""End-to-end tests for embed deletion and sweep-triggered game cancellation.

Case 1: Real-time deletion
  DELETE the Discord announcement message via helper → bot's on_message_delete fires
  → EmbedDeletionConsumer removes the game row.

Case 2: Sweep-triggered deletion
  Corrupt game's message_id so Discord 404s on fetch, then POST /admin/sweep to force
  a sweep run → bot detects missing message → game row removed.

Requires:
- Full stack via compose.e2e.yaml
- Bot running with PYTEST_RUNNING=1 (exposes /admin/sweep on port 8089)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TimeoutType
from tests.e2e.conftest import GuildContext, wait_for_db_condition, wait_for_game_message_id

pytestmark = pytest.mark.e2e

_BOT_SWEEP_URL = "http://bot:8089/admin/sweep"
# Valid snowflake format (≤ 2^63-1) that will never exist in the test channel
_NONEXISTENT_MESSAGE_ID = "1000000000000000000"


@pytest.mark.asyncio
async def test_case1_real_time_deletion(
    authenticated_admin_client,
    admin_db: AsyncSession,
    discord_helper,
    discord_channel_id,
    synced_guild: GuildContext,
    test_timeouts,
):
    """
    E2E Case 1: Deleting the Discord announcement message removes the game row.

    Verifies the on_message_delete → EmbedDeletionConsumer path end-to-end:
    1. Create game via API
    2. Wait for bot to post announcement (message_id populated)
    3. Delete the Discord message via test helper (as admin bot)
    4. Assert game row removed from DB
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Embed Delete Case1 {uuid4().hex[:8]}"

    game_data = {
        "template_id": synced_guild.template_id,
        "title": game_title,
        "description": "Embed deletion real-time test",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None

    await discord_helper.delete_message(discord_channel_id, message_id)

    await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM game_sessions WHERE id = :id",
        {"id": game_id},
        lambda row: row[0] == 0,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description=f"game {game_id} removal after embed deletion",
    )


@pytest.mark.asyncio
async def test_case2_sweep_http_trigger(
    authenticated_admin_client,
    admin_db: AsyncSession,
    synced_guild: GuildContext,
    test_timeouts,
):
    """
    E2E Case 2: Corrupting message_id + POST /admin/sweep removes game row.

    Verifies the sweep path end-to-end:
    1. Create game via API
    2. Wait for bot to post announcement (message_id populated)
    3. Overwrite message_id with a non-existent snowflake
    4. POST /admin/sweep (blocks until sweep completes)
    5. Assert game row removed from DB
    """
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Embed Delete Case2 {uuid4().hex[:8]}"

    game_data = {
        "template_id": synced_guild.template_id,
        "title": game_title,
        "description": "Sweep HTTP trigger test",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    await wait_for_game_message_id(admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE])

    await admin_db.execute(
        text("UPDATE game_sessions SET message_id = :fake_id WHERE id = :id"),
        {"fake_id": _NONEXISTENT_MESSAGE_ID, "id": game_id},
    )
    await admin_db.commit()

    async with httpx.AsyncClient() as client:
        sweep_response = await client.post(_BOT_SWEEP_URL, timeout=60.0)
    assert sweep_response.status_code == 200, (
        f"POST /admin/sweep returned {sweep_response.status_code}"
    )

    await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM game_sessions WHERE id = :id",
        {"id": game_id},
        lambda row: row[0] == 0,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description=f"game {game_id} removal after sweep",
    )
