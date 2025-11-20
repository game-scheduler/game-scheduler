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


"""Channel configuration endpoints."""

# ruff: noqa: B008
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.auth import oauth2
from services.api.dependencies import permissions
from services.api.services import config as config_service
from shared import database
from shared.schemas import auth as auth_schemas
from shared.schemas import channel as channel_schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@router.get("/{channel_id}", response_model=channel_schemas.ChannelConfigResponse)
async def get_channel(
    channel_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> channel_schemas.ChannelConfigResponse:
    """
    Get channel configuration by database UUID.

    Requires user to be member of the parent guild.
    """

    service = config_service.ConfigurationService(db)
    channel_config = await service.get_channel_by_id(channel_id)

    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel configuration not found"
        )

    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guild_ids = {g["id"] for g in user_guilds}

    # channel_config.guild.guild_id is the Discord guild ID (snowflake)
    discord_guild_id = channel_config.guild.guild_id

    logger.info(
        f"Channel UUID {channel_id} (Discord ID {channel_config.channel_id}) "
        f"belongs to Discord guild {discord_guild_id}, "
        f"User has access to {len(user_guild_ids)} guilds"
    )

    if discord_guild_id not in user_guild_ids:
        logger.warning(
            f"Guild membership check failed: channel's discord_guild_id={discord_guild_id} "
            f"not in user's guilds: {list(user_guild_ids.keys())[:3]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this channel's guild",
        )

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_config.channel_name,
        is_active=channel_config.is_active,
        max_players=channel_config.max_players,
        reminder_minutes=channel_config.reminder_minutes,
        default_rules=channel_config.default_rules,
        allowed_host_role_ids=channel_config.allowed_host_role_ids,
        game_category=channel_config.game_category,
        created_at=channel_config.created_at.isoformat(),
        updated_at=channel_config.updated_at.isoformat(),
    )


@router.post(
    "", response_model=channel_schemas.ChannelConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_channel_config(
    request: channel_schemas.ChannelConfigCreateRequest,
    current_user: auth_schemas.CurrentUser = Depends(permissions.require_manage_channels),
    db: AsyncSession = Depends(database.get_db),
) -> channel_schemas.ChannelConfigResponse:
    """
    Create channel configuration.

    Requires MANAGE_CHANNELS permission in the guild.
    """
    service = config_service.ConfigurationService(db)

    existing = await service.get_channel_by_discord_id(request.channel_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel configuration already exists",
        )

    channel_config = await service.create_channel_config(
        guild_id=request.guild_id,
        channel_discord_id=request.channel_id,
        channel_name=request.channel_name,
        is_active=request.is_active,
        max_players=request.max_players,
        reminder_minutes=request.reminder_minutes,
        default_rules=request.default_rules,
        allowed_host_role_ids=request.allowed_host_role_ids,
        game_category=request.game_category,
    )

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_config.channel_name,
        is_active=channel_config.is_active,
        max_players=channel_config.max_players,
        reminder_minutes=channel_config.reminder_minutes,
        default_rules=channel_config.default_rules,
        allowed_host_role_ids=channel_config.allowed_host_role_ids,
        game_category=channel_config.game_category,
        created_at=channel_config.created_at.isoformat(),
        updated_at=channel_config.updated_at.isoformat(),
    )


@router.put("/{channel_id}", response_model=channel_schemas.ChannelConfigResponse)
async def update_channel_config(
    channel_id: str,
    request: channel_schemas.ChannelConfigUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(permissions.require_manage_channels),
    db: AsyncSession = Depends(database.get_db),
) -> channel_schemas.ChannelConfigResponse:
    """
    Update channel configuration.

    Requires MANAGE_CHANNELS permission in the guild.
    """
    service = config_service.ConfigurationService(db)

    channel_config = await service.get_channel_by_id(channel_id)
    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel configuration not found"
        )

    updates = request.model_dump(exclude_unset=True)
    channel_config = await service.update_channel_config(channel_config, **updates)

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_config.channel_name,
        is_active=channel_config.is_active,
        max_players=channel_config.max_players,
        reminder_minutes=channel_config.reminder_minutes,
        default_rules=channel_config.default_rules,
        allowed_host_role_ids=channel_config.allowed_host_role_ids,
        game_category=channel_config.game_category,
        created_at=channel_config.created_at.isoformat(),
        updated_at=channel_config.updated_at.isoformat(),
    )
