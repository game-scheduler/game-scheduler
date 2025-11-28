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


"""Notification schedule model for database-backed notification system."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession


class NotificationSchedule(Base):
    """
    Pre-calculated notification times for scheduled games.

    Each record represents one notification to be sent at a specific time.
    The scheduler daemon queries MIN(notification_time) to determine when
    to wake up next.
    """

    __tablename__ = "notification_schedule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    reminder_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    notification_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    game: Mapped["GameSession"] = relationship("GameSession")

    __table_args__ = (
        UniqueConstraint(
            "game_id", "reminder_minutes", name="uq_notification_schedule_game_reminder"
        ),
    )
