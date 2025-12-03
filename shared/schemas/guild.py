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


"""Pydantic schemas for Guild configuration."""

from pydantic import BaseModel, Field


class GuildConfigCreateRequest(BaseModel):
    """Create guild configuration."""

    guild_id: str = Field(..., description="Discord guild snowflake ID")
    require_host_role: bool = Field(
        default=False,
        description="If true, users must have allowed host role to create games",
    )


class GuildConfigUpdateRequest(BaseModel):
    """Update guild configuration (all fields optional)."""

    bot_manager_role_ids: list[str] | None = None
    require_host_role: bool | None = None


class GuildConfigResponse(BaseModel):
    """Guild configuration response."""

    id: str = Field(..., description="Internal guild config ID (UUID)")
    guild_id: str = Field(..., description="Discord guild snowflake ID")
    guild_name: str = Field(..., description="Discord guild name")
    bot_manager_role_ids: list[str] | None = Field(
        None, description="Role IDs with Bot Manager permissions (can edit/delete any game)"
    )
    require_host_role: bool = Field(..., description="Whether host role is required")
    created_at: str = Field(..., description="Creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")

    model_config = {"from_attributes": True}


class GuildListResponse(BaseModel):
    """List of guilds for a user."""

    guilds: list[GuildConfigResponse] = Field(..., description="List of guild configurations")


class ValidateMentionRequest(BaseModel):
    """Request to validate a Discord mention."""

    mention: str = Field(..., description="Discord mention to validate (@username, <@123>, etc)")


class ValidateMentionResponse(BaseModel):
    """Response from mention validation."""

    valid: bool = Field(..., description="Whether the mention is valid")
    error: str | None = Field(None, description="Error message if validation failed")
