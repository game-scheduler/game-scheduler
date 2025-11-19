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


"""Task to send game reminder notifications to participants."""

import logging
import uuid

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.scheduler.celery_app import app
from services.scheduler.services import notification_service as notif_service
from shared import database
from shared.models import game, user

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task with async support."""

    def __call__(self, *args, **kwargs):
        """Execute task synchronously wrapping async function."""
        import asyncio

        return asyncio.run(self.run_async(*args, **kwargs))

    async def run_async(self, *args, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError


@app.task(base=AsyncTask, bind=True, max_retries=3)
class SendGameNotificationTask(AsyncTask):
    """Send notification to user about upcoming game."""

    async def run_async(self, game_id_str: str, user_id_str: str, reminder_minutes: int):
        """
        Send notification to user about their game.

        Args:
            game_id_str: Game session UUID as string
            user_id_str: User UUID as string
            reminder_minutes: Minutes before game this reminder is for
        """
        game_id = uuid.UUID(game_id_str)
        user_id = uuid.UUID(user_id_str)

        logger.info(
            f"Sending notification to user {user_id} for game {game_id} "
            f"({reminder_minutes} min before)"
        )

        async with database.get_db_session() as db:
            try:
                game_session = await self._get_game(db, game_id)
                if not game_session:
                    logger.error(f"Game {game_id} not found")
                    return {"status": "error", "reason": "game_not_found"}

                if game_session.status != "SCHEDULED":
                    logger.info(
                        f"Game {game_id} status is {game_session.status}, skipping notification"
                    )
                    return {"status": "skipped", "reason": "game_not_scheduled"}

                user_record = await self._get_user(db, user_id)
                if not user_record:
                    logger.error(f"User {user_id} not found")
                    return {"status": "error", "reason": "user_not_found"}

                notification_srv = await notif_service.get_notification_service()

                game_time_unix = int(game_session.scheduled_at.timestamp())

                success = await notification_srv.send_game_reminder(
                    game_id=game_id,
                    user_id=user_id,
                    game_title=game_session.title,
                    game_time_unix=game_time_unix,
                    reminder_minutes=reminder_minutes,
                )

                if success:
                    logger.info(
                        f"Successfully sent notification to user {user_id} for game {game_id}"
                    )
                    return {"status": "success"}
                else:
                    logger.error(
                        f"Failed to send notification to user {user_id} for game {game_id}"
                    )
                    raise Exception("Failed to publish notification event")

            except Exception as e:
                logger.error(
                    f"Error sending notification to user {user_id} for game {game_id}: {e}"
                )
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=e, countdown=60 * (self.request.retries + 1)) from e
                return {"status": "error", "reason": str(e)}

    async def _get_game(self, db: AsyncSession, game_id: uuid.UUID) -> game.GameSession | None:
        """Get game session by ID."""
        stmt = select(game.GameSession).where(game.GameSession.id == game_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user(self, db: AsyncSession, user_id: uuid.UUID) -> user.User | None:
        """Get user by ID."""
        stmt = select(user.User).where(user.User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


send_game_notification = SendGameNotificationTask()
