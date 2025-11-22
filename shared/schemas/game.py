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


"""Pydantic schemas for Game sessions."""

from datetime import datetime

from pydantic import BaseModel, Field


class GameCreateRequest(BaseModel):
    """Create a new game session."""

    title: str = Field(..., description="Game title", min_length=1, max_length=200)
    description: str | None = Field(
        None, description="Game description (optional)", max_length=4000
    )
    signup_instructions: str | None = Field(
        None, description="Signup instructions for participants (optional)", max_length=1000
    )
    scheduled_at: datetime = Field(..., description="Game start time (ISO 8601 UTC timestamp)")
    guild_id: str = Field(..., description="Guild ID (UUID)")
    channel_id: str = Field(..., description="Channel ID (UUID)")
    max_players: int | None = Field(
        None, description="Max players override (uses channel/guild default if None)"
    )
    min_players: int = Field(1, description="Minimum players required (default: 1)", ge=1)
    reminder_minutes: list[int] | None = Field(
        None,
        description="Reminder times override (uses channel/guild default if None)",
    )
    rules: str | None = Field(
        None, description="Game rules override (uses channel/guild default if None)"
    )
    initial_participants: list[str] = Field(
        default_factory=list,
        description="Pre-populated participants (@mentions or placeholder strings)",
    )


class GameUpdateRequest(BaseModel):
    """Update game session (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    signup_instructions: str | None = Field(None, max_length=1000)
    scheduled_at: datetime | None = None
    max_players: int | None = None
    min_players: int | None = Field(None, ge=1)
    reminder_minutes: list[int] | None = None
    rules: str | None = None
    status: str | None = Field(
        None,
        description="Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)",
    )


class GameResponse(BaseModel):
    """Game session response."""

    id: str = Field(..., description="Game session ID (UUID)")
    title: str = Field(..., description="Game title")
    description: str | None = Field(None, description="Game description")
    signup_instructions: str | None = Field(
        None, description="Signup instructions for participants"
    )
    scheduled_at: str = Field(..., description="Game start time (ISO 8601 UTC timestamp)")
    scheduled_at_unix: int = Field(..., description="Game start time (Unix timestamp for Discord)")
    max_players: int | None = Field(None, description="Max players (resolved)")
    min_players: int = Field(1, description="Minimum players required")
    guild_id: str = Field(..., description="Guild ID (UUID)")
    channel_id: str = Field(..., description="Channel ID (UUID)")
    message_id: str | None = Field(None, description="Discord message snowflake ID")
    host: "ParticipantResponse" = Field(..., description="Game host information")
    rules: str | None = Field(None, description="Game rules (resolved)")
    reminder_minutes: list[int] | None = Field(None, description="Reminder times (resolved)")
    status: str = Field(..., description="Game status")
    participant_count: int = Field(..., description="Current number of participants")
    participants: list["ParticipantResponse"] = Field(
        default_factory=list, description="List of participants"
    )
    created_at: str = Field(..., description="Creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")

    model_config = {"from_attributes": True}


class GameListResponse(BaseModel):
    """List of games response."""

    games: list[GameResponse] = Field(..., description="List of games")
    total: int = Field(..., description="Total number of games")


# Import at end to avoid circular import
from shared.schemas.participant import ParticipantResponse  # noqa: E402

GameResponse.model_rebuild()
