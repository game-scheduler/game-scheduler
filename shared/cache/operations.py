# Copyright 2026 Bret McKee
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


"""Cache operation names, generic hit/miss counters, latency histogram, and projection reads."""

import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from opentelemetry import metrics

from shared.cache.client import RedisClient, get_redis_client
from shared.cache.keys import CacheKeys

_meter = metrics.get_meter(__name__)
_hit_counter = _meter.create_counter("cache.hits", description="Cache hits", unit="1")
_miss_counter = _meter.create_counter("cache.misses", description="Cache misses", unit="1")
_duration_histogram = _meter.create_histogram("cache.duration", unit="s")

_proj_read_retry_counter = _meter.create_counter(
    name="cache.projection.read.retries",
    description="Number of gen-rotation retries during projection reads",
    unit="1",
)
_proj_read_not_found_counter = _meter.create_counter(
    name="cache.projection.read.not_found",
    description="Number of stable-gen misses during projection reads",
    unit="1",
)

_MAX_GEN_RETRIES = 3


class CacheOperation(StrEnum):
    """Symbolic names for every cache read site in the codebase."""

    FETCH_GUILD = "fetch_guild"
    FETCH_CHANNEL = "fetch_channel"
    FETCH_GUILD_ROLES = "fetch_guild_roles"
    FETCH_GUILD_CHANNELS = "fetch_guild_channels"
    GET_APPLICATION_INFO = "get_application_info"
    USER_ROLES_API = "user_roles_api"
    DISPLAY_NAME = "display_name"
    SESSION_LOOKUP = "session_lookup"
    SESSION_REFRESH = "session_refresh"
    OAUTH_STATE = "oauth_state"
    USER_ROLES_BOT = "user_roles_bot"
    GUILD_ROLES_BOT = "guild_roles_bot"


async def cache_get(key: str, operation: CacheOperation) -> Any | None:  # noqa: ANN401
    """
    Read a JSON value from Redis and record hit/miss counter and latency.

    Args:
        key: Redis cache key.
        operation: Symbolic operation name used as the metric label.

    Returns:
        Deserialized value on hit, None on miss.
    """
    redis = await get_redis_client()
    t0 = time.monotonic()
    result = await redis.get_json(key)
    hit = result is not None
    (_hit_counter if hit else _miss_counter).add(1, {"operation": operation})
    _duration_histogram.record(
        time.monotonic() - t0,
        {"operation": operation, "result": "hit" if hit else "miss"},
    )
    return result


async def read_projection_key(
    redis: RedisClient, key_fn: Callable[..., str], *key_args: str
) -> str | None:
    """
    Read a projection key with generation-rotation retry.

    Handles the window where the gen pointer has flipped to a new value but
    the caller's key was constructed with the old value. Retries up to
    _MAX_GEN_RETRIES times before giving up.

    Args:
        redis: Redis async client wrapper
        key_fn: Key factory function (e.g., CacheKeys.proj_member)
        *key_args: Arguments to pass to key_fn after the gen argument

    Returns:
        Cached value string, or None if absent
    """
    gen = await redis.get(CacheKeys.proj_gen())
    for _ in range(_MAX_GEN_RETRIES):
        value = await redis.get(key_fn(gen, *key_args))
        if value is not None:
            return value
        gen2 = await redis.get(CacheKeys.proj_gen())
        if gen == gen2:
            _proj_read_not_found_counter.add(1)
            return None
        _proj_read_retry_counter.add(1)
        gen = gen2
    return None
