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


"""
Permission check dependencies for protected routes.

Provides FastAPI dependencies for role-based authorization.
"""

import logging

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import roles as roles_module
from services.api.auth import tokens
from services.api.database import queries
from services.api.dependencies import auth
from shared import database
from shared.schemas import auth as auth_schemas
from shared.utils.discord import DiscordPermissions

logger = logging.getLogger(__name__)


async def get_role_service() -> roles_module.RoleVerificationService:
    """
    Get role verification service dependency.

    Returns:
        Role verification service instance
    """
    return roles_module.get_role_service()


async def _resolve_guild_id(guild_id: str, db: AsyncSession) -> str:
    """
    Resolve database UUID to Discord guild ID if needed.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        db: Database session

    Returns:
        Discord guild ID (snowflake)
    """
    # Check if already a Discord snowflake ID (numeric string, 17-20 chars)
    if guild_id.isdigit() and 17 <= len(guild_id) <= 20:
        return guild_id

    # Otherwise treat as UUID and look up
    guild_config = await queries.get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(status_code=404, detail="Guild not found")

    return guild_config.guild_id


async def require_manage_guild(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(get_role_service),  # noqa: B008
    db: AsyncSession = Depends(database.get_db),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have MANAGE_GUILD permission for guild.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks MANAGE_GUILD permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    # Resolve Discord guild_id from database UUID if needed
    discord_guild_id = await _resolve_guild_id(guild_id, db)

    has_permission = await role_service.has_permissions(
        current_user.user.discord_id,
        discord_guild_id,
        access_token,
        DiscordPermissions.MANAGE_GUILD,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.user.discord_id} lacks MANAGE_GUILD permission "
            f"in guild {discord_guild_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You need MANAGE_GUILD permission to perform this action",
        )

    return current_user


async def require_manage_channels(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(get_role_service),  # noqa: B008
    db: AsyncSession = Depends(database.get_db),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have MANAGE_CHANNELS permission for guild.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks MANAGE_CHANNELS permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    # Resolve Discord guild_id from database UUID if needed
    discord_guild_id = await _resolve_guild_id(guild_id, db)

    has_permission = await role_service.has_permissions(
        current_user.user.discord_id,
        discord_guild_id,
        access_token,
        DiscordPermissions.MANAGE_CHANNELS,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.user.discord_id} lacks MANAGE_CHANNELS permission "
            f"in guild {discord_guild_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You need MANAGE_CHANNELS permission to perform this action",
        )

    return current_user


async def require_game_host(
    guild_id: str,
    channel_id: str | None = None,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(get_role_service),  # noqa: B008
    db: AsyncSession = Depends(database.get_db),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have game host permission with inheritance resolution.

    Checks channel-specific allowed roles, then guild allowed roles,
    then falls back to MANAGE_GUILD permission.

    Args:
        guild_id: Discord guild ID
        channel_id: Discord channel ID (optional)
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks game host permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    has_permission = await role_service.check_game_host_permission(
        current_user.user.discord_id,
        guild_id,
        db,
        channel_id=channel_id,
        access_token=access_token,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.user.discord_id} lacks game host permission in "
            f"guild {guild_id}, channel {channel_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to host games in this guild/channel",
        )

    return current_user


async def can_manage_game(
    game_host_id: str,
    guild_id: str,
    current_user: auth_schemas.CurrentUser,
    role_service: roles_module.RoleVerificationService,
    db: AsyncSession,
) -> bool:
    """
    Check if user can manage (edit/delete) a game.

    User can manage game if they are:
    1. The game host
    2. A Bot Manager (has bot_manager_role_ids)
    3. An administrator (MANAGE_GUILD permission)

    Args:
        game_host_id: Discord ID of the game host
        guild_id: Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        True if user can manage the game
    """
    if current_user.user.discord_id == game_host_id:
        return True

    is_bot_manager = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_id, db
    )
    if is_bot_manager:
        return True

    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        return False

    access_token = token_data["access_token"]
    is_admin = await role_service.has_permissions(
        current_user.user.discord_id, guild_id, access_token, DiscordPermissions.MANAGE_GUILD
    )

    return is_admin


async def can_export_game(
    game_host_id: str,
    game_participants: list,
    guild_id: str,
    user_id: str,
    discord_id: str,
    role_service: roles_module.RoleVerificationService,
    db: AsyncSession,
    access_token: str | None = None,
) -> bool:
    """
    Check if user can export a game to calendar format.

    User can export game if they are:
    1. The game host
    2. A participant in the game
    3. A Bot Manager (has bot_manager_role_ids)
    4. An administrator (MANAGE_GUILD permission)

    Args:
        game_host_id: Database UUID of the game host
        game_participants: List of GameParticipant objects
        guild_id: Discord guild ID
        user_id: Database UUID of the user
        discord_id: Discord ID of the user
        role_service: Role verification service
        db: Database session
        access_token: OAuth2 access token (required for admin check)

    Returns:
        True if user can export the game
    """
    # Check if user is the host
    if game_host_id == user_id:
        return True

    # Check if user is a participant
    if any(p.user_id == discord_id and p.user is not None for p in game_participants):
        return True

    # Check if user is bot manager or admin
    is_bot_manager = await role_service.check_bot_manager_permission(
        discord_id, guild_id, db, access_token
    )

    return is_bot_manager


async def require_administrator(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(get_role_service),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have ADMINISTRATOR permission for guild.

    Args:
        guild_id: Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks ADMINISTRATOR permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    has_permission = await role_service.has_permissions(
        current_user.user.discord_id,
        guild_id,
        access_token,
        DiscordPermissions.ADMINISTRATOR,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.user.discord_id} lacks ADMINISTRATOR permission "
            f"in guild {guild_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You need ADMINISTRATOR permission to perform this action",
        )

    return current_user
