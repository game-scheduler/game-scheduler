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


"""Add game_status_schedule table with PostgreSQL LISTEN/NOTIFY trigger

Revision ID: 020_add_game_status_schedule
Revises: 019_add_template_system
Create Date: 2025-12-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "020_add_game_status_schedule"
down_revision: str | None = "019_add_template_system"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create game_status_schedule table with indexes and PostgreSQL trigger.

    The game_status_schedule table stores scheduled status transitions for games,
    enabling the status_transition_daemon to use an efficient MIN() query pattern
    instead of polling all games.

    The PostgreSQL trigger sends LISTEN/NOTIFY events when schedule changes,
    allowing the daemon to wake up immediately for near-term transitions.
    """
    op.create_table(
        "game_status_schedule",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("game_id", sa.String(36), nullable=False),
        sa.Column("target_status", sa.String(20), nullable=False),
        sa.Column("transition_time", sa.DateTime(), nullable=False),
        sa.Column(
            "executed",
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
            name="fk_game_status_schedule_game_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "game_id",
            "target_status",
            name="uq_game_status_schedule_game_target",
        ),
    )

    op.create_index(
        "idx_game_status_schedule_next_due",
        "game_status_schedule",
        ["transition_time"],
        postgresql_where=sa.text("executed = false"),
    )

    op.create_index(
        "idx_game_status_schedule_game_id",
        "game_status_schedule",
        ["game_id"],
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_game_status_schedule_changed()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Always notify on INSERT/UPDATE/DELETE so daemon can wake immediately
            -- This enables true event-driven architecture without polling
            IF TG_OP = 'DELETE' THEN
                PERFORM pg_notify(
                    'game_status_schedule_changed',
                    json_build_object(
                        'operation', TG_OP,
                        'schedule_id', OLD.id::text,
                        'game_id', OLD.game_id::text
                    )::text
                );
                RETURN OLD;
            ELSE
                -- INSERT or UPDATE
                IF NEW.executed = FALSE THEN
                    PERFORM pg_notify(
                        'game_status_schedule_changed',
                        json_build_object(
                            'operation', TG_OP,
                            'schedule_id', NEW.id::text,
                            'game_id', NEW.game_id::text,
                            'transition_time', NEW.transition_time::text
                        )::text
                    );
                END IF;
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER game_status_schedule_trigger
        AFTER INSERT OR UPDATE OR DELETE ON game_status_schedule
        FOR EACH ROW
        EXECUTE FUNCTION notify_game_status_schedule_changed();
        """
    )


def downgrade() -> None:
    """Remove game_status_schedule table, trigger, and function."""
    op.execute("DROP TRIGGER IF EXISTS game_status_schedule_trigger ON game_status_schedule;")
    op.execute("DROP FUNCTION IF EXISTS notify_game_status_schedule_changed();")
    op.drop_index("idx_game_status_schedule_game_id", table_name="game_status_schedule")
    op.drop_index("idx_game_status_schedule_next_due", table_name="game_status_schedule")
    op.drop_table("game_status_schedule")
