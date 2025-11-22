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


"""Game session model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .guild import GuildConfiguration
    from .participant import GameParticipant
    from .user import User


class GameStatus(str, Enum):
    """Game session status."""

    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GameSession(Base):
    """
    Game session with scheduling and participant management.

    Settings inherit from channel and guild via resolution logic.
    """

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column()
    min_players: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"))
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_configurations.id"))
    message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    host_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    notify_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=GameStatus.SCHEDULED.value, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship("GuildConfiguration", back_populates="games")
    channel: Mapped["ChannelConfiguration"] = relationship(
        "ChannelConfiguration", back_populates="games"
    )
    host: Mapped["User"] = relationship("User", back_populates="hosted_games")
    participants: Mapped[list["GameParticipant"]] = relationship(
        "GameParticipant", back_populates="game"
    )

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, title={self.title}, status={self.status})>"
