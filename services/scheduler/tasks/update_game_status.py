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


"""Task to update game statuses based on scheduled times."""

import datetime
import logging

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.scheduler.celery_app import app
from services.scheduler.utils import status_transitions
from shared import database
from shared.messaging import events, publisher
from shared.models import game

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


@app.task(base=AsyncTask, bind=True)
class UpdateGameStatusesTask(AsyncTask):
    """Update game statuses based on current time."""

    async def run_async(self, *args, **kwargs):
        """Check games and update statuses as needed."""
        logger.info("Checking for games needing status updates")

        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

        async with database.get_db_session() as db:
            try:
                started_count = await self._mark_games_in_progress(db, now)
                await db.commit()

                logger.info(f"Updated statuses: {started_count} games marked IN_PROGRESS")

                return {
                    "games_started": started_count,
                }

            except Exception as e:
                logger.error(f"Failed to update game statuses: {e}")
                await db.rollback()
                raise

    async def _mark_games_in_progress(
        self, db: AsyncSession, current_time: datetime.datetime
    ) -> int:
        """Mark games as IN_PROGRESS if their scheduled time has passed."""
        stmt = (
            select(game.GameSession)
            .where(game.GameSession.status == "SCHEDULED")
            .where(game.GameSession.scheduled_at <= current_time)
        )

        result = await db.execute(stmt)
        games_to_start = list(result.scalars().all())

        count = 0
        for game_session in games_to_start:
            if status_transitions.is_valid_transition(game_session.status, "IN_PROGRESS"):
                game_session.status = "IN_PROGRESS"
                game_session.updated_at = current_time

                await self._publish_game_started_event(game_session)
                count += 1

        return count

    async def _publish_game_started_event(self, game_session: game.GameSession) -> None:
        """Publish game.started event to notify other services."""
        event_pub = publisher.EventPublisher()

        try:
            await event_pub.connect()

            game_started_data = {
                "game_id": str(game_session.id),
                "title": game_session.title,
                "guild_id": game_session.guild.guild_id if game_session.guild else None,
                "channel_id": game_session.channel.channel_id if game_session.channel else None,
            }

            event_wrapper = events.Event(
                event_type=events.EventType.GAME_STARTED, data=game_started_data
            )

            await event_pub.publish(event_wrapper)

            logger.info(f"Published GAME_STARTED event for game {game_session.id}")

        except Exception as e:
            logger.error(f"Failed to publish GAME_STARTED event for game {game_session.id}: {e}")

        finally:
            await event_pub.close()


update_game_statuses = UpdateGameStatusesTask()
