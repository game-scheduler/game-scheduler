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


"""add template system

Revision ID: 019_add_template_system
Revises: 018_remove_inheritance
Create Date: 2025-12-02 00:00:00.000000

Add game template system to replace inheritance-based configuration.
Templates represent game types with locked and pre-populated settings.

Changes:
- Create game_templates table with all fields
- Add indexes for templates (guild_id, guild_order, guild_default)
- Add template_id FK to game_sessions
- Add allowed_player_role_ids to game_sessions
- Add check constraint for template order >= 0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "019_add_template_system"
down_revision: str | None = "018_remove_inheritance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add template system tables and fields."""
    # Create game_templates table
    op.create_table(
        "game_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "guild_id",
            sa.String(36),
            sa.ForeignKey("guild_configurations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        # Locked fields
        sa.Column(
            "channel_id",
            sa.String(36),
            sa.ForeignKey("channel_configurations.id"),
            nullable=False,
        ),
        sa.Column("notify_role_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("allowed_player_role_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("allowed_host_role_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        # Pre-populated fields
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("expected_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("reminder_minutes", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("where", sa.Text(), nullable=True),
        sa.Column("signup_instructions", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Check constraint for order
        sa.CheckConstraint('"order" >= 0', name="ck_template_order_positive"),
    )

    # Create indexes for templates
    op.create_index("ix_game_templates_guild_id", "game_templates", ["guild_id"])
    op.create_index("ix_game_templates_guild_order", "game_templates", ["guild_id", "order"])
    op.create_index("ix_game_templates_guild_default", "game_templates", ["guild_id", "is_default"])

    # Add template_id and allowed_player_role_ids to game_sessions
    op.add_column(
        "game_sessions",
        sa.Column(
            "template_id",
            sa.String(36),
            sa.ForeignKey("game_templates.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "game_sessions",
        sa.Column("allowed_player_role_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_game_sessions_template_id", "game_sessions", ["template_id"])


def downgrade() -> None:
    """Remove template system tables and fields."""
    # Remove template_id from game_sessions
    op.drop_index("ix_game_sessions_template_id", "game_sessions")
    op.drop_column("game_sessions", "allowed_player_role_ids")
    op.drop_column("game_sessions", "template_id")

    # Remove game_templates table
    op.drop_index("ix_game_templates_guild_default", "game_templates")
    op.drop_index("ix_game_templates_guild_order", "game_templates")
    op.drop_index("ix_game_templates_guild_id", "game_templates")
    op.drop_table("game_templates")
