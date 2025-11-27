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

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.scheduler.celery_app import app
from services.scheduler.services import notification_service as notif_service
from shared import database
from shared.models import game, user

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    name="services.scheduler.tasks.send_notification.send_game_notification",
)
def send_game_notification(self, game_id_str: str, user_id_str: str, reminder_minutes: int):
    """
    Send notification to user about upcoming game.

    Args:
        game_id_str: Game session UUID as string
        user_id_str: User UUID as string
        reminder_minutes: Minutes before game this reminder is for
    """
    game_id = uuid.UUID(game_id_str)
    user_id = uuid.UUID(user_id_str)

    logger.info(
        f"=== Executing notification task: game={game_id}, user={user_id}, "
        f"reminder={reminder_minutes}min ==="
    )

    with database.get_sync_db_session() as db:
        try:
            game_session = _get_game(db, game_id)
            if not game_session:
                logger.error(f"Game {game_id} not found in database")
                return {"status": "error", "reason": "game_not_found"}

            if game_session.status != "SCHEDULED":
                logger.info(
                    f"Game {game_id} status is {game_session.status}, skipping notification"
                )
                return {"status": "skipped", "reason": "game_not_scheduled"}

            user_record = _get_user(db, user_id)
            if not user_record:
                logger.error(f"User {user_id} not found in database")
                return {"status": "error", "reason": "user_not_found"}

            logger.info(f"User found: discord_id={user_record.discord_id}")

            notification_srv = notif_service.get_notification_service()

            game_time_unix = int(game_session.scheduled_at.timestamp())
            logger.info(
                f"Publishing notification event: game_time_unix={game_time_unix}, "
                f"discord_id={user_record.discord_id}"
            )

            success = notification_srv.send_game_reminder(
                game_id=game_id,
                user_id=user_id,
                game_title=game_session.title,
                game_time_unix=game_time_unix,
                reminder_minutes=reminder_minutes,
            )

            if success:
                logger.info(
                    f"Successfully published notification event for user {user_id}, game {game_id}"
                )
                return {"status": "success"}
            else:
                logger.error(
                    f"Failed to publish notification event for user {user_id}, game {game_id}"
                )
                raise Exception("Failed to publish notification event")

        except Exception as e:
            logger.error(
                f"Error in notification task: game={game_id}, user={user_id}, error={e}",
                exc_info=True,
            )
            if self.request.retries < self.max_retries:
                retry_countdown = 60 * (self.request.retries + 1)
                logger.info(f"Retrying in {retry_countdown} seconds")
                raise self.retry(exc=e, countdown=retry_countdown) from e
            return {"status": "error", "reason": str(e)}


def _get_game(db: Session, game_id: uuid.UUID) -> game.GameSession | None:
    """Get game session by ID."""
    stmt = select(game.GameSession).where(game.GameSession.id == str(game_id))
    result = db.execute(stmt)
    return result.scalar_one_or_none()


def _get_user(db: Session, user_id: uuid.UUID) -> user.User | None:
    """Get user by ID."""
    stmt = select(user.User).where(user.User.id == str(user_id))
    result = db.execute(stmt)
    return result.scalar_one_or_none()
