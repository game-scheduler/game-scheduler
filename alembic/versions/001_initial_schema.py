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


"""Initial database schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("discord_id", sa.String(20), nullable=False, unique=True),
        sa.Column("notification_preferences", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_discord_id", "users", ["discord_id"])

    # Create guild_configurations table
    op.create_table(
        "guild_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("guild_id", sa.String(20), nullable=False, unique=True),
        sa.Column("guild_name", sa.String(100), nullable=False),
        sa.Column("default_max_players", sa.Integer(), nullable=True),
        sa.Column("default_reminder_minutes", sa.JSON(), nullable=False, server_default="[60, 15]"),
        sa.Column("default_rules", sa.Text(), nullable=True),
        sa.Column("allowed_host_role_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("require_host_role", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_guild_configurations_guild_id", "guild_configurations", ["guild_id"])

    # Create channel_configurations table
    op.create_table(
        "channel_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "guild_id",
            sa.String(36),
            sa.ForeignKey("guild_configurations.id"),
            nullable=False,
        ),
        sa.Column("channel_id", sa.String(20), nullable=False, unique=True),
        sa.Column("channel_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("reminder_minutes", sa.JSON(), nullable=True),
        sa.Column("default_rules", sa.Text(), nullable=True),
        sa.Column("allowed_host_role_ids", sa.JSON(), nullable=True),
        sa.Column("game_category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_channel_configurations_channel_id", "channel_configurations", ["channel_id"]
    )

    # Create game_sessions table
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column(
            "guild_id",
            sa.String(36),
            sa.ForeignKey("guild_configurations.id"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.String(36),
            sa.ForeignKey("channel_configurations.id"),
            nullable=False,
        ),
        sa.Column("message_id", sa.String(20), nullable=True),
        sa.Column("host_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rules", sa.Text(), nullable=True),
        sa.Column("reminder_minutes", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_game_sessions_status", "game_sessions", ["status"])
    op.create_index("ix_game_sessions_created_at", "game_sessions", ["created_at"])

    # Create game_participants table
    op.create_table(
        "game_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "game_session_id",
            sa.String(36),
            sa.ForeignKey("game_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="JOINED"),
        sa.Column("is_pre_populated", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND display_name IS NULL) OR "
            "(user_id IS NULL AND display_name IS NOT NULL)",
            name="participant_identity_check",
        ),
    )
    op.create_index(
        "ix_game_participants_game_session_id", "game_participants", ["game_session_id"]
    )
    op.create_index("ix_game_participants_user_id", "game_participants", ["user_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("game_participants")
    op.drop_table("game_sessions")
    op.drop_table("channel_configurations")
    op.drop_table("guild_configurations")
    op.drop_table("users")
