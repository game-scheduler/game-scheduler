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
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.auth import discord_client as discord_client_module
from services.api.auth import oauth2
from services.api.dependencies import permissions
from services.api.services import config as config_service
from shared import database
from shared.schemas import auth as auth_schemas
from shared.schemas import channel as channel_schemas
from shared.schemas import guild as guild_schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/guilds", tags=["guilds"])


@router.get("", response_model=guild_schemas.GuildListResponse)
async def list_guilds(
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> guild_schemas.GuildListResponse:
    """
    List all guilds where the bot is present and user is a member.

    Returns guild configurations with current settings.
    """
    service = config_service.ConfigurationService(db)

    # Get guilds with automatic caching from discord client
    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    guild_configs = []
    for guild_id, discord_guild_data in user_guilds_dict.items():
        guild_config = await service.get_guild_by_discord_id(guild_id)
        if guild_config:
            guild_name = discord_guild_data.get("name", "Unknown Guild")

            guild_configs.append(
                guild_schemas.GuildConfigResponse(
                    id=guild_config.id,
                    guild_id=guild_config.guild_id,
                    guild_name=guild_name,
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


@router.get("/{guild_id}", response_model=guild_schemas.GuildConfigResponse)
async def get_guild(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> guild_schemas.GuildConfigResponse:
    """
    Get guild configuration by database UUID.

    Requires user to be member of the guild.
    """
    from services.api.auth import tokens

    service = config_service.ConfigurationService(db)

    guild_config = await service.get_guild_by_id(guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild configuration not found",
        )

    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    access_token = token_data["access_token"]
    user_guilds = await oauth2.get_user_guilds(access_token, current_user.user.discord_id)
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    discord_guild_id = guild_config.guild_id

    logger.info(
        f"get_guild: UUID {guild_id} maps to Discord guild {discord_guild_id}. "
        f"User has access to {len(user_guilds_dict)} guilds"
    )

    if discord_guild_id not in user_guilds_dict:
        logger.warning(
            f"get_guild: Discord guild {discord_guild_id} not found in "
            f"user's {len(user_guilds_dict)} guilds"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    guild_name = user_guilds_dict[discord_guild_id].get("name", "Unknown Guild")

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_name,
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
    db: AsyncSession = Depends(database.get_db),
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
        default_max_players=request.default_max_players,
        default_reminder_minutes=request.default_reminder_minutes or [60, 15],
        default_rules=request.default_rules,
        allowed_host_role_ids=request.allowed_host_role_ids or [],
        require_host_role=request.require_host_role,
    )

    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guilds_dict = {g["id"]: g for g in user_guilds}
    guild_name = user_guilds_dict.get(request.guild_id, {}).get("name", "Unknown Guild")

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_name,
        default_max_players=guild_config.default_max_players,
        default_reminder_minutes=guild_config.default_reminder_minutes,
        default_rules=guild_config.default_rules,
        allowed_host_role_ids=guild_config.allowed_host_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.put("/{guild_id}", response_model=guild_schemas.GuildConfigResponse)
async def update_guild_config(
    guild_id: str,
    request: guild_schemas.GuildConfigUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(permissions.require_manage_guild),
    db: AsyncSession = Depends(database.get_db),
) -> guild_schemas.GuildConfigResponse:
    """
    Update guild configuration.

    Requires MANAGE_GUILD permission in the guild.
    """
    service = config_service.ConfigurationService(db)

    guild_config = await service.get_guild_by_id(guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    updates = request.model_dump(exclude_unset=True)
    guild_config = await service.update_guild_config(guild_config, **updates)

    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guilds_dict = {g["id"]: g for g in user_guilds}
    guild_name = user_guilds_dict.get(guild_config.guild_id, {}).get("name", "Unknown Guild")

    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_name,
        default_max_players=guild_config.default_max_players,
        default_reminder_minutes=guild_config.default_reminder_minutes,
        default_rules=guild_config.default_rules,
        allowed_host_role_ids=guild_config.allowed_host_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.get(
    "/{guild_id}/channels",
    response_model=list[channel_schemas.ChannelConfigResponse],
)
async def list_guild_channels(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> list[channel_schemas.ChannelConfigResponse]:
    """
    List all configured channels for a guild by UUID.

    Returns channels with their settings and inheritance information.
    """
    from services.api.auth import tokens

    service = config_service.ConfigurationService(db)

    guild_config = await service.get_guild_by_id(guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild configuration not found",
        )

    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    access_token = token_data["access_token"]
    user_guilds = await oauth2.get_user_guilds(access_token, current_user.user.discord_id)
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    discord_guild_id = guild_config.guild_id

    logger.info(
        f"list_guild_channels: UUID {guild_id} maps to Discord guild {discord_guild_id}. "
        f"User has access to {len(user_guilds_dict)} guilds"
    )

    if discord_guild_id not in user_guilds_dict:
        logger.warning(
            f"list_guild_channels: Discord guild {discord_guild_id} not found in "
            f"user's {len(user_guilds_dict)} guilds"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    channels = await service.get_channels_by_guild(guild_config.id)

    return [
        channel_schemas.ChannelConfigResponse(
            id=channel.id,
            guild_id=channel.guild_id,
            guild_discord_id=guild_config.guild_id,
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


@router.get("/{guild_id}/roles")
async def list_guild_roles(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    discord_client: discord_client_module.DiscordAPIClient = Depends(
        discord_client_module.get_discord_client
    ),
) -> list[dict]:
    """
    List all roles for a guild, excluding @everyone and managed roles.

    Returns roles suitable for notification mentions.
    """
    from services.api.auth import tokens

    service = config_service.ConfigurationService(db)

    guild_config = await service.get_guild_by_id(guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild configuration not found",
        )

    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    access_token = token_data["access_token"]
    user_guilds = await oauth2.get_user_guilds(access_token, current_user.user.discord_id)
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    discord_guild_id = guild_config.guild_id

    if discord_guild_id not in user_guilds_dict:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    roles = await discord_client.fetch_guild_roles(discord_guild_id)

    # Filter out @everyone and managed roles
    filtered_roles = [
        {
            "id": role["id"],
            "name": role["name"],
            "color": role["color"],
            "position": role["position"],
            "managed": role.get("managed", False),
        }
        for role in roles
        if role["name"] != "@everyone" and not role.get("managed", False)
    ]

    # Sort by position (highest first)
    filtered_roles.sort(key=lambda r: r["position"], reverse=True)

    return filtered_roles
