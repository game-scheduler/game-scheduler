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


"""Guild configuration endpoints."""

# ruff: noqa: B008
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.dependencies import permissions
from services.api.services import config as config_service
from shared import database
from shared.schemas import auth as auth_schemas
from shared.schemas import channel as channel_schemas
from shared.schemas import guild as guild_schemas

router = APIRouter(prefix="/api/v1/guilds", tags=["guilds"])


@router.get("", response_model=guild_schemas.GuildListResponse)
async def list_guilds(
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_session),
) -> guild_schemas.GuildListResponse:
    """
    List all guilds where the bot is present and user is a member.

    Returns guild configurations with current settings.
    """
    from services.api.auth import discord_client

    client = discord_client.get_discord_client()
    service = config_service.ConfigurationService(db)

    user_guilds = await client.get_user_guilds(current_user.access_token)

    guild_configs = []
    for guild_data in user_guilds:
        guild_config = await service.get_guild_by_discord_id(guild_data["id"])

        if guild_config:
            guild_configs.append(
                guild_schemas.GuildConfigResponse(
                    id=guild_config.id,
                    guild_id=guild_config.guild_id,
                    guild_name=guild_config.guild_name,
                    default_max_players=guild_config.default_max_players,
                    default_reminder_minutes=guild_config.default_reminder_minutes,
                    default_rules=guild_config.default_rules,
                    allowed_host_role_ids=guild_config.allowed_host_role_ids,
                    require_host_role=guild_config.require_host_role,
                    created_at=guild_config.created_at.isoformat(),
                    updated_at=guild_config.updated_at.isoformat(),
                )
            )

    return guild_schemas.GuildListResponse(guilds=guild_configs)


@router.get("/{guild_discord_id}", response_model=guild_schemas.GuildConfigResponse)
async def get_guild(
    guild_discord_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_session),
) -> guild_schemas.GuildConfigResponse:
    """
    Get guild configuration by Discord guild ID.

    Requires user to be member of the guild.
    """
    from services.api.auth import discord_client

    client = discord_client.get_discord_client()
    service = config_service.ConfigurationService(db)

    user_guilds = await client.get_user_guilds(current_user.access_token)
    user_guild_ids = {g["id"] for g in user_guilds}

    if guild_discord_id not in user_guild_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    guild_config = await service.get_guild_by_discord_id(guild_discord_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_config.guild_name,
        default_max_players=guild_config.default_max_players,
        default_reminder_minutes=guild_config.default_reminder_minutes,
        default_rules=guild_config.default_rules,
        allowed_host_role_ids=guild_config.allowed_host_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.post(
    "", response_model=guild_schemas.GuildConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_guild_config(
    request: guild_schemas.GuildConfigCreateRequest,
    current_user: auth_schemas.CurrentUser = Depends(permissions.require_manage_guild),
    db: AsyncSession = Depends(database.get_db_session),
) -> guild_schemas.GuildConfigResponse:
    """
    Create guild configuration.

    Requires MANAGE_GUILD permission in the guild.
    """
    service = config_service.ConfigurationService(db)

    existing = await service.get_guild_by_discord_id(request.guild_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Guild configuration already exists",
        )

    guild_config = await service.create_guild_config(
        guild_discord_id=request.guild_id,
        guild_name=request.guild_name,
        default_max_players=request.default_max_players,
        default_reminder_minutes=request.default_reminder_minutes or [60, 15],
        default_rules=request.default_rules,
        allowed_host_role_ids=request.allowed_host_role_ids or [],
        require_host_role=request.require_host_role,
    )

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_config.guild_name,
        default_max_players=guild_config.default_max_players,
        default_reminder_minutes=guild_config.default_reminder_minutes,
        default_rules=guild_config.default_rules,
        allowed_host_role_ids=guild_config.allowed_host_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.put("/{guild_discord_id}", response_model=guild_schemas.GuildConfigResponse)
async def update_guild_config(
    guild_discord_id: str,
    request: guild_schemas.GuildConfigUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(permissions.require_manage_guild),
    db: AsyncSession = Depends(database.get_db_session),
) -> guild_schemas.GuildConfigResponse:
    """
    Update guild configuration.

    Requires MANAGE_GUILD permission in the guild.
    """
    service = config_service.ConfigurationService(db)

    guild_config = await service.get_guild_by_discord_id(guild_discord_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    updates = request.model_dump(exclude_unset=True)
    guild_config = await service.update_guild_config(guild_config, **updates)

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_config.guild_name,
        default_max_players=guild_config.default_max_players,
        default_reminder_minutes=guild_config.default_reminder_minutes,
        default_rules=guild_config.default_rules,
        allowed_host_role_ids=guild_config.allowed_host_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.get(
    "/{guild_discord_id}/channels",
    response_model=list[channel_schemas.ChannelConfigResponse],
)
async def list_guild_channels(
    guild_discord_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_session),
) -> list[channel_schemas.ChannelConfigResponse]:
    """
    List all configured channels for a guild.

    Returns channels with their settings and inheritance information.
    """
    from services.api.auth import discord_client

    client = discord_client.get_discord_client()
    service = config_service.ConfigurationService(db)

    user_guilds = await client.get_user_guilds(current_user.access_token)
    user_guild_ids = {g["id"] for g in user_guilds}

    if guild_discord_id not in user_guild_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    guild_config = await service.get_guild_by_discord_id(guild_discord_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    channels = await service.get_channels_by_guild(guild_config.id)

    return [
        channel_schemas.ChannelConfigResponse(
            id=channel.id,
            guild_id=channel.guild_id,
            channel_id=channel.channel_id,
            channel_name=channel.channel_name,
            is_active=channel.is_active,
            max_players=channel.max_players,
            reminder_minutes=channel.reminder_minutes,
            default_rules=channel.default_rules,
            allowed_host_role_ids=channel.allowed_host_role_ids,
            game_category=channel.game_category,
            created_at=channel.created_at.isoformat(),
            updated_at=channel.updated_at.isoformat(),
        )
        for channel in channels
    ]
