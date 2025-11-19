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


"""Celery application configuration."""

from celery import Celery

from services.scheduler import config as scheduler_config

config = scheduler_config.get_config()

app = Celery(
    "game_scheduler",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=[
        "services.scheduler.tasks.check_notifications",
        "services.scheduler.tasks.send_notification",
        "services.scheduler.tasks.update_game_status",
    ],
)

app.conf.update(
    task_serializer=config.CELERY_TASK_SERIALIZER,
    result_serializer=config.CELERY_RESULT_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,
    task_acks_late=config.CELERY_TASK_ACKS_LATE,
    worker_prefetch_multiplier=config.CELERY_WORKER_PREFETCH_MULTIPLIER,
    task_default_retry_delay=config.CELERY_TASK_DEFAULT_RETRY_DELAY,
    task_max_retries=config.CELERY_TASK_MAX_RETRIES,
    beat_schedule={
        "check-notifications-every-5-minutes": {
            "task": "services.scheduler.tasks.check_notifications.check_upcoming_notifications",
            "schedule": config.NOTIFICATION_CHECK_INTERVAL_SECONDS,
        },
        "update-game-status-every-minute": {
            "task": "services.scheduler.tasks.update_game_status.update_game_statuses",
            "schedule": config.STATUS_UPDATE_INTERVAL_SECONDS,
        },
    },
)

if __name__ == "__main__":
    app.start()
