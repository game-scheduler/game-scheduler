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
Role caching wrapper for Redis.

Provides caching of Discord user roles to reduce API calls.
"""

import json
import logging

from shared.cache import client, keys, ttl

logger = logging.getLogger(__name__)


class RoleCache:
    """Redis cache wrapper for Discord user roles."""

    def __init__(self, redis: client.RedisClient | None = None):
        """
        Initialize role cache.

        Args:
            redis: Redis client instance. Uses global client if not provided.
        """
        self._redis = redis

    async def get_redis(self) -> client.RedisClient:
        """Get Redis client instance."""
        if self._redis is None:
            self._redis = await client.get_redis_client()
        return self._redis

    async def get_user_roles(self, user_id: str, guild_id: str) -> list[str] | None:
        """
        Get cached user roles from Redis.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            List of role IDs if cached, None if not found
        """
        try:
            redis = await self.get_redis()
            cache_key = keys.CacheKeys.user_roles(user_id, guild_id)
            cached = await redis.get(cache_key)

            if cached:
                role_ids = json.loads(cached)
                logger.debug(f"Cache hit for user roles: {user_id} in guild {guild_id}")
                return role_ids

            logger.debug(f"Cache miss for user roles: {user_id} in guild {guild_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting cached roles: {e}")
            return None

    async def set_user_roles(self, user_id: str, guild_id: str, role_ids: list[str]) -> None:
        """
        Cache user roles in Redis with TTL.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            role_ids: List of Discord role IDs
        """
        try:
            redis = await self.get_redis()
            cache_key = keys.CacheKeys.user_roles(user_id, guild_id)
            await redis.set(cache_key, json.dumps(role_ids), ttl=ttl.CacheTTL.USER_ROLES)
            logger.debug(f"Cached roles for user {user_id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error caching roles: {e}")

    async def invalidate_user_roles(self, user_id: str, guild_id: str) -> None:
        """
        Invalidate cached user roles.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
        """
        try:
            redis = await self.get_redis()
            cache_key = keys.CacheKeys.user_roles(user_id, guild_id)
            await redis.delete(cache_key)
            logger.debug(f"Invalidated role cache for user {user_id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error invalidating role cache: {e}")

    async def get_guild_roles(self, guild_id: str) -> list[dict] | None:
        """
        Get cached guild roles from Redis.

        Args:
            guild_id: Discord guild ID

        Returns:
            List of role dicts if cached, None if not found
        """
        try:
            redis = await self.get_redis()
            cache_key = keys.CacheKeys.guild_config(guild_id)
            cached = await redis.get(cache_key)

            if cached:
                roles = json.loads(cached)
                logger.debug(f"Cache hit for guild roles: {guild_id}")
                return roles

            logger.debug(f"Cache miss for guild roles: {guild_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting cached guild roles: {e}")
            return None

    async def set_guild_roles(self, guild_id: str, roles: list[dict]) -> None:
        """
        Cache guild roles in Redis with TTL.

        Args:
            guild_id: Discord guild ID
            roles: List of Discord role dicts
        """
        try:
            redis = await self.get_redis()
            cache_key = keys.CacheKeys.guild_config(guild_id)
            await redis.set(cache_key, json.dumps(roles), ttl=ttl.CacheTTL.GUILD_CONFIG)
            logger.debug(f"Cached guild roles for {guild_id}")

        except Exception as e:
            logger.error(f"Error caching guild roles: {e}")
