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


"""Game template model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .game import GameSession
    from .guild import GuildConfiguration


class GameTemplate(Base):
    """
    Game template defines game type with locked and pre-populated settings.

    Templates are guild-scoped and represent game types (e.g., "D&D Campaign").
    Host selects template at game creation. Locked fields cannot be changed by host,
    while pre-populated fields provide defaults that host can edit.
    """

    __tablename__ = "game_templates"

    # Identity & Metadata
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=func.now()
    )

    # Locked Fields (manager-only, host cannot edit)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_configurations.id"))
    notify_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_player_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_host_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Pre-populated Fields (host-editable defaults)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    where: Mapped[str | None] = mapped_column(Text, nullable=True)
    signup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_signup_methods: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    default_signup_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship(
        "GuildConfiguration", back_populates="templates"
    )
    channel: Mapped["ChannelConfiguration"] = relationship("ChannelConfiguration")
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="template")

    # Constraints and Indexes
    __table_args__ = (
        Index("ix_game_templates_guild_order", "guild_id", "order"),
        Index("ix_game_templates_guild_default", "guild_id", "is_default"),
        CheckConstraint('"order" >= 0', name="ck_template_order_positive"),
    )

    def __repr__(self) -> str:
        return f"<GameTemplate(id={self.id}, name={self.name}, guild_id={self.guild_id})>"
