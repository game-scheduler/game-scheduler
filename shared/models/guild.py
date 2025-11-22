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


"""Guild configuration model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .game import GameSession


class GuildConfiguration(Base):
    """
    Discord guild (server) configuration with default settings.

    Settings cascade to channels and games via inheritance hierarchy.
    """

    __tablename__ = "guild_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    default_max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_reminder_minutes: Mapped[list[int]] = mapped_column(JSON, default=lambda: [60, 15])
    allowed_host_role_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    bot_manager_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    require_host_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    channels: Mapped[list["ChannelConfiguration"]] = relationship(
        "ChannelConfiguration", back_populates="guild"
    )
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="guild")

    def __repr__(self) -> str:
        return f"<GuildConfiguration(id={self.id}, guild_id={self.guild_id})>"
