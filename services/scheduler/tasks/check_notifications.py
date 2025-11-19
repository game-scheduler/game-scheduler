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


"""Periodic task to check for upcoming games and schedule notifications."""

import datetime
import logging

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.scheduler.celery_app import app
from services.scheduler.utils import notification_windows
from shared import database
from shared.models import channel, game

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
class CheckUpcomingNotificationsTask(AsyncTask):
    """Check for games needing notifications and schedule delivery."""

    async def run_async(self, *args, **kwargs):
        """Check upcoming games and schedule notifications."""
        logger.info("Checking for upcoming game notifications")

        start_time, end_time = notification_windows.get_upcoming_games_window()

        async with database.get_db_session() as db:
            upcoming_games = await self._get_upcoming_games(db, start_time, end_time)

            notification_count = 0
            for game_session in upcoming_games:
                try:
                    notifications_sent = await self._schedule_game_notifications(db, game_session)
                    notification_count += notifications_sent
                    await db.commit()
                except Exception as e:
                    logger.error(
                        f"Failed to schedule notifications for game {game_session.id}: {e}"
                    )
                    await db.rollback()

            logger.info(
                f"Scheduled {notification_count} notifications for {len(upcoming_games)} games"
            )

        return {
            "games_checked": len(upcoming_games),
            "notifications_scheduled": notification_count,
        }

    async def _get_upcoming_games(
        self, db: AsyncSession, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> list[game.GameSession]:
        """Query games scheduled in the notification window."""
        stmt = (
            select(game.GameSession)
            .where(game.GameSession.scheduled_at >= start_time)
            .where(game.GameSession.scheduled_at <= end_time)
            .where(game.GameSession.status == "SCHEDULED")
            .options(
                selectinload(game.GameSession.participants),
                selectinload(game.GameSession.channel).selectinload(
                    channel.ChannelConfiguration.guild
                ),
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _schedule_game_notifications(
        self, db: AsyncSession, game_session: game.GameSession
    ) -> int:
        """Schedule notifications for a game using inherited reminder settings."""
        from services.scheduler.tasks import send_notification

        reminder_minutes = self._resolve_reminder_minutes(game_session)
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

        notification_count = 0

        for reminder_min in reminder_minutes:
            should_send, notification_time = notification_windows.should_send_notification(
                game_session.scheduled_at, reminder_min, now
            )

            if should_send:
                participants = [
                    p
                    for p in game_session.participants
                    if p.user_id is not None and p.status == "JOINED"
                ]

                for participant_record in participants:
                    notification_key = (
                        f"{game_session.id}_{participant_record.user_id}_{reminder_min}"
                    )

                    if not await self._notification_already_sent(db, notification_key):
                        send_notification.send_game_notification.apply_async(
                            args=[
                                str(game_session.id),
                                str(participant_record.user_id),
                                reminder_min,
                            ],
                            eta=notification_time,
                        )
                        await self._mark_notification_sent(db, notification_key)
                        notification_count += 1

        return notification_count

    def _resolve_reminder_minutes(self, game_session: game.GameSession) -> list[int]:
        """Resolve reminder minutes using game → channel → guild inheritance."""
        if game_session.reminder_minutes:
            return game_session.reminder_minutes

        if game_session.channel and game_session.channel.reminder_minutes:
            return game_session.channel.reminder_minutes

        if (
            game_session.channel
            and game_session.channel.guild
            and game_session.channel.guild.default_reminder_minutes
        ):
            return game_session.channel.guild.default_reminder_minutes

        return [60, 15]

    async def _notification_already_sent(self, db: AsyncSession, notification_key: str) -> bool:
        """Check if notification has already been sent."""
        from shared.cache import client as cache_client

        redis = await cache_client.get_redis_client()
        cache_key = f"notification_sent:{notification_key}"

        result = await redis.get(cache_key)
        return result is not None

    async def _mark_notification_sent(self, db: AsyncSession, notification_key: str) -> None:
        """Mark notification as sent to prevent duplicates."""
        from shared.cache import client as cache_client

        redis = await cache_client.get_redis_client()
        cache_key = f"notification_sent:{notification_key}"

        await redis.set(cache_key, "1", ttl=86400 * 7)  # 7 days


check_upcoming_notifications = CheckUpcomingNotificationsTask()
