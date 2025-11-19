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


"""Scheduler service configuration."""

import os


class SchedulerConfig:
    """Configuration for scheduler service with Celery settings."""

    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/game_scheduler",
    )

    CELERY_BROKER_URL: str = RABBITMQ_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    CELERY_TASK_DEFAULT_RETRY_DELAY: int = 60
    CELERY_TASK_MAX_RETRIES: int = 3

    NOTIFICATION_CHECK_INTERVAL_SECONDS: int = 300  # 5 minutes
    STATUS_UPDATE_INTERVAL_SECONDS: int = 60  # 1 minute

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


_config = None


def get_config() -> SchedulerConfig:
    """Get singleton configuration instance."""
    global _config
    if _config is None:
        _config = SchedulerConfig()
    return _config
