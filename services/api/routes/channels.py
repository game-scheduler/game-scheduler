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
from services.api.auth import discord_client as discord_client_module
from services.api.database import queries
from services.api.dependencies import permissions
from services.api.services import channel_service
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

    channel_config = await queries.get_channel_by_id(db, channel_id)

    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel configuration not found"
        )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    await permissions.verify_guild_membership(channel_config.guild.guild_id, current_user, db)

    channel_name = await discord_client_module.fetch_channel_name_safe(channel_config.channel_id)

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_name,
        is_active=channel_config.is_active,
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
    existing = await queries.get_channel_by_discord_id(db, request.channel_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel configuration already exists",
        )

    channel_config = await channel_service.create_channel_config(
        db,
        guild_id=request.guild_id,
        channel_discord_id=request.channel_id,
        is_active=request.is_active,
    )

    channel_name = await discord_client_module.fetch_channel_name_safe(channel_config.channel_id)

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_name,
        is_active=channel_config.is_active,
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
    channel_config = await queries.get_channel_by_id(db, channel_id)
    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel configuration not found"
        )

    updates = request.model_dump(exclude_unset=True)
    channel_config = await channel_service.update_channel_config(db, channel_config, **updates)

    channel_name = await discord_client_module.fetch_channel_name_safe(channel_config.channel_id)

    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_name,
        is_active=channel_config.is_active,
        created_at=channel_config.created_at.isoformat(),
        updated_at=channel_config.updated_at.isoformat(),
    )
