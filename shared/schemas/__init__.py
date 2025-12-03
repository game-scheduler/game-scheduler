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


"""Pydantic schemas for request/response validation."""

from shared.schemas.auth import (
    LoginRequest,
    LoginResponse,
    OAuthCallbackRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfoResponse,
)
from shared.schemas.channel import (
    ChannelConfigCreateRequest,
    ChannelConfigResponse,
    ChannelConfigUpdateRequest,
)
from shared.schemas.game import (
    GameCreateRequest,
    GameListResponse,
    GameResponse,
    GameUpdateRequest,
)
from shared.schemas.guild import (
    GuildConfigCreateRequest,
    GuildConfigResponse,
    GuildConfigUpdateRequest,
    GuildListResponse,
)
from shared.schemas.participant import (
    ParticipantJoinRequest,
    ParticipantResponse,
)
from shared.schemas.template import (
    TemplateCreateRequest,
    TemplateListItem,
    TemplateReorderRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)
from shared.schemas.user import UserPreferencesRequest, UserResponse

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "OAuthCallbackRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserInfoResponse",
    # Channel
    "ChannelConfigCreateRequest",
    "ChannelConfigUpdateRequest",
    "ChannelConfigResponse",
    # Game
    "GameCreateRequest",
    "GameUpdateRequest",
    "GameResponse",
    "GameListResponse",
    # Guild
    "GuildConfigCreateRequest",
    "GuildConfigUpdateRequest",
    "GuildConfigResponse",
    "GuildListResponse",
    # Participant
    "ParticipantJoinRequest",
    "ParticipantResponse",
    # Template
    "TemplateCreateRequest",
    "TemplateUpdateRequest",
    "TemplateResponse",
    "TemplateListItem",
    "TemplateReorderRequest",
    # User
    "UserResponse",
    "UserPreferencesRequest",
]
