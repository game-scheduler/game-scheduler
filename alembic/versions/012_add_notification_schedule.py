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


"""Add notification_schedule table with PostgreSQL LISTEN/NOTIFY trigger

Revision ID: 012_add_notification_schedule
Revises: 011_add_duration
Create Date: 2025-11-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "012_add_notification_schedule"
down_revision: str | None = "011_add_duration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create notification_schedule table with indexes and PostgreSQL trigger.

    The notification_schedule table stores pre-calculated notification times
    for game reminders, enabling the notification daemon to use an efficient
    MIN() query pattern instead of polling all games.

    The PostgreSQL trigger sends LISTEN/NOTIFY events when schedule changes,
    allowing the daemon to wake up immediately for near-term notifications.
    """
    op.create_table(
        "notification_schedule",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("game_id", sa.String(36), nullable=False),
        sa.Column("reminder_minutes", sa.Integer(), nullable=False),
        sa.Column("notification_time", sa.DateTime(), nullable=False),
        sa.Column(
            "sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["game_sessions.id"],
            name="fk_notification_schedule_game_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "game_id",
            "reminder_minutes",
            name="uq_notification_schedule_game_reminder",
        ),
    )

    op.create_index(
        "idx_notification_schedule_next_due",
        "notification_schedule",
        ["notification_time"],
        postgresql_where=sa.text("sent = false"),
    )

    op.create_index(
        "idx_notification_schedule_game_id",
        "notification_schedule",
        ["game_id"],
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_schedule_changed()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only notify if change affects near-term schedule (within 10 minutes)
            -- This reduces noise for distant future notifications
            IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND
               NEW.notification_time <= NOW() + INTERVAL '10 minutes' AND
               NEW.sent = FALSE THEN
                PERFORM pg_notify(
                    'notification_schedule_changed',
                    json_build_object(
                        'operation', TG_OP,
                        'game_id', NEW.game_id::text,
                        'notification_time', NEW.notification_time::text
                    )::text
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER notification_schedule_trigger
        AFTER INSERT OR UPDATE OR DELETE ON notification_schedule
        FOR EACH ROW
        EXECUTE FUNCTION notify_schedule_changed();
        """
    )


def downgrade() -> None:
    """Remove notification_schedule table, trigger, and function."""
    op.execute("DROP TRIGGER IF EXISTS notification_schedule_trigger ON notification_schedule;")
    op.execute("DROP FUNCTION IF EXISTS notify_schedule_changed();")
    op.drop_index("idx_notification_schedule_game_id", table_name="notification_schedule")
    op.drop_index("idx_notification_schedule_next_due", table_name="notification_schedule")
    op.drop_table("notification_schedule")
