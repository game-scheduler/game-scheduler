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


"""
Permission check dependencies for protected routes.

Provides FastAPI dependencies for role-based authorization.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from services.api.auth import roles as roles_module
from services.api.auth import tokens
from services.api.database import queries
from services.api.dependencies import auth
from shared import database
from shared.cache import projection as member_projection
from shared.cache.client import RedisClient, get_redis_client
from shared.models.game import GameSession
from shared.models.template import GameTemplate
from shared.schemas import auth as auth_schemas
from shared.utils.discord import DiscordPermissions
from shared.utils.security_constants import (
    DISCORD_SNOWFLAKE_MAX_LENGTH,
    DISCORD_SNOWFLAKE_MIN_LENGTH,
)

logger = logging.getLogger(__name__)


async def _check_guild_membership(
    user_discord_id: str,
    guild_id: str,
    redis: RedisClient,
) -> bool:
    """
    Check if user is a member of a Discord guild using projection.

    This is an internal helper that returns a boolean without raising exceptions.
    Use verify_guild_membership for route-level authorization that raises 404.

    Args:
        user_discord_id: Discord ID of the user
        guild_id: Discord guild ID (snowflake)
        redis: Redis client for projection reads

    Returns:
        True if user is a member of the guild, False otherwise
    """
    if not await member_projection.is_bot_fresh(redis=redis):
        logger.debug(
            "Bot projection not fresh for guild membership check (user=%s, guild=%s)",
            user_discord_id,
            guild_id,
        )
        return False

    guild_ids = await member_projection.get_user_guilds(user_discord_id, redis=redis)
    if guild_ids is None:
        return False
    return guild_id in guild_ids


async def verify_guild_membership(
    guild_id: str,
    current_user: auth_schemas.CurrentUser,
    _db: AsyncSession,
    redis: RedisClient | None = None,
) -> list[str] | None:
    """
    Verify user is a member of the specified Discord guild.

    Returns the list of user's guild IDs if member, or raises 503 if bot projection is
    not fresh, or raises 404 if not member.

    Args:
        guild_id: Discord guild ID (snowflake)
        _db: Database session (unused, reserved for future authorization checks)
        current_user: Current authenticated user
        redis: Redis client for projection reads (optional, will get singleton if not provided)

    Returns:
        List of user's guild IDs if member, or None if bot not fresh

    Raises:
        HTTPException(503): If bot projection is not fresh
        HTTPException(404): If user is not a member of the guild
        HTTPException(401): If session token is invalid
    """
    if redis is None:
        redis = await get_redis_client()

    if not await member_projection.is_bot_fresh(redis=redis):
        logger.warning(
            "Bot projection not fresh when verifying guild membership for user %s in guild %s",
            current_user.user.discord_id,
            guild_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot is temporarily unavailable; please try again",
        )

    user_guilds = await member_projection.get_user_guilds(current_user.user.discord_id, redis=redis)

    if user_guilds is None:
        logger.warning(
            "User guilds not found in projection for user %s",
            current_user.user.discord_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unavailable"
        )

    is_member = guild_id in user_guilds

    if not is_member:
        logger.warning(
            "User %s attempted to access guild %s where they are not a member",
            current_user.user.discord_id,
            guild_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild not found")

    return user_guilds


async def verify_template_access(
    template: GameTemplate,
    user_discord_id: str,
    access_token: str,
    db: AsyncSession,
    redis: RedisClient | None = None,
) -> GameTemplate:
    """
    Verify user can access a template based on guild membership.

    Returns 404 (not 403) if user is not a guild member to prevent information
    disclosure about guilds the user doesn't belong to.

    Args:
        template: Template to check access for
        user_discord_id: Discord ID of the user
        access_token: User's OAuth2 access token (deprecated, no longer used)
        db: Database session
        redis: Redis client for projection checks (optional, will get singleton if not provided)

    Returns:
        Template if user is authorized

    Raises:
        HTTPException(404): If user is not a member of template's guild
        HTTPException(503): If bot projection is not fresh
    """
    # Get guild configuration to resolve Discord guild ID
    guild_config = await queries.require_guild_by_id(
        db,
        template.guild_id,
        access_token,
        user_discord_id,
        not_found_detail="Template not found",
    )

    # Check guild membership using projection
    if redis is None:
        redis = await get_redis_client()
    is_member = await _check_guild_membership(user_discord_id, guild_config.guild_id, redis)

    if not is_member:
        logger.warning(
            "User %s attempted to access template %s in guild %s where they are not a member",
            user_discord_id,
            template.id,
            guild_config.guild_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return template


async def verify_game_access(
    game: GameSession,
    user_discord_id: str,
    access_token: str,
    db: AsyncSession,
    role_service: roles_module.RoleVerificationService,
    redis: RedisClient | None = None,
) -> GameSession:
    """
    Verify user can access a game based on guild membership and template player roles.

    Returns 404 (not 403) if user is not a guild member to prevent information
    disclosure about guilds the user doesn't belong to. If user is a guild member
    but lacks required player roles, raises 403.

    Args:
        game: Game to check access for
        user_discord_id: Discord ID of the user
        access_token: User's OAuth2 access token (deprecated, no longer used for guild checks)
        db: Database session
        role_service: Role verification service
        redis: Redis client for projection checks (optional, will get singleton if not provided)

    Returns:
        Game if user is authorized

    Raises:
        HTTPException(404): If user is not a member of game's guild
        HTTPException(403): If user lacks required player roles
        HTTPException(503): If bot projection is not fresh
    """
    # Get guild configuration to resolve Discord guild ID
    guild_config = await queries.require_guild_by_id(
        db,
        game.guild_id,
        access_token,
        user_discord_id,
        not_found_detail="Game not found",
    )

    # Check guild membership first - return 404 if not member to prevent info disclosure
    if redis is None:
        redis = await get_redis_client()
    is_member = await _check_guild_membership(user_discord_id, guild_config.guild_id, redis)

    if not is_member:
        logger.warning(
            "User %s attempted to access game %s in guild %s where they are not a member",
            user_discord_id,
            game.id,
            guild_config.guild_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    # Check player role restrictions from template (if configured).
    # Hosts are always exempt — they can always see and access their own games.
    is_host = game.host is not None and user_discord_id == game.host.discord_id
    if game.allowed_player_role_ids and not is_host:
        has_role = await role_service.has_any_role(
            user_discord_id,
            guild_config.guild_id,
            game.allowed_player_role_ids,
        )

        if not has_role:
            logger.warning(
                "User %s lacks required player roles for game %s",
                user_discord_id,
                game.id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have the required role to access this game",
            )

    return game


async def get_role_service() -> roles_module.RoleVerificationService:
    """
    Get role verification service dependency.

    Returns:
        Role verification service instance
    """
    return roles_module.get_role_service()


async def _resolve_guild_id(
    guild_id: str, db: AsyncSession, access_token: str, user_discord_id: str
) -> str:
    """
    Resolve database UUID to Discord guild ID if needed.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        db: Database session
        access_token: User's OAuth2 access token
        user_discord_id: Discord ID of the user

    Returns:
        Discord guild ID (snowflake)
    """
    # Check if already a Discord snowflake ID (numeric string, 17-20 chars)
    if (
        guild_id.isdigit()
        and DISCORD_SNOWFLAKE_MIN_LENGTH <= len(guild_id) <= DISCORD_SNOWFLAKE_MAX_LENGTH
    ):
        return guild_id

    # Otherwise treat as UUID and look up with authorization check
    guild_config = await queries.require_guild_by_id(db, guild_id, access_token, user_discord_id)

    return guild_config.guild_id


async def _require_permission(
    guild_id: str,
    permission_checker: Callable[..., Awaitable[bool]],
    error_message: str,
    current_user: auth_schemas.CurrentUser,
    _role_service: roles_module.RoleVerificationService,
    db: AsyncSession,
    **checker_kwargs: Any,  # noqa: ANN401
) -> auth_schemas.CurrentUser:
    """
    Generic permission requirement helper for FastAPI dependencies.

    Performs token validation, guild ID resolution, and permission checking.
    Use this helper to eliminate duplication in permission dependency functions.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        permission_checker: Async callable that checks permissions
            (e.g., role_service.has_permissions or role_service.check_bot_manager_permission)
        error_message: Custom error message for permission denial
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session
        **checker_kwargs: Additional keyword arguments passed to permission_checker
            (e.g., permissions for has_permissions)

    Returns:
        Current user if authorized

    Raises:
        HTTPException(401): If session token is invalid
        HTTPException(403): If user lacks required permission
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if token_data.get("is_maintainer"):
        return current_user

    access_token = token_data["access_token"]
    discord_guild_id = await _resolve_guild_id(
        guild_id, db, access_token, current_user.user.discord_id
    )

    has_permission = await permission_checker(
        current_user.user.discord_id,
        discord_guild_id,
        access_token,
        **checker_kwargs,
    )

    if not has_permission:
        logger.warning(
            "User %s lacks permission in guild %s",
            current_user.user.discord_id,
            discord_guild_id,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)

    return current_user


async def require_manage_guild(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(  # noqa: B008
        auth.get_current_user
    ),
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        get_role_service
    ),
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

    async def check_manage_guild(user_id: str, guild_id: str, token: str) -> bool:
        return await role_service.has_permissions(
            user_id, guild_id, token, DiscordPermissions.MANAGE_GUILD
        )

    return await _require_permission(
        guild_id,
        check_manage_guild,
        "You need MANAGE_GUILD permission to perform this action",
        current_user,
        role_service,
        db,
    )

    return current_user


async def require_manage_channels(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(  # noqa: B008
        auth.get_current_user
    ),
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        get_role_service
    ),
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

    async def check_manage_channels(user_id: str, guild_id: str, token: str) -> bool:
        return await role_service.has_permissions(
            user_id, guild_id, token, DiscordPermissions.MANAGE_CHANNELS
        )

    return await _require_permission(
        guild_id,
        check_manage_channels,
        "You need MANAGE_CHANNELS permission to perform this action",
        current_user,
        role_service,
        db,
    )


async def get_guild_name(
    guild_discord_id: str,
    _db: AsyncSession,
    *,
    redis: RedisClient | None = None,
) -> str:
    """
    Get display name for a Discord guild from the projection.

    Args:
        guild_discord_id: Discord guild ID (snowflake)
        _db: Database session (reserved for future use)
        redis: Redis client for projection checks (optional)

    Returns:
        Guild display name

    Raises:
        HTTPException(503): If bot projection is not fresh
        HTTPException(500): If guild name not found in projection (data integrity issue)
    """
    if redis is None:
        redis = await get_redis_client()

    if not await member_projection.is_bot_fresh(redis=redis):
        logger.warning(
            "Bot projection not fresh when getting guild name for guild %s",
            guild_discord_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot is temporarily unavailable; please try again",
        )

    # Get guild name from projection - must be present if bot is fresh
    guild_name = await member_projection.get_guild_name(guild_discord_id, redis=redis)

    if guild_name is None:
        logger.error(
            "Guild name missing from projection for guild %s (data integrity issue)",
            guild_discord_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Guild data incomplete in projection",
        )

    return guild_name


async def require_bot_manager(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(  # noqa: B008
        auth.get_current_user
    ),
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        get_role_service
    ),
    db: AsyncSession = Depends(database.get_db),  # noqa: B008
) -> auth_schemas.CurrentUser:
    """
    Require user to have bot manager role for guild.

    Bot manager permission is determined by:
    1. Guild's bot_manager_role_ids configuration
    2. MANAGE_GUILD Discord permission as fallback

    Args:
        guild_id: Database guild UUID or Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user lacks bot manager role
    """

    async def check_bot_manager(user_id: str, guild_id: str, token: str) -> bool:
        return await role_service.check_bot_manager_permission(user_id, guild_id, db, token)

    return await _require_permission(
        guild_id,
        check_bot_manager,
        "Bot manager role required to perform this action",
        current_user,
        role_service,
        db,
    )


async def check_bot_manager_permission(
    guild_id: str,
    current_user: auth_schemas.CurrentUser,
    role_service: roles_module.RoleVerificationService,
    db: AsyncSession,
) -> bool:
    """
    Return True if user has bot manager permission (including maintainer bypass).

    Boolean wrapper around require_bot_manager for use in contexts that need a
    predicate rather than an exception-raising dependency.

    Args:
        guild_id: Database guild UUID or Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        True if user has bot manager permission or is a maintainer
    """
    try:
        await require_bot_manager(guild_id, current_user, role_service, db)
        return True
    except HTTPException:
        return False


async def require_game_host(
    guild_id: str,
    channel_id: str | None = None,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(  # noqa: B008
        auth.get_current_user
    ),
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        get_role_service
    ),
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if token_data.get("is_maintainer"):
        return current_user

    access_token = token_data["access_token"]

    has_permission = await role_service.check_game_host_permission(
        current_user.user.discord_id,
        guild_id,
        db,
        access_token=access_token,
    )

    if not has_permission:
        logger.warning(
            "User %s lacks game host permission in guild %s, channel %s",
            current_user.user.discord_id,
            guild_id,
            channel_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
    2. A Bot Manager (has bot_manager_role_ids or MANAGE_GUILD permission)

    Raises HTTPException with 404 if user not member of guild.

    Args:
        game_host_id: Discord ID of the game host
        guild_id: Discord guild ID
        current_user: Current authenticated user
        role_service: Role verification service
        db: Database session

    Returns:
        True if user can manage the game

    Raises:
        HTTPException: 404 if not guild member, to prevent information disclosure
    """
    # Verify guild membership first - returns 404 if not member
    await verify_guild_membership(guild_id, current_user, db)

    if current_user.user.discord_id == game_host_id:
        return True

    token_data = await tokens.get_user_tokens(current_user.session_token)
    if token_data and token_data.get("is_maintainer"):
        return True
    access_token = token_data["access_token"] if token_data else None

    return await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_id, db, access_token
    )


async def can_export_game(
    game_host_id: str,
    game_participants: list,
    guild_id: str,
    user_id: str,
    discord_id: str,
    role_service: roles_module.RoleVerificationService,
    db: AsyncSession,
    access_token: str | None = None,
    current_user: auth_schemas.CurrentUser | None = None,
) -> bool:
    """
    Check if user can export a game to calendar format.

    User can export game if they are:
    1. The game host
    2. A participant in the game
    3. A Bot Manager (has bot_manager_role_ids)
    4. An administrator (MANAGE_GUILD permission)

    Raises HTTPException with 404 if user not member of guild.

    Args:
        game_host_id: Database UUID of the game host
        game_participants: List of GameParticipant objects
        guild_id: Discord guild ID
        user_id: Database UUID of the user
        discord_id: Discord ID of the user
        role_service: Role verification service
        db: Database session
        access_token: OAuth2 access token (required for admin check)
        current_user: Current authenticated user (for guild membership check)

    Returns:
        True if user can export the game

    Raises:
        HTTPException: 404 if not guild member, to prevent information disclosure
    """
    # Verify guild membership first - returns 404 if not member
    if current_user:
        await verify_guild_membership(guild_id, current_user, db)

    # Check if user is the host
    if game_host_id == user_id:
        return True

    # Check if user is a participant
    if any(p.user_id == discord_id and p.user is not None for p in game_participants):
        return True

    # Check if user is bot manager or admin
    return await role_service.check_bot_manager_permission(discord_id, guild_id, db, access_token)


async def require_administrator(
    guild_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    current_user: auth_schemas.CurrentUser = Depends(  # noqa: B008
        auth.get_current_user
    ),
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        get_role_service
    ),
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if token_data.get("is_maintainer"):
        return current_user

    access_token = token_data["access_token"]

    has_permission = await role_service.has_permissions(
        current_user.user.discord_id,
        guild_id,
        access_token,
        DiscordPermissions.ADMINISTRATOR,
    )

    if not has_permission:
        logger.warning(
            "User %s lacks ADMINISTRATOR permission in guild %s",
            current_user.user.discord_id,
            guild_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need ADMINISTRATOR permission to perform this action",
        )

    return current_user
