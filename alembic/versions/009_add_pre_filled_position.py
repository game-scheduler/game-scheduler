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


"""Add pre_filled_position field to game_participants

Revision ID: 009_add_pre_filled_position
Revises: 008_remove_rules_field
Create Date: 2025-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_add_pre_filled_position"
down_revision: str | None = "008_remove_rules_field"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pre_filled_position field and migrate existing pre-populated participants."""
    # Add the pre_filled_position column (nullable)
    op.add_column(
        "game_participants", sa.Column("pre_filled_position", sa.Integer(), nullable=True)
    )

    # Migrate existing pre-populated participants to have positions
    # Calculate positions based on joined_at timestamp within each game
    op.execute("""
        WITH numbered_participants AS (
            SELECT 
                id,
                ROW_NUMBER() OVER (PARTITION BY game_session_id ORDER BY joined_at) as position
            FROM game_participants
            WHERE is_pre_populated = true
        )
        UPDATE game_participants
        SET pre_filled_position = numbered_participants.position
        FROM numbered_participants
        WHERE game_participants.id = numbered_participants.id
    """)


def downgrade() -> None:
    """Remove pre_filled_position field."""
    op.drop_column("game_participants", "pre_filled_position")
