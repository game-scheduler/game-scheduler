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


"""Remove rules field from all tables

Revision ID: 008_remove_rules_field
Revises: 007_notify_roles
Create Date: 2025-11-21 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_remove_rules_field"
down_revision = "007_notify_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove rules fields from game_sessions, guild_configurations, and channel_configurations."""
    op.drop_column("game_sessions", "rules")
    op.drop_column("guild_configurations", "default_rules")
    op.drop_column("channel_configurations", "default_rules")


def downgrade() -> None:
    """Restore rules fields to game_sessions, guild_configurations, and channel_configurations."""
    op.add_column(
        "game_sessions",
        sa.Column("rules", sa.Text(), nullable=True),
    )
    op.add_column(
        "guild_configurations",
        sa.Column("default_rules", sa.Text(), nullable=True),
    )
    op.add_column(
        "channel_configurations",
        sa.Column("default_rules", sa.Text(), nullable=True),
    )
