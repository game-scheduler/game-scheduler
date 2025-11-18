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


"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request to initiate OAuth2 login flow."""

    redirect_uri: str | None = Field(None, description="Optional redirect URI after authentication")


class LoginResponse(BaseModel):
    """OAuth2 authorization URL response."""

    authorization_url: str = Field(..., description="Discord OAuth2 authorization URL")
    state: str = Field(..., description="CSRF protection state token")


class OAuthCallbackRequest(BaseModel):
    """OAuth2 callback parameters."""

    code: str = Field(..., description="Authorization code from Discord")
    state: str = Field(..., description="State token for CSRF verification")


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str = Field(..., description="Discord access token")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Refresh token from previous auth")


class UserInfoResponse(BaseModel):
    """Discord user information response."""

    id: str = Field(..., description="Discord user snowflake ID")
    username: str = Field(..., description="Discord username")
    avatar: str | None = Field(None, description="Avatar hash")
    guilds: list[dict] = Field(default_factory=list, description="User's guilds")


class CurrentUser(BaseModel):
    """Current authenticated user from token."""

    discord_id: str = Field(..., description="Discord user snowflake ID")
    access_token: str = Field(..., description="Discord API access token")
