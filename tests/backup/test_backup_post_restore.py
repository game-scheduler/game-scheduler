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


"""Backup test Phases 3 and 4: post-restore assertions and cron test.

Phase 3 — after restore:
  - gameA (pre-backup) is present in DB by its exact game_id
  - gameB (post-backup) is absent from DB by its exact game_id
  - gameB's Discord embed has been deleted by the bot's orphaned-embed sweep

Phase 4 — cron test:
  - A backup container started with BACKUP_SCHEDULE=* * * * * runs backup-script.sh
  - Within 90 seconds a backup_metadata row appears in DB
  - slot-0.dump.gz is present in MinIO

Record file format (written by test_backup_create_game.py):
  "<game_id>:<channel_id>:<message_id>"
"""

import os

import boto3
import pytest
from botocore.exceptions import ClientError
from sqlalchemy import text

from tests.shared.polling import wait_for_db_condition_async

pytestmark = pytest.mark.backup

MINIO_ENDPOINT = os.environ.get("BACKUP_S3_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("BACKUP_S3_ACCESS_KEY_ID", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("BACKUP_S3_SECRET_ACCESS_KEY", "minioadmin")
S3_BUCKET = os.environ.get("BACKUP_S3_BUCKET", "test-backups")


def _read_record(env_var: str) -> tuple[str, str, str]:
    """Return (game_id, channel_id, message_id) from the record file at env_var."""
    path = os.environ.get(env_var)
    assert path, f"{env_var} env var must be set by run-backup-tests.sh"
    assert os.path.exists(path), f"{env_var} file {path!r} does not exist"
    with open(path, encoding="utf-8") as f:
        game_id, channel_id, message_id = f.read().strip().split(":")
    return game_id, channel_id, message_id


def _s3_client() -> boto3.client:
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


@pytest.mark.asyncio
async def test_game_a_present_and_game_b_absent_after_restore(admin_db):
    """
    Phase 3: gameA (pre-backup) present in DB; gameB (post-backup) absent.

    Uses exact game UUIDs from the record files rather than title matching.
    """
    game_a_id, _, _ = _read_record("GAME_A_RECORD_FILE")
    game_b_id, _, _ = _read_record("GAME_B_RECORD_FILE")

    result = await admin_db.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_a_id},
    )
    assert result.fetchone(), f"gameA {game_a_id} should be present in DB after restore"

    result = await admin_db.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_b_id},
    )
    assert result.fetchone() is None, f"gameB {game_b_id} should be absent from DB after restore"


@pytest.mark.asyncio
async def test_game_b_embed_deleted_after_restore(discord_helper):
    """
    Phase 4: gameB's Discord embed must have been deleted by the orphaned-embed sweep.
    """
    _, channel_id, message_id = _read_record("GAME_B_RECORD_FILE")

    await discord_helper.wait_for_message_deleted(
        channel_id=channel_id,
        message_id=message_id,
        timeout=60,
    )
    assert True  # wait_for_message_deleted raises on failure


@pytest.mark.asyncio
async def test_cron_backup_runs_within_90_seconds(admin_db):
    """
    Phase 4: cron test — backup-script.sh fires within 90 seconds.

    run-backup-tests.sh starts a temporary backup container with
    BACKUP_SCHEDULE=* * * * * before invoking this test.  We poll the DB for a
    new backup_metadata row and check MinIO for slot-0.dump.gz.

    The container starts fresh each run so SLOT_FILE is absent and slot 0 is
    always used.
    """
    await wait_for_db_condition_async(
        admin_db,
        "SELECT COUNT(*) FROM backup_metadata",
        {},
        lambda row: row[0] >= 1,
        timeout=90,
        interval=2.0,
        description="backup_metadata row after cron fire",
    )

    s3 = _s3_client()
    key = "backup/slot-0.dump.gz"
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as exc:
        msg = f"Expected {key} in MinIO bucket {S3_BUCKET} after cron backup, but got: {exc}"
        raise AssertionError(msg) from exc

    result = await admin_db.execute(
        text("SELECT backed_up_at FROM backup_metadata ORDER BY id DESC LIMIT 1")
    )
    row = result.fetchone()
    assert row is not None, "backup_metadata row missing after cron fire"
    assert row[0] is not None, "backed_up_at should be populated"
    print(f"\n[Phase 4] Cron backup confirmed: slot-0.dump.gz present, backed_up_at={row[0]}")
