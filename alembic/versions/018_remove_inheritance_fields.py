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


"""remove inheritance fields

Revision ID: 018_remove_inheritance
Revises: 017_remove_channel_name
Create Date: 2025-12-02 00:00:00.000000

Remove settings inheritance system fields from guild and channel configurations.
These fields are being replaced with a template-based system.

Changes:
- Remove default_max_players from guild_configurations
- Remove default_reminder_minutes from guild_configurations
- Remove allowed_host_role_ids from guild_configurations
- Remove max_players from channel_configurations
- Remove reminder_minutes from channel_configurations
- Remove allowed_host_role_ids from channel_configurations
- Remove game_category from channel_configurations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018_remove_inheritance"
down_revision: str | None = "017_remove_channel_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove inheritance fields from guild and channel configurations."""
    # Remove guild inheritance fields
    op.drop_column("guild_configurations", "default_max_players")
    op.drop_column("guild_configurations", "default_reminder_minutes")
    op.drop_column("guild_configurations", "allowed_host_role_ids")

    # Remove channel inheritance fields
    op.drop_column("channel_configurations", "max_players")
    op.drop_column("channel_configurations", "reminder_minutes")
    op.drop_column("channel_configurations", "allowed_host_role_ids")
    op.drop_column("channel_configurations", "game_category")


def downgrade() -> None:
    """Restore inheritance fields to guild and channel configurations."""
    # Restore guild inheritance fields
    op.add_column(
        "guild_configurations", sa.Column("default_max_players", sa.Integer(), nullable=True)
    )
    op.add_column(
        "guild_configurations", sa.Column("default_reminder_minutes", sa.JSON(), nullable=True)
    )
    op.add_column(
        "guild_configurations", sa.Column("allowed_host_role_ids", sa.JSON(), nullable=True)
    )

    # Restore channel inheritance fields
    op.add_column("channel_configurations", sa.Column("max_players", sa.Integer(), nullable=True))
    op.add_column("channel_configurations", sa.Column("reminder_minutes", sa.JSON(), nullable=True))
    op.add_column(
        "channel_configurations", sa.Column("allowed_host_role_ids", sa.JSON(), nullable=True)
    )
    op.add_column(
        "channel_configurations", sa.Column("game_category", sa.String(50), nullable=True)
    )
