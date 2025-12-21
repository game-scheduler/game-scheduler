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


"""add_game_image_storage

Revision ID: 3aeec3d09d7c
Revises: 790845a2735f
Create Date: 2025-12-20 16:07:39.565834

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3aeec3d09d7c"
down_revision: str | None = "790845a2735f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("thumbnail_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("thumbnail_mime_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("image_mime_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("game_sessions", "image_mime_type")
    op.drop_column("game_sessions", "image_data")
    op.drop_column("game_sessions", "thumbnail_mime_type")
    op.drop_column("game_sessions", "thumbnail_data")
