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


"""Add bot_manager_role_ids field to guild_configurations

Revision ID: 006_bot_mgr_roles
Revises: 005_desc_signup_instr
Create Date: 2025-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_bot_mgr_roles"
down_revision: str | None = "005_desc_signup_instr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add bot_manager_role_ids field to guild_configurations."""
    op.add_column(
        "guild_configurations",
        sa.Column("bot_manager_role_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove bot_manager_role_ids field from guild_configurations."""
    op.drop_column("guild_configurations", "bot_manager_role_ids")
