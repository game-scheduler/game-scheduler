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
Role verification service for API authentication.

Provides role checking using Discord API and Redis caching for web dashboard.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.dependencies.discord import get_discord_client
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import projection as member_projection
from shared.cache import ttl as cache_ttl
from shared.cache.operations import CacheOperation, cache_get
from shared.models import guild as guild_model
from shared.utils.discord import DiscordPermissions

logger = logging.getLogger(__name__)


class RoleVerificationService:
    """Service for verifying user roles and permissions via Discord API."""

    def __init__(self) -> None:
        """Initialize role verification service."""
        self.discord_client = get_discord_client()
        self._cache: cache_client.RedisClient | None = None

    async def _get_cache(self) -> cache_client.RedisClient:
        """Get or initialize cache client."""
        if self._cache is None:
            self._cache = await cache_client.get_redis_client()
        return self._cache

    async def get_user_role_ids(
        self, user_id: str, guild_id: str, force_refresh: bool = False
    ) -> list[str]:
        """
        Get user's role IDs with caching.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            force_refresh: Skip cache and fetch from Discord API

        Returns:
            List of role IDs user has in guild
        """
        cache = await self._get_cache()
        cache_key = cache_keys.CacheKeys.user_roles(user_id, guild_id)

        if not force_refresh:
            cached_roles_raw = await cache_get(cache_key, CacheOperation.USER_ROLES_API)
            if cached_roles_raw is not None and isinstance(cached_roles_raw, list):
                # Type narrowing: cached roles is a list (should contain string role IDs)
                return cached_roles_raw

        role_ids = await member_projection.get_user_roles(guild_id, user_id, redis=cache)

        # Add @everyone role (which has the same ID as the guild)
        # Discord doesn't include it in the roles array but every member has it
        if guild_id not in role_ids:
            role_ids.append(guild_id)

        await cache.set_json(cache_key, role_ids, ttl=cache_ttl.CacheTTL.USER_ROLES)
        return role_ids

    def _find_guild_data(self, guilds: list[dict], guild_id: str) -> dict | None:
        """
        Find guild data in list of guilds.

        Args:
            guilds: List of guild data dictionaries
            guild_id: Discord guild ID to find

        Returns:
            Guild data dict if found, None otherwise
        """
        for guild_data in guilds:
            if guild_data["id"] == guild_id:
                return guild_data
        return None

    def _has_administrator_permission(self, user_permissions: int) -> bool:
        """
        Check if user has ADMINISTRATOR permission.

        Args:
            user_permissions: User's permission flags as integer

        Returns:
            True if user has ADMINISTRATOR permission
        """
        return bool(user_permissions & DiscordPermissions.ADMINISTRATOR)

    def _has_any_requested_permission(
        self, user_permissions: int, permissions: tuple[int, ...]
    ) -> bool:
        """
        Check if user has any of the requested permissions.

        Args:
            user_permissions: User's permission flags as integer
            permissions: Tuple of permission flags to check

        Returns:
            True if user has any of the requested permissions
        """
        return any(user_permissions & permission for permission in permissions)

    async def has_permissions(
        self, user_id: str, guild_id: str, access_token: str, *permissions: int
    ) -> bool:
        """
        Check if user has any of the specified permissions in a guild.

        ADMINISTRATOR permission always grants access as it includes all permissions.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            access_token: User's OAuth2 access token
            *permissions: One or more permission flags to check
                (e.g., DiscordPermissions.MANAGE_GUILD)

        Returns:
            True if user has ADMINISTRATOR or any of the specified permissions
        """
        try:
            guilds = await self.discord_client.get_guilds(token=access_token, user_id=user_id)
            guild_data = self._find_guild_data(guilds, guild_id)

            if not guild_data:
                return False

            user_permissions = int(guild_data.get("permissions", 0))

            if self._has_administrator_permission(user_permissions):
                return True

            return self._has_any_requested_permission(user_permissions, permissions)

        except Exception as e:
            logger.error("Error checking permissions: %s", e)
            return False

    async def has_any_role(
        self,
        user_id: str,
        guild_id: str,
        role_ids: list[str],
    ) -> bool:
        """
        Check if user has any of the specified roles in a guild.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            role_ids: List of role IDs to check for

        Returns:
            True if user has at least one of the specified roles
        """
        if not role_ids:
            return False

        user_role_ids = await self.get_user_role_ids(user_id, guild_id)
        return any(role_id in role_ids for role_id in user_role_ids)

    async def check_game_host_permission(
        self,
        user_id: str,
        guild_id: str,
        db: AsyncSession,
        allowed_host_role_ids: list[str] | None = None,
        access_token: str | None = None,
    ) -> bool:
        """
        Check if user can host games with optional template role restrictions.

        Checks both bot manager permissions (MANAGE_GUILD or bot_manager_role_ids)
        and template-specific role requirements.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            db: Database session for configuration queries
            allowed_host_role_ids: Template's allowed host role IDs (None or [] = managers only)
            access_token: User's OAuth2 access token

        Returns:
            True if user can host games with this template
        """
        # Bot managers can always host
        is_bot_manager = await self.check_bot_manager_permission(
            user_id, guild_id, db, access_token
        )
        if is_bot_manager:
            return True

        # If no roles specified (None or empty list), only managers can host
        if not allowed_host_role_ids:
            return False

        # Check if user has one of the required roles
        user_role_ids = await self.get_user_role_ids(user_id, guild_id)
        return any(role_id in allowed_host_role_ids for role_id in user_role_ids)

    async def check_bot_manager_permission(
        self,
        user_id: str,
        guild_id: str,
        db: AsyncSession,
        access_token: str | None = None,
    ) -> bool:
        """
        Check if user has Bot Manager role in guild.

        Bot Managers can edit/delete any game in the guild.
        Falls back to MANAGE_GUILD permission if no Bot Manager roles configured.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            db: Database session for configuration queries
            access_token: User's OAuth2 access token (required if no Bot Manager roles configured)

        Returns:
            True if user has Bot Manager role or MANAGE_GUILD permission
        """
        user_role_ids = await self.get_user_role_ids(user_id, guild_id)

        result = await db.execute(
            select(guild_model.GuildConfiguration).where(
                guild_model.GuildConfiguration.guild_id == guild_id
            )
        )
        guild_config = result.scalar_one_or_none()

        if not guild_config or not guild_config.bot_manager_role_ids:
            if access_token:
                return await self.has_permissions(
                    user_id, guild_id, access_token, DiscordPermissions.MANAGE_GUILD
                )
            return False

        return any(role_id in guild_config.bot_manager_role_ids for role_id in user_role_ids)

    async def invalidate_user_roles(self, user_id: str, guild_id: str) -> None:
        """
        Invalidate cached user roles.

        Call this after operations that may change user permissions.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
        """
        cache = await self._get_cache()
        cache_key = cache_keys.CacheKeys.user_roles(user_id, guild_id)
        await cache.delete(cache_key)


_role_service_instance: RoleVerificationService | None = None


def get_role_service() -> RoleVerificationService:
    """Get role verification service singleton."""
    global _role_service_instance  # noqa: PLW0603 - Singleton pattern for service instance
    if _role_service_instance is None:
        _role_service_instance = RoleVerificationService()
    return _role_service_instance
