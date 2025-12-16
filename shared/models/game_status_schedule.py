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


"""Game status schedule model for database-backed status transition system."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession


class GameStatusSchedule(Base):
    """
    Scheduled status transitions for games.

    Each record represents one status transition to be executed at a specific time.
    The status_transition_daemon queries MIN(transition_time) to determine when
    to wake up next.
    """

    __tablename__ = "game_status_schedule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    target_status: Mapped[str] = mapped_column(String(20), nullable=False)
    transition_time: Mapped[datetime] = mapped_column(nullable=False)
    executed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())

    game: Mapped["GameSession"] = relationship("GameSession")

    __table_args__ = (
        UniqueConstraint("game_id", "target_status", name="uq_game_status_schedule_game_target"),
    )
