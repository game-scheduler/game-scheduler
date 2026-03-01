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


"""Pydantic schemas for Guild configuration."""

from pydantic import BaseModel, Field


class GuildConfigCreateRequest(BaseModel):
    """Create guild configuration."""

    guild_id: str = Field(..., description="Discord guild snowflake ID")


class GuildConfigUpdateRequest(BaseModel):
    """Update guild configuration (all fields optional)."""

    bot_manager_role_ids: list[str] | None = None


class GuildBasicInfoResponse(BaseModel):
    """Basic guild information response (no sensitive config data)."""

    id: str = Field(..., description="Internal guild config ID (UUID)")
    guild_name: str = Field(..., description="Discord guild name")
    created_at: str = Field(..., description="When guild was added to database")
    updated_at: str = Field(..., description="When guild config was last updated")


class GuildConfigResponse(BaseModel):
    """Guild configuration response (includes sensitive config data)."""

    id: str = Field(..., description="Internal guild config ID (UUID)")
    guild_name: str = Field(..., description="Discord guild name")
    bot_manager_role_ids: list[str] | None = Field(
        None, description="Role IDs with Bot Manager permissions (can edit/delete any game)"
    )
    created_at: str = Field(..., description="When guild was added to database")
    updated_at: str = Field(..., description="When guild config was last updated")

    model_config = {"from_attributes": True}


class GuildListResponse(BaseModel):
    """List of guilds for a user."""

    guilds: list[GuildBasicInfoResponse] = Field(..., description="List of guilds")


class ValidateMentionRequest(BaseModel):
    """Request to validate a Discord mention."""

    mention: str = Field(..., description="Discord mention to validate (@username, <@123>, etc)")


class ValidateMentionResponse(BaseModel):
    """Response from mention validation."""

    valid: bool = Field(..., description="Whether the mention is valid")
    error: str | None = Field(None, description="Error message if validation failed")


class GuildSyncResponse(BaseModel):
    """Response from guild sync operation."""

    new_guilds: int = Field(..., description="Number of new guilds created")
    new_channels: int = Field(..., description="Number of channels added for new guilds")
