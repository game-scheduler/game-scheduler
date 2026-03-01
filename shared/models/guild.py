# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Guild configuration model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .game import GameSession
    from .template import GameTemplate


class GuildConfiguration(Base):
    """
    Discord guild (server) configuration.

    Manages bot access and template-based game types.
    """

    __tablename__ = "guild_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    bot_manager_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=func.now()
    )

    # Relationships
    channels: Mapped[list["ChannelConfiguration"]] = relationship(
        "ChannelConfiguration", back_populates="guild"
    )
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="guild")
    templates: Mapped[list["GameTemplate"]] = relationship("GameTemplate", back_populates="guild")

    def __repr__(self) -> str:
        return f"<GuildConfiguration(id={self.id}, guild_id={self.guild_id})>"
