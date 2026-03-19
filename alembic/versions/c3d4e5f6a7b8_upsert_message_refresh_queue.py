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


"""upsert_message_refresh_queue

Revision ID: c3d4e5f6a7b8
Revises: b1d2e3f4a5c6
Create Date: 2026-03-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text as sql_text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b1d2e3f4a5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sql_text("DROP TRIGGER IF EXISTS message_refresh_queue_trigger ON message_refresh_queue")
    )

    op.drop_constraint("message_refresh_queue_pkey", "message_refresh_queue", type_="primary")
    op.drop_column("message_refresh_queue", "id")

    op.create_primary_key(
        "message_refresh_queue_pkey",
        "message_refresh_queue",
        ["channel_id", "game_id"],
    )

    # Fire on both INSERT and UPDATE so the upsert write path always triggers NOTIFY.
    op.execute(
        sql_text(
            """
        CREATE TRIGGER message_refresh_queue_trigger
        AFTER INSERT OR UPDATE ON message_refresh_queue
        FOR EACH ROW
        EXECUTE FUNCTION notify_message_refresh_queue_changed()
    """
        )
    )


def downgrade() -> None:
    op.execute(
        sql_text("DROP TRIGGER IF EXISTS message_refresh_queue_trigger ON message_refresh_queue")
    )

    op.drop_constraint("message_refresh_queue_pkey", "message_refresh_queue", type_="primary")

    op.add_column(
        "message_refresh_queue",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
    )
    op.execute(
        sql_text("UPDATE message_refresh_queue SET id = gen_random_uuid()::text WHERE id IS NULL")
    )
    op.alter_column("message_refresh_queue", "id", nullable=False)
    op.create_primary_key("message_refresh_queue_pkey", "message_refresh_queue", ["id"])

    op.execute(
        sql_text(
            """
        CREATE TRIGGER message_refresh_queue_trigger
        AFTER INSERT ON message_refresh_queue
        FOR EACH ROW
        EXECUTE FUNCTION notify_message_refresh_queue_changed()
    """
        )
    )
