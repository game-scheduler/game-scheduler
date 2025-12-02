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


"""remove channel_name column

Revision ID: 017_remove_channel_name
Revises: 016_remove_guild_name_column
Create Date: 2025-12-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017_remove_channel_name"
down_revision: str | None = "016_remove_guild_name_column"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove channel_name column from channel_configurations table."""
    op.drop_column("channel_configurations", "channel_name")


def downgrade() -> None:
    """Restore channel_name column as nullable (data cannot be restored)."""
    op.add_column(
        "channel_configurations",
        sa.Column("channel_name", sa.String(100), nullable=True),
    )
