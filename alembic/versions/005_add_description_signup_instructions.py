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


"""Add description and signup_instructions fields to game_sessions

Revision ID: 005_desc_signup_instr
Revises: 004_add_min_players_field
Create Date: 2025-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_desc_signup_instr"
down_revision: str | None = "004_add_min_players_field"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add signup_instructions field and make description nullable."""
    # Make description nullable (existing field)
    op.alter_column("game_sessions", "description", existing_type=sa.Text(), nullable=True)

    # Add signup_instructions field (new field)
    op.add_column("game_sessions", sa.Column("signup_instructions", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove signup_instructions field and revert description to NOT NULL."""
    # Remove signup_instructions field
    op.drop_column("game_sessions", "signup_instructions")

    # Revert description to NOT NULL
    op.alter_column("game_sessions", "description", existing_type=sa.Text(), nullable=False)
