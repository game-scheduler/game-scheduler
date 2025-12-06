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


"""
Event builder functions for generic scheduler daemon.

Each builder function constructs an Event object from a schedule
model instance for publishing to RabbitMQ.
"""

import logging
from uuid import UUID

from shared.messaging.events import Event, EventType, GameReminderDueEvent
from shared.models import GameStatusSchedule, NotificationSchedule
from shared.models.base import utc_now
from shared.schemas.events import GameStatusTransitionDueEvent

logger = logging.getLogger(__name__)


def build_game_reminder_event(notification: NotificationSchedule) -> tuple[Event, int | None]:
    """
    Build GAME_REMINDER_DUE event from notification schedule with per-message TTL.

    Args:
        notification: NotificationSchedule record

    Returns:
        Tuple of (Event, expiration_ms) where expiration_ms is milliseconds
        until game starts. If game has no scheduled_at or already started,
        returns minimal TTL.
    """
    event_data = GameReminderDueEvent(
        game_id=UUID(notification.game_id),
        reminder_minutes=notification.reminder_minutes,
    )

    event = Event(
        event_type=EventType.GAME_REMINDER_DUE,
        data=event_data.model_dump(),
    )

    expiration_ms = None
    if notification.game_scheduled_at:
        time_until_game = (notification.game_scheduled_at - utc_now()).total_seconds()

        if time_until_game > 60:
            expiration_ms = int(time_until_game * 1000)
            logger.debug(
                f"Notification TTL: {time_until_game:.0f}s until game starts "
                f"(game_id={notification.game_id})"
            )
        else:
            expiration_ms = 60000
            logger.warning(
                f"Game already started or starting soon, setting minimal TTL "
                f"(game_id={notification.game_id})"
            )

    return event, expiration_ms


def build_status_transition_event(transition: GameStatusSchedule) -> tuple[Event, None]:
    """
    Build GAME_STATUS_TRANSITION_DUE event from status schedule.

    Status transitions never expire - they must eventually succeed to
    maintain database consistency.

    Args:
        transition: GameStatusSchedule record

    Returns:
        Tuple of (Event, None) - status transitions have no TTL
    """
    event_data = GameStatusTransitionDueEvent(
        game_id=UUID(transition.game_id),
        target_status=transition.target_status,
        transition_time=transition.transition_time,
    )

    event = Event(
        event_type=EventType.GAME_STATUS_TRANSITION_DUE,
        data=event_data.model_dump(),
    )

    return event, None
