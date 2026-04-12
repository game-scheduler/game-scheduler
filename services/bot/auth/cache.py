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
Role caching wrapper for Redis.

Provides caching of Discord user roles to reduce API calls.
"""

import json
import logging

from shared.cache import client, keys, ttl
from shared.cache.operations import CacheOperation, cache_get

logger = logging.getLogger(__name__)


class RoleCache:
    """Redis cache wrapper for Discord user roles."""

    def __init__(self, redis: client.RedisClient | None = None) -> None:
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
            cache_key = keys.CacheKeys.user_roles(user_id, guild_id)
            cached = await cache_get(cache_key, CacheOperation.USER_ROLES_BOT)

            if cached is not None:
                logger.debug("Cache hit for user roles: %s in guild %s", user_id, guild_id)
                return cached

            logger.debug("Cache miss for user roles: %s in guild %s", user_id, guild_id)
            return None

        except Exception as e:
            logger.error("Error getting cached roles: %s", e)
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
            logger.debug("Cached roles for user %s in guild %s", user_id, guild_id)

        except Exception as e:
            logger.error("Error caching roles: %s", e)

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
            logger.debug("Invalidated role cache for user %s in guild %s", user_id, guild_id)

        except Exception as e:
            logger.error("Error invalidating role cache: %s", e)

    async def get_guild_roles(self, guild_id: str) -> list[dict] | None:
        """
        Get cached guild roles from Redis.

        Args:
            guild_id: Discord guild ID

        Returns:
            List of role dicts if cached, None if not found
        """
        try:
            cache_key = keys.CacheKeys.guild_config(guild_id)
            cached = await cache_get(cache_key, CacheOperation.GUILD_ROLES_BOT)

            if cached is not None:
                logger.debug("Cache hit for guild roles: %s", guild_id)
                return cached

            logger.debug("Cache miss for guild roles: %s", guild_id)
            return None

        except Exception as e:
            logger.error("Error getting cached guild roles: %s", e)
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
            logger.debug("Cached guild roles for %s", guild_id)

        except Exception as e:
            logger.error("Error caching guild roles: %s", e)
