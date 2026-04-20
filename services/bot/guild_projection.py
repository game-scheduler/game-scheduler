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


"""Bot-side projection writer and reader for Discord member data from gateway events."""

import json
import logging
from datetime import UTC, datetime

import discord
from opentelemetry import metrics

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.cache.operations import read_projection_key


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
    raw = await read_projection_key(redis, CacheKeys.proj_member, guild_id, uid)
    if raw is None:
        return []
    return json.loads(raw).get("roles", [])


logger = logging.getLogger(__name__)
meter = metrics.get_meter(__name__)

repopulation_started_counter = meter.create_counter(
    name="bot.projection.repopulation.started",
    description="Number of projection repopulation cycles started",
    unit="1",
)
repopulation_duration_histogram = meter.create_histogram(
    name="bot.projection.repopulation.duration",
    description="Duration of projection repopulation in seconds",
    unit="s",
)
repopulation_members_written_histogram = meter.create_histogram(
    name="bot.projection.repopulation.members_written",
    description="Number of members written in projection repopulation",
    unit="1",
)


async def _delete_old_generation(redis: RedisClient, prev_gen: str) -> None:
    """Delete all projection keys from the previous generation."""
    pattern = f"proj:*:{prev_gen}:*"
    cursor = 0
    while True:
        cursor, keys = await redis._client.scan(cursor, match=pattern, count=100)
        if keys:
            await redis._client.delete(*keys)
        if cursor == 0:
            break


async def _write_all_members(
    bot: discord.Client,
    redis: RedisClient,
    new_gen: str,
) -> tuple[int, dict[str, list[str]]]:
    """Write all member records and accumulate user->guild mapping.

    Returns:
        Tuple of (total_members_written, user_guild_map)
    """
    user_guild_map: dict[str, list[str]] = {}
    total_members_written = 0
    for guild in bot.guilds:
        guild_id = str(guild.id)
        for member in guild.members:
            uid = str(member.id)
            await write_member(redis=redis, gen=new_gen, guild_id=guild_id, uid=uid, member=member)
            total_members_written += 1
            user_guild_map.setdefault(uid, []).append(guild_id)
    return total_members_written, user_guild_map


async def repopulate_all(
    *,
    bot: discord.Client,
    redis: RedisClient,
    reason: str,
) -> None:
    """
    Repopulate entire member projection from bot gateway cache.

    Writes all member and user_guilds keys, then atomically flips the generation
    pointer to signal visibility. Old generation keys are cleaned up after the flip.

    Args:
        bot: Discord bot instance with guild cache
        redis: Redis async client
        reason: Reason for repopulation (e.g., "on_ready", "member_add")
    """
    start_time = datetime.now(UTC)
    repopulation_started_counter.add(1, {"reason": reason})

    new_gen = str(int(datetime.now(UTC).timestamp() * 1000))
    prev_gen = await redis.get(CacheKeys.proj_gen())

    total_members_written, user_guild_map = await _write_all_members(bot, redis, new_gen)

    for uid, guild_ids in user_guild_map.items():
        await write_user_guilds(redis=redis, gen=new_gen, uid=uid, guild_ids=guild_ids)

    # Write guild names for all guilds
    for guild in bot.guilds:
        await write_guild_name(
            redis=redis, gen=new_gen, guild_id=str(guild.id), guild_name=guild.name
        )

    # CRITICAL: Flip generation pointer AFTER all writes are complete.
    # Readers observing the new gen value are guaranteed to find all data present.
    await redis.set(CacheKeys.proj_gen(), new_gen)

    if prev_gen:
        await _delete_old_generation(redis, prev_gen)

    # Mark bot as fresh immediately — projection is now fully populated.
    # Without this, is_bot_fresh() returns False until the heartbeat task fires
    # (up to 30 seconds after on_ready), causing membership checks to deny access.
    await write_bot_last_seen(redis=redis)

    duration = (datetime.now(UTC) - start_time).total_seconds()
    repopulation_duration_histogram.record(duration, {"reason": reason})
    repopulation_members_written_histogram.record(total_members_written, {"reason": reason})

    logger.info(
        "Projection repopulation complete: %d members, %.2fs, reason=%s",
        total_members_written,
        duration,
        reason,
    )


async def write_member(
    *,
    redis: RedisClient,
    gen: str,
    guild_id: str,
    uid: str,
    member: discord.Member,
) -> None:
    """
    Write a single member record to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        guild_id: Discord guild ID
        uid: Discord user ID
        member: Discord Member object

    Raises:
        NotImplementedError: Function not yet implemented
    """
    member_data = {
        "roles": [str(role.id) for role in member.roles],
        "nick": member.nick,
        "global_name": member.global_name,
        "username": member.name,
        "avatar_url": member.avatar.url if member.avatar else None,
    }

    key = CacheKeys.proj_member(gen, guild_id, uid)
    await redis.set_json(key, member_data, ttl=None)

    usernames_key = CacheKeys.proj_usernames(gen, guild_id)
    names_seen: set[str] = set()
    for name in [member.name, member.global_name, member.nick]:
        if not name:
            continue
        name_lower = name.lower()
        if name_lower in names_seen:
            continue
        names_seen.add(name_lower)
        await redis._client.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})


async def write_user_guilds(
    *,
    redis: RedisClient,
    gen: str,
    uid: str,
    guild_ids: list[str],
) -> None:
    """
    Write the user's guild list to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        uid: Discord user ID
        guild_ids: List of guild IDs the user is in

    Raises:
        NotImplementedError: Function not yet implemented
    """
    key = CacheKeys.proj_user_guilds(gen, uid)
    await redis.set_json(key, guild_ids, ttl=None)


async def write_guild_name(
    *,
    redis: RedisClient,
    gen: str,
    guild_id: str,
    guild_name: str,
) -> None:
    """
    Write a guild name to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        guild_id: Discord guild ID
        guild_name: Guild name to store
    """
    key = CacheKeys.proj_guild_name(gen, guild_id)
    await redis.set(key, guild_name, ttl=None)


async def write_bot_last_seen(
    *,
    redis: RedisClient,
    heartbeat_interval: int = 30,
) -> None:
    """
    Write bot heartbeat timestamp.

    Args:
        redis: Redis async client
        heartbeat_interval: Heartbeat interval in seconds

    Raises:
        NotImplementedError: Function not yet implemented
    """
    timestamp = datetime.now(UTC).isoformat()
    ttl = heartbeat_interval * 3
    key = CacheKeys.bot_last_seen()
    await redis.set(key, timestamp, ttl=ttl)
