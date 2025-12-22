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
Role verification service for API authentication.

Provides role checking using Discord API and Redis caching for web dashboard.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.dependencies.discord import get_discord_client
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl as cache_ttl
from shared.discord import client as discord_client
from shared.models import guild as guild_model
from shared.utils.discord import DiscordPermissions

logger = logging.getLogger(__name__)


class RoleVerificationService:
    """Service for verifying user roles and permissions via Discord API."""

    def __init__(self):
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
            cached_roles = await cache.get_json(cache_key)
            if cached_roles is not None:
                return cached_roles

        try:
            member_data = await self.discord_client.get_guild_member(guild_id, user_id)
            role_ids = member_data.get("roles", [])

            # Add @everyone role (which has the same ID as the guild)
            # Discord doesn't include it in the roles array but every member has it
            if guild_id not in role_ids:
                role_ids.append(guild_id)

            await cache.set_json(cache_key, role_ids, ttl=cache_ttl.CacheTTL.USER_ROLES)
            return role_ids

        except discord_client.DiscordAPIError as e:
            logger.warning(f"Failed to fetch user roles for {user_id} in guild {guild_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching user roles: {e}")
            return []

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

            for guild_data in guilds:
                if guild_data["id"] == guild_id:
                    user_permissions = int(guild_data.get("permissions", 0))

                    # ADMINISTRATOR grants all permissions
                    if user_permissions & DiscordPermissions.ADMINISTRATOR:
                        return True

                    # Check if user has any of the requested permissions
                    for permission in permissions:
                        if user_permissions & permission:
                            return True

                    return False

            return False

        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
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
    global _role_service_instance
    if _role_service_instance is None:
        _role_service_instance = RoleVerificationService()
    return _role_service_instance
