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


"""Backup test: create one game and record its IDs.

run-backup-tests.sh invokes this test file twice:
  Phase 1 — with GAME_RECORD_FILE=$GAME_A_FILE  (before the backup)
  Phase 2 — with GAME_RECORD_FILE=$GAME_B_FILE  (after the backup)

Each run creates one game with a unique title, waits for the Discord embed, and
writes "<game_id>:<channel_id>:<message_id>" to GAME_RECORD_FILE.

test_backup_post_restore.py reads both files to assert DB presence/absence and
Discord embed deletion.
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import wait_for_game_message_id

pytestmark = pytest.mark.backup


def _write_record(path: str, game_id: str, channel_id: str, message_id: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{game_id}:{channel_id}:{message_id}")


@pytest.mark.asyncio
async def test_create_game_and_record(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    synced_guild,
    discord_channel_id,
):
    """
    Create one game, wait for its Discord embed, and persist the IDs.

    GAME_RECORD_FILE must be set by the caller (run-backup-tests.sh).
    The file receives "<game_id>:<channel_id>:<message_id>" for later assertions.
    """
    record_file = os.environ.get("GAME_RECORD_FILE")
    assert record_file, "GAME_RECORD_FILE env var must be set by run-backup-tests.sh"

    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": synced_guild.discord_id},
    )
    row = result.fetchone()
    assert row, f"Guild {synced_guild.discord_id} not found in DB"
    guild_db_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_db_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {guild_db_id}"
    template_id = row[0]

    game_title = f"BackupGame-{uuid4().hex[:8]}"
    game_data = {
        "template_id": template_id,
        "title": game_title,
        "description": "Backup test game",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "max_players": "4",
        "where": "Test Location",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(admin_db, game_id, timeout=30)
    assert message_id is not None, "message_id should be populated after announcement"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord embed should be visible"

    _write_record(record_file, game_id, discord_channel_id, message_id)
    print(f"\n[backup] game created: id={game_id}, message_id={message_id}, record={record_file}")
