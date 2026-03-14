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


"""Pydantic schemas for Game sessions."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_constants import (
    DISCORD_SNOWFLAKE_MAX_LENGTH,
    DISCORD_SNOWFLAKE_MIN_LENGTH,
)

if TYPE_CHECKING:
    from shared.schemas.participant import ParticipantResponse

# Discord API constraints
MAX_ROLES_PER_GAME = 10


class GameCreateRequest(BaseModel):
    """Create a new game session from a template."""

    template_id: str = Field(..., description="Template UUID")
    title: str = Field(..., description="Game title", min_length=1, max_length=200)
    scheduled_at: datetime = Field(..., description="Game start time (ISO 8601 UTC timestamp)")

    # Optional overrides of template defaults
    description: str | None = Field(
        None, description="Game description (optional)", max_length=2000
    )
    max_players: int | None = Field(
        None,
        description="Max players override (uses template default if None)",
        ge=1,
        le=100,
    )
    expected_duration_minutes: int | None = Field(
        None,
        description="Expected game duration in minutes (optional, uses template default if None)",
        ge=1,
    )
    reminder_minutes: list[int] | None = Field(
        None,
        description="Reminder times override (uses template default if None)",
    )
    where: str | None = Field(
        None,
        description="Game location (optional, uses template default if None)",
        max_length=500,
    )
    signup_instructions: str | None = Field(
        None,
        description=(
            "Signup instructions for participants (optional, uses template default if None)"
        ),
        max_length=1000,
    )
    initial_participants: list[str] = Field(
        default_factory=list,
        description="Pre-populated participants (@mentions or placeholder strings)",
    )
    host: str | None = Field(
        None,
        description=(
            "Game host (@mention or username). Bot managers only. Defaults to current user if None."
        ),
        max_length=200,
    )
    signup_method: str | None = Field(
        None,
        description=(
            "Signup method (SELF_SIGNUP or HOST_SELECTED). Must be in template's "
            "allowed_signup_methods if specified. Defaults to template's default_signup_method."
        ),
        max_length=50,
    )

    @field_validator("signup_method")
    @classmethod
    def validate_signup_method(cls, v: str | None) -> str | None:
        """Validate signup method is a valid value."""
        if v is None:
            return v
        from shared.models.signup_method import SignupMethod  # noqa: PLC0415

        valid_values = [method.value for method in SignupMethod]
        if v not in valid_values:
            msg = f"Invalid signup method: {v}. Must be one of {valid_values}"
            raise ValueError(msg)
        return v


class GameUpdateRequest(BaseModel):
    """Update game session (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    signup_instructions: str | None = Field(None, max_length=1000)
    scheduled_at: datetime | None = None
    where: str | None = Field(None, max_length=500)
    max_players: int | None = None
    reminder_minutes: list[int] | None = None
    expected_duration_minutes: int | None = Field(
        None,
        description="Expected game duration in minutes (optional)",
        ge=1,
    )
    status: str | None = Field(
        None,
        description="Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)",
    )
    notify_role_ids: list[str] | None = Field(
        None,
        description="Discord role IDs to mention in announcement (max 10)",
        max_length=10,
    )
    participants: list[dict[str, str | int]] | None = Field(
        None,
        description="Updated participants list with mention, position_type, and position",
    )
    removed_participant_ids: list[str] | None = Field(
        None,
        description="List of participant IDs to remove",
    )
    signup_method: str | None = Field(
        None,
        description="Signup method (SELF_SIGNUP or HOST_SELECTED)",
    )

    @field_validator("notify_role_ids")
    @classmethod
    def validate_role_ids(cls, v: list[str] | None) -> list[str] | None:
        """Validate role IDs are valid Discord snowflakes."""
        if v is None:
            return v
        if len(v) > MAX_ROLES_PER_GAME:
            msg = f"Maximum {MAX_ROLES_PER_GAME} roles allowed"
            raise ValueError(msg)
        for role_id in v:
            if (
                not role_id.isdigit()
                or len(role_id) < DISCORD_SNOWFLAKE_MIN_LENGTH
                or len(role_id) > DISCORD_SNOWFLAKE_MAX_LENGTH
            ):
                msg = f"Invalid Discord role ID format: {role_id}"
                raise ValueError(msg)
        return v


class GameResponse(BaseModel):
    """Game session response."""

    id: str = Field(..., description="Game session ID (UUID)")
    title: str = Field(..., description="Game title")
    description: str | None = Field(None, description="Game description")
    signup_instructions: str | None = Field(
        None, description="Signup instructions for participants"
    )
    scheduled_at: str = Field(..., description="Game start time (ISO 8601 UTC timestamp)")
    where: str | None = Field(None, description="Game location")
    max_players: int | None = Field(None, description="Max players (resolved)")
    guild_id: str = Field(..., description="Guild ID (UUID)")
    guild_name: str | None = Field(None, description="Guild name")
    channel_id: str = Field(..., description="Channel ID (UUID)")
    channel_name: str | None = Field(None, description="Channel name")
    message_id: str | None = Field(None, description="Discord message snowflake ID)")
    host: "ParticipantResponse" = Field(..., description="Game host information")
    reminder_minutes: list[int] | None = Field(None, description="Reminder times (resolved)")
    expected_duration_minutes: int | None = Field(
        None, description="Expected game duration in minutes"
    )
    status: str = Field(..., description="Game status")
    signup_method: str = Field(..., description="Signup method (SELF_SIGNUP or HOST_SELECTED)")
    participant_count: int = Field(..., description="Current number of participants")
    participants: list["ParticipantResponse"] = Field(
        default_factory=list, description="List of participants"
    )
    notify_role_ids: list[str] | None = Field(
        None, description="Discord role IDs to mention in announcement"
    )
    created_at: str = Field(..., description="Creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")
    has_thumbnail: bool = Field(default=False, description="True if game has a thumbnail image")
    has_image: bool = Field(default=False, description="True if game has a banner image")
    thumbnail_id: str | None = Field(None, description="UUID of thumbnail image if present")
    banner_image_id: str | None = Field(None, description="UUID of banner image if present")
    can_manage: bool = Field(
        default=False,
        description="True if the requesting user can edit or manage this game",
    )

    model_config = {"from_attributes": True}


class GameListResponse(BaseModel):
    """List of games response."""

    games: list[GameResponse] = Field(..., description="List of games")
    total: int = Field(..., description="Total number of games")


# Import at end to avoid circular import
from shared.schemas.participant import ParticipantResponse  # noqa: E402, TC001

GameResponse.model_rebuild()
