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


"""Redis client wrapper for async operations."""

import json
import logging
import os
import secrets
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Awaitable

import redis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

logger = logging.getLogger(__name__)

_REDIS_ERROR_BACKOFF_BASE_MS = 1000
_REDIS_ERROR_BACKOFF_JITTER_MS = 250
_REDIS_CONNECTION_POOL_SIZE = 100

# Atomic Lua script for sliding-window rate limit tracking.
#
# Arguments: KEYS[1] = sorted-set key, ARGV[1] = current time in ms.
# Spacing table (seconds before next edit is allowed, indexed by window count):
#   n=0 → 0s, n=1 → 1s, n=2 → 1s, n=3 → 1.5s, n=4+ → 1.5s
#
# Returns the number of milliseconds the caller must sleep before editing
# (0 = proceed now).  When returning 0, atomically records the timestamp
# and resets the 5001ms expiry so the key disappears after 5s of inactivity.
_CHANNEL_RATE_LIMIT_LUA = """
local key     = KEYS[1]
local now_ms  = tonumber(ARGV[1])
local window  = 5000

redis.call('zremrangebyscore', key, 0, now_ms - window)

local n = redis.call('zcard', key)

local spacing_ms
if     n == 0 then spacing_ms = 0
elseif n == 1 then spacing_ms = 1000
elseif n == 2 then spacing_ms = 1000
elseif n == 3 then spacing_ms = 1500
else               spacing_ms = 1500
end

local wait_ms = 0

if n > 0 then
    local last_ts = tonumber(redis.call('zrange', key, -1, -1)[1])
    local spacing_wait = last_ts + spacing_ms - now_ms
    if spacing_wait > wait_ms then wait_ms = spacing_wait end
end

if n >= 5 then
    local oldest_ts = tonumber(redis.call('zrange', key, 0, 0)[1])
    local window_wait = oldest_ts + window - now_ms
    if window_wait > wait_ms then wait_ms = window_wait end
end

if wait_ms <= 0 then
    redis.call('zadd', key, now_ms, tostring(now_ms))
    redis.call('pexpire', key, 5001)
    return 0
end

return wait_ms
"""

# Atomic Lua script that claims one global token AND one per-channel slot in a
# single round-trip, preventing partial-claim races.
#
# KEYS[1] = global sorted-set key  ("discord:global_rate_limit")
# KEYS[2] = channel sorted-set key ("channel_rate_limit:{channel_id}")
# ARGV[1]  = current time in ms
# ARGV[2]  = per-channel max (default 5; pass a very large value for global-only callers)
#
# Global budget: 25 requests per 1000ms window (leaky bucket).
# Channel budget: ARGV[2] per 5000ms with inter-edit spacing.
#
# Returns 0 and records both timestamps when both budgets have capacity.
# Returns the larger wait (ms) and records nothing when either is exhausted.
_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA = """
local global_key    = KEYS[1]
local channel_key   = KEYS[2]
local now_ms        = tonumber(ARGV[1])
local ch_max        = tonumber(ARGV[2] or '5')

-- Global: 25 req per 1000ms sliding window
local global_window = 1000
local global_max    = 25
redis.call('zremrangebyscore', global_key, 0, now_ms - global_window)
local global_n      = redis.call('zcard', global_key)
local global_wait   = 0
if global_n >= global_max then
    local oldest_ts = tonumber(redis.call('zrange', global_key, 0, 0)[1])
    global_wait = oldest_ts + global_window - now_ms
    if global_wait < 1 then global_wait = 1 end
end

-- Channel: ch_max per 5000ms with inter-edit spacing (mirrors _CHANNEL_RATE_LIMIT_LUA)
local ch_window = 5000
redis.call('zremrangebyscore', channel_key, 0, now_ms - ch_window)
local ch_n = redis.call('zcard', channel_key)

local spacing_ms
if     ch_n == 0 then spacing_ms = 0
elseif ch_n == 1 then spacing_ms = 1000
elseif ch_n == 2 then spacing_ms = 1000
elseif ch_n == 3 then spacing_ms = 1500
else               spacing_ms = 1500
end

local ch_wait = 0
if ch_n > 0 then
    local last_ts = tonumber(redis.call('zrange', channel_key, -1, -1)[1])
    local spacing_wait = last_ts + spacing_ms - now_ms
    if spacing_wait > ch_wait then ch_wait = spacing_wait end
end
if ch_n >= ch_max then
    local oldest_ch = tonumber(redis.call('zrange', channel_key, 0, 0)[1])
    local window_wait = oldest_ch + ch_window - now_ms
    if window_wait > ch_wait then ch_wait = window_wait end
end

-- Return max wait; only record when both budgets are available
local wait_ms = global_wait
if ch_wait > wait_ms then wait_ms = ch_wait end

if wait_ms <= 0 then
    redis.call('zadd', global_key,  now_ms, tostring(now_ms))
    redis.call('pexpire', global_key, 1001)
    redis.call('zadd', channel_key, now_ms, tostring(now_ms))
    redis.call('pexpire', channel_key, 5001)
    return 0
end

return wait_ms
"""


class RedisClient:
    """Async Redis client wrapper with connection pooling."""

    def __init__(self, redis_url: str | None = None) -> None:
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
                max_connections=_REDIS_CONNECTION_POOL_SIZE,
                decode_responses=True,
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
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
            return await self._client.get(key)
        except Exception as e:
            logger.error("Redis GET error for key %s: %s", key, e)
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
            logger.error("Redis SET error for key %s: %s", key, e)
            return False

    async def get_json(self, key: str) -> Any | None:  # noqa: ANN401
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
            logger.error("Failed to decode JSON for key %s: %s", key, e)
            return None

    async def set_json(
        self,
        key: str,
        value: Any,  # noqa: ANN401
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
            logger.error("Failed to serialize JSON for key %s: %s", key, e)
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
            logger.error("Redis DELETE error for key %s: %s", key, e)
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
            logger.error("Redis EXISTS error for key %s: %s", key, e)
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
            return await self._client.expire(key, ttl)
        except Exception as e:
            logger.error("Redis EXPIRE error for key %s: %s", key, e)
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
            logger.error("Redis TTL error for key %s: %s", key, e)
            return -2

    async def claim_channel_rate_limit_slot(self, channel_id: str) -> int:
        """
        Claim a rate-limit slot for the given Discord channel.

        Uses a Redis sorted set (`channel_rate_limit:{channel_id}`) as a
        sliding 5-second window of recent edit timestamps.  Returns the number
        of milliseconds the caller should sleep before performing the Discord
        edit (0 = proceed immediately).  When returning 0 the timestamp is
        recorded atomically so subsequent callers see the updated window.

        Args:
            channel_id: Discord channel snowflake string.

        Returns:
            Milliseconds to wait before the edit is safe to send (0 = now).
        """
        if not self._client:
            await self.connect()

        key = f"channel_rate_limit:{channel_id}"
        now_ms = int(time.time() * 1000)

        try:
            raw = self._client.eval(_CHANNEL_RATE_LIMIT_LUA, 1, key, str(now_ms))
            result = await cast("Awaitable[Any]", raw)
            return int(result)
        except Exception as e:
            logger.error("Redis EVAL error for channel %s: %s", channel_id, e)
            return _REDIS_ERROR_BACKOFF_BASE_MS + secrets.randbelow(
                _REDIS_ERROR_BACKOFF_JITTER_MS + 1
            )

    async def claim_global_and_channel_slot(self, channel_id: str) -> int:
        """
        Atomically claim one global token and one per-channel slot.

        Uses a single Lua round-trip to enforce:
        - Global budget: 25 requests per 1000ms sliding window
        - Per-channel budget: 5 per 5000ms with inter-edit spacing

        Returns 0 and records both timestamps when both budgets have capacity.
        Returns the larger wait (ms) and records nothing when either is full,
        preventing partial-claim races.

        Args:
            channel_id: Discord channel snowflake string.

        Returns:
            Milliseconds to wait (0 = proceed immediately).
        """
        if not self._client:
            await self.connect()

        global_key = "discord:global_rate_limit"
        channel_key = f"channel_rate_limit:{channel_id}"
        now_ms = int(time.time() * 1000)

        try:
            raw = self._client.eval(
                _GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA,
                2,
                global_key,
                channel_key,
                str(now_ms),
                "5",
            )
            result = await cast("Awaitable[Any]", raw)
            return int(result)
        except Exception as e:
            logger.error(
                "Redis EVAL error for global+channel slot (channel=%s): %s",
                channel_id,
                e,
            )
            return _REDIS_ERROR_BACKOFF_BASE_MS + secrets.randbelow(
                _REDIS_ERROR_BACKOFF_JITTER_MS + 1
            )

    async def claim_global_slot(self) -> int:
        """
        Claim one global Discord rate-limit token without per-channel constraint.

        Uses the same combined Lua script as claim_global_and_channel_slot with
        a sentinel channel key and an impossibly high per-channel limit so only
        the 25 req/s global bucket is enforced.  Intended for API calls that
        have no meaningful Discord channel context (OAuth, guild/user fetches).

        Returns:
            Milliseconds to wait (0 = proceed immediately).
        """
        if not self._client:
            await self.connect()

        global_key = "discord:global_rate_limit"
        sentinel_key = "discord:_no_channel"
        now_ms = int(time.time() * 1000)

        try:
            raw = self._client.eval(
                _GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA,
                2,
                global_key,
                sentinel_key,
                str(now_ms),
                "999999",
            )
            result = await cast("Awaitable[Any]", raw)
            return int(result)
        except Exception as e:
            logger.error("Redis EVAL error for global slot: %s", e)
            return _REDIS_ERROR_BACKOFF_BASE_MS + secrets.randbelow(
                _REDIS_ERROR_BACKOFF_JITTER_MS + 1
            )


_redis_client: RedisClient | None = None


async def get_redis_client() -> RedisClient:
    """
    Get singleton Redis client instance.

    Returns:
        Initialized RedisClient instance.
    """
    global _redis_client  # noqa: PLW0603 - Singleton pattern for Redis client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client


class SyncRedisClient:
    """Synchronous Redis client for synchronous operations."""

    def __init__(self, redis_url: str | None = None) -> None:
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
            logger.error("Redis GET error for key %s: %s", key, e)
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
            logger.error("Redis SET error for key %s: %s", key, e)
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
    global _sync_redis_client  # noqa: PLW0603 - Singleton pattern for sync Redis client

    if _sync_redis_client is None:
        _sync_redis_client = SyncRedisClient()

    return _sync_redis_client
