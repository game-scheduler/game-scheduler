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


"""Game session model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.utils.status_transitions import GameStatus

from .base import Base, generate_uuid, utc_now
from .signup_method import SignupMethod

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .game_image import GameImage
    from .guild import GuildConfiguration
    from .participant import GameParticipant
    from .template import GameTemplate
    from .user import User


class GameSession(Base):
    """
    Game session with scheduling and participant management.

    Settings come from selected template with optional host overrides.
    """

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("game_templates.id"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column()
    where: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"))
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_configurations.id"))
    archive_delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archive_channel_id: Mapped[str | None] = mapped_column(
        ForeignKey("channel_configurations.id", ondelete="SET NULL"), nullable=True
    )
    rewards: Mapped[str | None] = mapped_column(Text, nullable=True)
    remind_host_rewards: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    host_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    notify_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_player_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=GameStatus.SCHEDULED.value,
        server_default=text(f"'{GameStatus.SCHEDULED.value}'"),
        index=True,
    )
    signup_method: Mapped[str] = mapped_column(
        String(50),
        default=SignupMethod.SELF_SIGNUP.value,
        server_default=text(f"'{SignupMethod.SELF_SIGNUP.value}'"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=utc_now, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=func.now()
    )

    # Image references (FK to game_images table)
    thumbnail_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_images.id", ondelete="SET NULL"), nullable=True
    )
    banner_image_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_images.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    template: Mapped["GameTemplate"] = relationship("GameTemplate", back_populates="games")
    guild: Mapped["GuildConfiguration"] = relationship("GuildConfiguration", back_populates="games")
    channel: Mapped["ChannelConfiguration"] = relationship(
        "ChannelConfiguration",
        back_populates="games",
        foreign_keys="GameSession.channel_id",
    )
    archive_channel: Mapped["ChannelConfiguration | None"] = relationship(
        "ChannelConfiguration", foreign_keys="GameSession.archive_channel_id"
    )
    host: Mapped["User"] = relationship("User", back_populates="hosted_games")
    participants: Mapped[list["GameParticipant"]] = relationship(
        "GameParticipant", back_populates="game", passive_deletes="all"
    )
    thumbnail: Mapped["GameImage | None"] = relationship(
        "GameImage", foreign_keys=[thumbnail_id], lazy="selectin"
    )
    banner_image: Mapped["GameImage | None"] = relationship(
        "GameImage", foreign_keys=[banner_image_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, title={self.title}, status={self.status})>"
