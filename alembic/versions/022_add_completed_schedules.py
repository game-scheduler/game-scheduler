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


"""Add COMPLETED status schedules for existing IN_PROGRESS games

Revision ID: 022_add_completed_schedules
Revises: 021_add_game_scheduled_at_to_notification_schedule
Create Date: 2025-12-13

"""

from collections.abc import Sequence

from alembic import op

revision: str = "022_add_completed_schedules"
down_revision: str | None = "021_add_game_scheduled_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add COMPLETED status schedules for existing IN_PROGRESS games.

    This migration fixes games that only have IN_PROGRESS status schedules
    by adding COMPLETED schedules calculated as scheduled_at + 60 minutes (default).

    Games without expected_duration_minutes use DEFAULT_GAME_DURATION_MINUTES (60).
    This is idempotent - only creates schedules if they don't already exist.
    """
    # Add COMPLETED schedules for games that only have IN_PROGRESS schedules
    # Uses expected_duration_minutes if set, otherwise defaults to 60 minutes
    op.execute(
        """
        INSERT INTO game_status_schedule (id, game_id, target_status, transition_time, executed)
        SELECT
            gen_random_uuid()::text,
            gs.id,
            'COMPLETED',
            gs.scheduled_at + INTERVAL '1 minute' * COALESCE(gs.expected_duration_minutes, 60),
            FALSE
        FROM game_sessions gs
        WHERE gs.status IN ('SCHEDULED', 'IN_PROGRESS')
        AND NOT EXISTS (
            SELECT 1
            FROM game_status_schedule gss
            WHERE gss.game_id = gs.id
            AND gss.target_status = 'COMPLETED'
        )
        """
    )


def downgrade() -> None:
    """
    Remove COMPLETED status schedules added by this migration.

    This removes ALL COMPLETED schedules as we cannot differentiate between
    schedules created by this migration and those created normally.
    """
    op.execute(
        """
        DELETE FROM game_status_schedule
        WHERE target_status = 'COMPLETED'
        """
    )
