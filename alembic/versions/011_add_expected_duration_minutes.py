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


"""Add expected_duration_minutes field to game_sessions

Revision ID: 011_add_expected_duration_minutes
Revises: 14d77a523f0a
Create Date: 2025-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_add_duration"
down_revision: str | None = "14d77a523f0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add expected_duration_minutes column to game_sessions table."""
    op.add_column(
        "game_sessions",
        sa.Column("expected_duration_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove expected_duration_minutes column from game_sessions table."""
    op.drop_column("game_sessions", "expected_duration_minutes")
