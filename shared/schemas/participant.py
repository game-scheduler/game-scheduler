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


"""Pydantic schemas for Game participants."""

from pydantic import BaseModel, Field


class ParticipantJoinRequest(BaseModel):
    """Request to join a game."""

    user_discord_id: str = Field(..., description="Discord user snowflake ID")


class ParticipantResponse(BaseModel):
    """Game participant response."""

    id: str = Field(..., description="Participant ID (UUID)")
    game_session_id: str = Field(..., description="Game session ID (UUID)")
    user_id: str | None = Field(None, description="User ID (UUID) - None for placeholder entries")
    discord_id: str | None = Field(None, description="Discord snowflake ID - None for placeholders")
    display_name: str | None = Field(
        None,
        description="Resolved display name (guild-specific or placeholder text)",
    )
    joined_at: str = Field(..., description="Join timestamp (UTC ISO)")
    status: str = Field(
        ..., description="Participant status (JOINED, DROPPED, WAITLIST, PLACEHOLDER)"
    )
    is_pre_populated: bool = Field(..., description="True if added at game creation time")

    model_config = {"from_attributes": True}
