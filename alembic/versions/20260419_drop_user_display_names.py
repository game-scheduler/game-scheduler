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


"""drop_user_display_names

Display names are now read directly from the Redis member projection written by
the bot gateway events. The user_display_names DB table is no longer written to
or read from by any code path.

Revision ID: 20260419_drop_user_display_names
Revises: 20260414_add_user_display_names
Create Date: 2026-04-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260419_drop_user_display_names"
down_revision: str | None = "20260414_add_user_display_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop user_display_names table — replaced by Redis member projection."""
    op.drop_index("idx_user_display_names_updated_at", table_name="user_display_names")
    op.drop_table("user_display_names")


def downgrade() -> None:
    """Recreate user_display_names table if rolling back."""
    op.create_table(
        "user_display_names",
        sa.Column("user_discord_id", sa.String(20), nullable=False),
        sa.Column("guild_discord_id", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_discord_id", "guild_discord_id"),
    )
    op.create_index(
        "idx_user_display_names_updated_at",
        "user_display_names",
        ["updated_at"],
    )
