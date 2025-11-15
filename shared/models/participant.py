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


"""Game participant model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .user import User


class ParticipantStatus(str, Enum):
    """Participant status in game session."""

    JOINED = "JOINED"
    DROPPED = "DROPPED"
    WAITLIST = "WAITLIST"
    PLACEHOLDER = "PLACEHOLDER"


class GameParticipant(Base):
    """
    Game session participant with support for placeholders.

    When userId is NULL, displayName must be set (placeholder entry).
    When userId is set, displayName should be NULL (resolved at render).
    """

    __tablename__ = "game_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(default=utc_now)
    status: Mapped[str] = mapped_column(String(20), default=ParticipantStatus.JOINED.value)
    is_pre_populated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    game: Mapped["GameSession"] = relationship("GameSession", back_populates="participants")
    user: Mapped["User | None"] = relationship("User", back_populates="participations")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND display_name IS NULL) OR "
            "(user_id IS NULL AND display_name IS NOT NULL)",
            name="participant_identity_check",
        ),
    )

    def __repr__(self) -> str:
        identity = f"user_id={self.user_id}" if self.user_id else f"placeholder={self.display_name}"
        return f"<GameParticipant(id={self.id}, {identity}, status={self.status})>"
