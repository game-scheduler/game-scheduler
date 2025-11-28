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
Database queries for notification schedule management.

Provides synchronous query functions for the notification daemon to
retrieve and update notification schedule records.
"""

import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from shared.models import NotificationSchedule

logger = logging.getLogger(__name__)


def get_next_due_notification(db: Session) -> NotificationSchedule | None:
    """
    Get the next notification due to be sent.

    Queries MIN(notification_time) using optimized partial index for O(1)
    performance regardless of total scheduled notifications.

    Returns unsent notifications regardless of whether notification_time is
    in the past, allowing recovery from daemon downtime. The consumer decides
    whether to act on overdue notifications.

    Args:
        db: Synchronous database session

    Returns:
        NotificationSchedule record with earliest notification_time, or None
    """
    stmt = (
        select(NotificationSchedule)
        .where(NotificationSchedule.sent == False)  # noqa: E712
        .order_by(NotificationSchedule.notification_time.asc())
        .limit(1)
    )

    result = db.execute(stmt)
    notification = result.scalar_one_or_none()

    if notification:
        logger.debug(
            f"Next notification due at {notification.notification_time} "
            f"for game {notification.game_id}"
        )

    return notification


def mark_notification_sent(db: Session, notification_id: str) -> bool:
    """
    Mark notification as sent.

    Args:
        db: Synchronous database session
        notification_id: ID of notification to mark as sent

    Returns:
        True if notification was updated, False otherwise
    """
    stmt = (
        update(NotificationSchedule)
        .where(NotificationSchedule.id == notification_id)
        .values(sent=True)
    )

    result = db.execute(stmt)
    db.flush()
    # Result from execute() with UPDATE has rowcount in SQLAlchemy 2.x
    updated = result.rowcount > 0  # type: ignore[attr-defined]

    if updated:
        logger.debug(f"Marked notification {notification_id} as sent")
    else:
        logger.warning(f"Failed to mark notification {notification_id} as sent")

    return updated
