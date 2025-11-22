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


"""add_min_players_field

Revision ID: 004_add_min_players_field
Revises: 003_remove_host_participant
Create Date: 2025-11-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_min_players_field"
down_revision: str | None = "003_remove_host_participant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add min_players field to game_sessions table.

    This migration adds a min_players column with NOT NULL constraint
    and default value of 1 to specify the minimum number of participants
    required for a game to proceed.
    """
    op.add_column(
        "game_sessions",
        sa.Column("min_players", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Remove min_players field from game_sessions table.

    This restores the previous schema without minimum player tracking.
    """
    op.drop_column("game_sessions", "min_players")
