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


"""Channel configuration model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .guild import GuildConfiguration


class ChannelConfiguration(Base):
    """
    Discord channel configuration with optional overrides.

    Settings override guild defaults and cascade to games.
    """

    __tablename__ = "channel_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"))
    channel_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    channel_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    allowed_host_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    game_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship(
        "GuildConfiguration", back_populates="channels"
    )
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="channel")

    def __repr__(self) -> str:
        return f"<ChannelConfiguration(id={self.id}, channel_name={self.channel_name})>"
