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


"""add_notification_type_participant_id

Revision ID: bcecd82ff82f
Revises: c2135ff3d5cd
Create Date: 2025-12-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcecd82ff82f"
down_revision: str | None = "c2135ff3d5cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add notification_type and participant_id columns to notification_schedule.

    This extends the notification system to support both game-wide reminders
    and participant-specific notifications (e.g., join confirmations).
    """
    # Add notification_type column with default 'reminder' for backward compatibility
    op.add_column(
        "notification_schedule",
        sa.Column(
            "notification_type",
            sa.String(length=50),
            nullable=False,
            server_default="reminder",
        ),
    )

    # Add participant_id column (nullable, CASCADE delete when participant removed)
    op.add_column(
        "notification_schedule",
        sa.Column("participant_id", sa.String(length=36), nullable=True),
    )

    # Add foreign key constraint for participant_id
    op.create_foreign_key(
        "fk_notification_schedule_participant_id",
        "notification_schedule",
        "game_participants",
        ["participant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add index on participant_id for efficient lookups
    op.create_index(
        op.f("ix_notification_schedule_participant_id"),
        "notification_schedule",
        ["participant_id"],
        unique=False,
    )

    # Add composite index for efficient queries by type and time
    op.create_index(
        "ix_notification_schedule_type_time",
        "notification_schedule",
        ["notification_type", "notification_time"],
        unique=False,
    )


def downgrade() -> None:
    """Remove notification_type and participant_id columns."""
    # Drop indexes
    op.drop_index("ix_notification_schedule_type_time", table_name="notification_schedule")
    op.drop_index(
        op.f("ix_notification_schedule_participant_id"),
        table_name="notification_schedule",
    )

    # Drop foreign key constraint
    op.drop_constraint(
        "fk_notification_schedule_participant_id",
        "notification_schedule",
        type_="foreignkey",
    )

    # Drop columns
    op.drop_column("notification_schedule", "participant_id")
    op.drop_column("notification_schedule", "notification_type")
