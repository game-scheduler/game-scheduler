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


"""Reader for the Discord member projection stored in Redis."""

import json
import logging
from datetime import UTC, datetime, timedelta

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.cache.operations import read_projection_key

logger = logging.getLogger(__name__)

_BOT_FRESHNESS_SECONDS = 120


async def get_user_guilds(uid: str, *, redis: RedisClient) -> list[str] | None:
    """
    Get the list of guild IDs the user belongs to from the projection.

    Args:
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        List of guild ID strings, or None if absent
    """
    raw = await read_projection_key(redis, CacheKeys.proj_user_guilds, uid)
    if raw is None:
        return None
    return json.loads(raw)


async def get_member(guild_id: str, uid: str, *, redis: RedisClient) -> dict | None:
    """
    Get member data for a user in a guild from the projection.

    Args:
        guild_id: Discord guild ID
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        Member dict with keys: roles, nick, global_name, username, avatar_url;
        or None if absent
    """
    raw = await read_projection_key(redis, CacheKeys.proj_member, guild_id, uid)
    if raw is None:
        return None
    return json.loads(raw)


async def get_user_roles(guild_id: str, uid: str, *, redis: RedisClient) -> list[str]:
    """
    Get the role IDs for a user in a guild from the projection.

    Args:
        guild_id: Discord guild ID
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        List of role ID strings, empty list if member absent
    """
    member = await get_member(guild_id, uid, redis=redis)
    if member is None:
        return []
    return member.get("roles", [])


async def get_guild_name(guild_id: str, *, redis: RedisClient) -> str | None:
    """
    Get the guild name from the projection.

    Args:
        guild_id: Discord guild ID
        redis: Redis async client wrapper

    Returns:
        Guild name string, or None if absent
    """
    return await read_projection_key(redis, CacheKeys.proj_guild_name, guild_id)


async def is_bot_fresh(*, redis: RedisClient) -> bool:
    """
    Check whether the bot projection is fresh (bot heartbeat recently seen).

    Args:
        redis: Redis async client wrapper

    Returns:
        True if bot:last_seen key exists and timestamp is within acceptable age
    """
    raw = await redis.get(CacheKeys.bot_last_seen())
    if raw is None:
        return False
    try:
        last_seen = datetime.fromisoformat(raw)
        age = datetime.now(UTC) - last_seen
        return age < timedelta(seconds=_BOT_FRESHNESS_SECONDS)
    except ValueError:
        return False


async def search_members_by_prefix(
    guild_id: str,
    query: str,
    *,
    redis: RedisClient,
) -> list[dict]:
    """
    Search guild members whose username, global_name, or nick starts with query.

    Uses ZRANGEBYLEX on the proj:usernames sorted set for O(log N + M) prefix
    queries without any Discord REST calls. Deduplicates via seen_uids so a
    member matching on multiple name fields appears only once.

    Args:
        guild_id: Discord guild ID
        query: Prefix string to match (case-insensitive)
        redis: Redis async client wrapper

    Returns:
        List of member dicts (with added "uid" field), empty list if gen absent
        or no matches
    """
    gen = await redis.get(CacheKeys.proj_gen())
    if not gen:
        return []

    key = CacheKeys.proj_usernames(gen, guild_id)
    q = query.lower()
    if not redis._client:
        await redis.connect()
    entries = await redis._client.zrangebylex(key, f"[{q}", f"[{q}\xff")

    results: list[dict] = []
    seen_uids: set[str] = set()
    for entry in entries:
        _name, uid = entry.rsplit("\x00", 1)
        if uid not in seen_uids:
            seen_uids.add(uid)
            member = await get_member(guild_id, uid, redis=redis)
            if member:
                results.append({"uid": uid, **member})
    return results
