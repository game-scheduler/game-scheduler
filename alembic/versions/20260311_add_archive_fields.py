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


"""add_archive_fields

Revision ID: a7c1e3b4f9c2
Revises: f3a2c1d8e9b7
Create Date: 2026-03-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1e3b4f9c2"
down_revision: str | None = "f3a2c1d8e9b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add archive fields to templates and sessions."""
    op.add_column(
        "game_templates",
        sa.Column("archive_delay_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "game_templates",
        sa.Column("archive_channel_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_templates_archive_channel_id",
        "game_templates",
        "channel_configurations",
        ["archive_channel_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "game_sessions",
        sa.Column("archive_delay_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("archive_channel_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_sessions_archive_channel_id",
        "game_sessions",
        "channel_configurations",
        ["archive_channel_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove archive fields from templates and sessions."""
    op.drop_constraint(
        "fk_game_sessions_archive_channel_id",
        "game_sessions",
    )
    op.drop_column("game_sessions", "archive_channel_id")
    op.drop_column("game_sessions", "archive_delay_seconds")

    op.drop_constraint(
        "fk_game_templates_archive_channel_id",
        "game_templates",
    )
    op.drop_column("game_templates", "archive_channel_id")
    op.drop_column("game_templates", "archive_delay_seconds")
