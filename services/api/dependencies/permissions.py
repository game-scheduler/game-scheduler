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
from services.api.dependencies import auth
from shared import database
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)


async def get_role_service() -> roles_module.RoleVerificationService:
    """
    Get role verification service dependency.

    Returns:
        Role verification service instance
    """
    return roles_module.get_role_service()


async def require_manage_guild(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(get_role_service),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have MANAGE_GUILD permission for guild.

    Args:
        guild_id: Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks MANAGE_GUILD permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    has_permission = await role_service.check_manage_guild_permission(
        current_user.discord_id,
        guild_id,
        access_token,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.discord_id} lacks MANAGE_GUILD permission in guild {guild_id}"
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
) -> auth_schemas.CurrentUser:
    """
    Require user to have MANAGE_CHANNELS permission for guild.

    Args:
        guild_id: Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks MANAGE_CHANNELS permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    access_token = token_data["access_token"]

    has_permission = await role_service.check_manage_channels_permission(
        current_user.discord_id,
        guild_id,
        access_token,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.discord_id} lacks MANAGE_CHANNELS permission in guild {guild_id}"
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
        current_user.discord_id,
        guild_id,
        db,
        channel_id=channel_id,
        access_token=access_token,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.discord_id} lacks game host permission in "
            f"guild {guild_id}, channel {channel_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to host games in this guild/channel",
        )

    return current_user


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

    has_permission = await role_service.check_administrator_permission(
        current_user.discord_id,
        guild_id,
        access_token,
    )

    if not has_permission:
        logger.warning(
            f"User {current_user.discord_id} lacks ADMINISTRATOR permission in guild {guild_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You need ADMINISTRATOR permission to perform this action",
        )

    return current_user
