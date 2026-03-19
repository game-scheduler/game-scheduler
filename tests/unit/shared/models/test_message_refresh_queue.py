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


"""Tests for MessageRefreshQueue model."""

from sqlalchemy import inspect

from shared.models import MessageRefreshQueue
from shared.models.base import utc_now


class TestMessageRefreshQueueModel:
    """Test suite for MessageRefreshQueue model."""

    def test_instantiate_with_required_fields(self):
        """Can instantiate with game_id and channel_id."""
        entry = MessageRefreshQueue(
            game_id="game-abc",
            channel_id="123456789012345678",
        )

        assert entry.game_id == "game-abc"
        assert entry.channel_id == "123456789012345678"

    def test_enqueued_at_can_be_set(self):
        """enqueued_at can be set explicitly."""
        now = utc_now()
        entry = MessageRefreshQueue(
            game_id="game-abc",
            channel_id="123456789012345678",
            enqueued_at=now,
        )

        assert entry.enqueued_at == now

    def test_tablename(self):
        """ORM model maps to the correct table name."""
        assert MessageRefreshQueue.__tablename__ == "message_refresh_queue"

    def test_column_types(self):
        """Column types match the composite-PK migration schema."""
        mapper = inspect(MessageRefreshQueue)
        columns = {c.key: c for c in mapper.mapper.column_attrs}

        assert "id" not in columns
        assert "game_id" in columns
        assert "channel_id" in columns
        assert "enqueued_at" in columns

    def test_primary_key_is_composite(self):
        """Primary key consists of channel_id and game_id (no surrogate id)."""
        mapper = inspect(MessageRefreshQueue)
        table = mapper.mapper.local_table
        pk_column_names = {col.name for col in table.primary_key.columns}

        assert pk_column_names == {"channel_id", "game_id"}

    def test_game_id_fk_target(self):
        """game_id foreign key references game_sessions.id with CASCADE delete."""
        mapper = inspect(MessageRefreshQueue)
        table = mapper.mapper.local_table
        fk_cols = {col.name: col for col in table.columns}

        fk = next(iter(fk_cols["game_id"].foreign_keys))
        assert fk.column.table.name == "game_sessions"
        assert fk.column.name == "id"
        assert fk.ondelete == "CASCADE"

    def test_channel_id_max_length(self):
        """channel_id column is String(20) matching Discord snowflake max length."""
        mapper = inspect(MessageRefreshQueue)
        table = mapper.mapper.local_table
        col = table.columns["channel_id"]

        assert col.type.length == 20
