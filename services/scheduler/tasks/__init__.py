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


"""Celery tasks for scheduler service."""

from services.scheduler.tasks.check_notifications import check_upcoming_notifications
from services.scheduler.tasks.send_notification import send_game_notification
from services.scheduler.tasks.update_game_status import update_game_statuses

__all__ = [
    "check_upcoming_notifications",
    "send_game_notification",
    "update_game_statuses",
]
