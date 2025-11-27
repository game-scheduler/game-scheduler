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


"""Redis client wrapper for async operations."""

import json
import logging
import os
from typing import Any

import redis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with connection pooling."""

    def __init__(self, redis_url: str | None = None):
        """
        Initialize Redis client with connection pool.

        Args:
            redis_url: Redis connection URL (default from REDIS_URL env var).
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0",
        )
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Establish Redis connection with pooling."""
        if self._client is not None:
            return

        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=10,
                decode_responses=True,
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection and cleanup pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None
        logger.info("Redis connection closed")

    async def get(self, key: str) -> str | None:
        """
        Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        if not self._client:
            await self.connect()

        try:
            value = await self._client.get(key)
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (optional).

        Returns:
            True if successful, False otherwise.
        """
        if not self._client:
            await self.connect()

        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get_json(self, key: str) -> Any | None:
        """
        Get JSON value from cache.

        Args:
            key: Cache key.

        Returns:
            Deserialized JSON value or None if not found.
        """
        value = await self.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key {key}: {e}")
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set JSON value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to serialize and cache.
            ttl: Time-to-live in seconds (optional).

        Returns:
            True if successful, False otherwise.
        """
        try:
            serialized = json.dumps(value)
            return await self.set(key, serialized, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize JSON for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if key was deleted, False otherwise.
        """
        if not self._client:
            await self.connect()

        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if key exists, False otherwise.
        """
        if not self._client:
            await self.connect()

        try:
            result = await self._client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL for existing key.

        Args:
            key: Cache key.
            ttl: Time-to-live in seconds.

        Returns:
            True if TTL was set, False otherwise.
        """
        if not self._client:
            await self.connect()

        try:
            result = await self._client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Args:
            key: Cache key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist.
        """
        if not self._client:
            await self.connect()

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -2


_redis_client: RedisClient | None = None


async def get_redis_client() -> RedisClient:
    """
    Get singleton Redis client instance.

    Returns:
        Initialized RedisClient instance.
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client


class SyncRedisClient:
    """Synchronous Redis client for Celery tasks."""

    def __init__(self, redis_url: str | None = None):
        """
        Initialize synchronous Redis client.

        Args:
            redis_url: Redis connection URL (default from REDIS_URL env var).
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0",
        )
        self._client = redis.from_url(
            self.redis_url,
            max_connections=10,
            decode_responses=True,
        )

    def get(self, key: str) -> str | None:
        """Get value from cache."""
        try:
            return self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if ttl:
                self._client.setex(key, ttl, value)
            else:
                self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()


_sync_redis_client: SyncRedisClient | None = None


def get_sync_redis_client() -> SyncRedisClient:
    """
    Get singleton synchronous Redis client instance.

    Returns:
        Initialized SyncRedisClient instance.
    """
    global _sync_redis_client

    if _sync_redis_client is None:
        _sync_redis_client = SyncRedisClient()

    return _sync_redis_client
