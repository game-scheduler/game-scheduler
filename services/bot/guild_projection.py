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
from redis.asyncio.client import Pipeline

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
    """Delete all projection keys from the previous generation.

    Collects all matching keys via SCAN first, then deletes in a single pipeline
    to avoid one round-trip per key batch.
    """
    pattern = f"proj:*:{prev_gen}:*"
    all_keys: list[bytes] = []
    cursor = 0
    while True:
        cursor, keys = await redis._client.scan(cursor, match=pattern, count=500)
        all_keys.extend(keys)
        if cursor == 0:
            break
    if not all_keys:
        return
    async with redis._client.pipeline(transaction=False) as pipe:
        for i in range(0, len(all_keys), 1000):
            pipe.delete(*all_keys[i : i + 1000])
        await pipe.execute()


def _build_member_data(member: discord.Member) -> dict[str, object]:
    return {
        "roles": [str(role.id) for role in member.roles],
        "nick": member.nick,
        "global_name": member.global_name,
        "username": member.name,
        "avatar_url": member.avatar.url if member.avatar else None,
    }


def _member_username_variants(member: discord.Member) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in [member.name, member.global_name, member.nick]:
        if not name:
            continue
        lower = name.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(lower)
    return result


def _queue_member_to_pipe(
    pipe: Pipeline,
    gen: str,
    guild_id: str,
    uid: str,
    member: discord.Member,
) -> None:
    """Queue a single member write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_member(gen, guild_id, uid)
    pipe.set(key, json.dumps(_build_member_data(member)))

    usernames_key = CacheKeys.proj_usernames(gen, guild_id)
    for name_lower in _member_username_variants(member):
        pipe.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})


def _queue_user_guilds_to_pipe(
    pipe: Pipeline,
    gen: str,
    uid: str,
    guild_ids: list[str],
) -> None:
    """Queue a user-guilds write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_user_guilds(gen, uid)
    pipe.set(key, json.dumps(guild_ids))


def _queue_guild_name_to_pipe(
    pipe: Pipeline,
    gen: str,
    guild_id: str,
    guild_name: str,
) -> None:
    """Queue a guild-name write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_guild_name(gen, guild_id)
    pipe.set(key, guild_name)


async def _write_all_members(
    bot: discord.Client,
    redis: RedisClient,
    new_gen: str,
) -> tuple[int, dict[str, list[str]]]:
    """Write all member records and accumulate user->guild mapping via a single pipeline.

    Returns:
        Tuple of (total_members_written, user_guild_map)
    """
    user_guild_map: dict[str, list[str]] = {}
    total_members_written = 0

    async with redis._client.pipeline(transaction=False) as pipe:
        for guild in bot.guilds:
            guild_id = str(guild.id)
            _queue_guild_name_to_pipe(pipe, new_gen, guild_id, guild.name)
            for member in guild.members:
                uid = str(member.id)
                _queue_member_to_pipe(pipe, new_gen, guild_id, uid, member)
                total_members_written += 1
                user_guild_map.setdefault(uid, []).append(guild_id)

        for uid, guild_ids in user_guild_map.items():
            _queue_user_guilds_to_pipe(pipe, new_gen, uid, guild_ids)

        await pipe.execute()

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

    total_members_written, _ = await _write_all_members(bot, redis, new_gen)

    # CRITICAL: Flip generation pointer AFTER all writes are complete.
    # Readers observing the new gen value are guaranteed to find all data present.
    await redis.set(CacheKeys.proj_gen(), new_gen)

    # Mark bot as fresh immediately — projection is now fully populated.
    # Without this, is_bot_fresh() returns False until the heartbeat task fires
    # (up to 30 seconds after on_ready), causing membership checks to deny access.
    await write_bot_last_seen(redis=redis)

    write_duration = (datetime.now(UTC) - start_time).total_seconds()
    repopulation_duration_histogram.record(write_duration, {"reason": reason})
    repopulation_members_written_histogram.record(total_members_written, {"reason": reason})

    logger.info(
        "Projection repopulation complete: %d members, %.2fs, reason=%s",
        total_members_written,
        write_duration,
        reason,
    )

    if prev_gen:
        delete_start = datetime.now(UTC)
        await _delete_old_generation(redis, prev_gen)
        delete_duration = (datetime.now(UTC) - delete_start).total_seconds()
        logger.info("Projection old-gen cleanup: %.2fs, gen=%s", delete_duration, prev_gen)


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
    key = CacheKeys.proj_member(gen, guild_id, uid)
    await redis.set_json(key, _build_member_data(member), ttl=None)

    usernames_key = CacheKeys.proj_usernames(gen, guild_id)
    for name_lower in _member_username_variants(member):
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
