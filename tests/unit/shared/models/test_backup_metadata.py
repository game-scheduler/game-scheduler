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


"""Tests for BackupMetadata SQLAlchemy model."""

from datetime import UTC, datetime

import shared.models as models
from shared.models import BackupMetadata


def test_backup_metadata_maps_to_correct_table():
    """BackupMetadata maps to the backup_metadata table."""
    assert BackupMetadata.__tablename__ == "backup_metadata"


def test_backup_metadata_has_id_primary_key():
    """BackupMetadata has an integer id primary key."""
    columns = {c.name: c for c in BackupMetadata.__table__.columns}
    assert "id" in columns
    assert columns["id"].primary_key is True


def test_backup_metadata_has_backed_up_at_column():
    """BackupMetadata has a backed_up_at TIMESTAMPTZ NOT NULL column."""
    columns = {c.name: c for c in BackupMetadata.__table__.columns}
    assert "backed_up_at" in columns
    assert columns["backed_up_at"].nullable is False


def test_backup_metadata_can_be_instantiated():
    """BackupMetadata can be constructed with a backed_up_at timestamp."""
    ts = datetime(2026, 4, 8, 12, 0, 0, tzinfo=UTC)
    record = BackupMetadata(backed_up_at=ts)

    assert record.backed_up_at == ts


def test_backup_metadata_exported_from_shared_models():
    """BackupMetadata is accessible via shared.models.__all__."""
    assert "BackupMetadata" in models.__all__
