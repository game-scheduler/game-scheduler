# Copyright 2026 Bret McKee
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


"""Participant action schedule model for deadline-based participant actions."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, generate_uuid

if TYPE_CHECKING:
    from .game import GameSession
    from .participant import GameParticipant


class ParticipantActionSchedule(CreatedAtMixin, Base):
    """
    Scheduled actions for individual participants.

    Each record represents one pending action (e.g., "drop") to be executed
    at a specific time if not cleared beforehand. The participant_action_daemon
    queries MIN(action_time) to determine when to wake up next.

    A UNIQUE constraint on participant_id ensures at most one pending action
    per participant at a time.
    """

    __tablename__ = "participant_action_schedule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("game_participants.id", ondelete="CASCADE"), unique=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    action_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )

    game: Mapped["GameSession"] = relationship("GameSession")
    participant: Mapped["GameParticipant"] = relationship("GameParticipant")
