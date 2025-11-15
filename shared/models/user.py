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


"""User model for Discord user integration."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .participant import GameParticipant


class User(Base):
    """
    Discord user model.

    Stores only discordId and application-specific data.
    Display names are never cached - always fetched at render time.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    discord_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    hosted_games: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="host", foreign_keys="GameSession.host_id"
    )
    participations: Mapped[list["GameParticipant"]] = relationship(
        "GameParticipant", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, discord_id={self.discord_id})>"
