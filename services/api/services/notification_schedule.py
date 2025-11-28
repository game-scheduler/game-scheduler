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


"""Notification schedule management for game sessions.

Handles population, updates, and cleanup of notification_schedule table.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import game as game_model
from shared.models import notification_schedule as notification_schedule_model

logger = logging.getLogger(__name__)


class NotificationScheduleService:
    """Service for managing notification schedules."""

    def __init__(self, db: AsyncSession):
        """
        Initialize notification schedule service.

        Args:
            db: Database session
        """
        self.db = db

    async def populate_schedule(
        self,
        game: game_model.GameSession,
        reminder_minutes: list[int],
    ) -> None:
        """
        Populate notification schedule for a game session.

        Creates notification_schedule records for each reminder time that
        falls in the future. PostgreSQL trigger automatically sends NOTIFY.

        Args:
            game: Game session to schedule notifications for
            reminder_minutes: List of reminder times in minutes before game
        """
        if not reminder_minutes:
            logger.info(f"No reminder minutes configured for game {game.id}")
            return

        now = datetime.now(UTC).replace(tzinfo=None)
        scheduled_at = game.scheduled_at

        for reminder_min in reminder_minutes:
            notification_time = scheduled_at - timedelta(minutes=reminder_min)

            if notification_time > now:
                schedule_entry = notification_schedule_model.NotificationSchedule(
                    game_id=game.id,
                    reminder_minutes=reminder_min,
                    notification_time=notification_time,
                    sent=False,
                )
                self.db.add(schedule_entry)
                logger.debug(
                    f"Scheduled notification for game {game.id} "
                    f"at {notification_time} ({reminder_min} min before)"
                )
            else:
                logger.debug(
                    f"Skipping past notification for game {game.id} "
                    f"at {notification_time} ({reminder_min} min before)"
                )

    async def update_schedule(
        self,
        game: game_model.GameSession,
        reminder_minutes: list[int],
    ) -> None:
        """
        Update notification schedule for a game session.

        Deletes existing schedule records and creates new ones based on
        current game.scheduled_at and reminder_minutes values.

        Args:
            game: Game session to update schedule for
            reminder_minutes: List of reminder times in minutes before game
        """
        # Delete existing schedule records
        await self.db.execute(
            delete(notification_schedule_model.NotificationSchedule).where(
                notification_schedule_model.NotificationSchedule.game_id == game.id
            )
        )
        logger.debug(f"Deleted existing schedule for game {game.id}")

        # Populate new schedule
        await self.populate_schedule(game, reminder_minutes)

    async def clear_schedule(self, game_id: str) -> None:
        """
        Clear all notification schedule records for a game.

        This is typically not needed since ON DELETE CASCADE handles cleanup,
        but provided for explicit cleanup if needed.

        Args:
            game_id: Game session UUID
        """
        await self.db.execute(
            delete(notification_schedule_model.NotificationSchedule).where(
                notification_schedule_model.NotificationSchedule.game_id == game_id
            )
        )
        logger.debug(f"Cleared schedule for game {game_id}")
