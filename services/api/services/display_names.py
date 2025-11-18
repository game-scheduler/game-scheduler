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
Display name resolution service for Discord users.

Resolves Discord user IDs to guild-specific display names with Redis caching.
"""

import logging
from typing import TYPE_CHECKING

from services.api.auth import discord_client
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl as cache_ttl

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DisplayNameResolver:
    """Service to resolve Discord user IDs to display names."""

    def __init__(
        self,
        discord_api: discord_client.DiscordAPIClient,
        cache: cache_client.RedisClient,
    ):
        """
        Initialize display name resolver.

        Args:
            discord_api: Discord API client for fetching member data
            cache: Redis cache client for caching display names
        """
        self.discord_api = discord_api
        self.cache = cache

    async def resolve_display_names(self, guild_id: str, user_ids: list[str]) -> dict[str, str]:
        """
        Resolve Discord user IDs to display names for a guild.

        Checks cache first, then fetches uncached IDs from Discord API.
        Names are resolved using priority: nick > global_name > username.

        Args:
            guild_id: Discord guild (server) ID
            user_ids: List of Discord user IDs to resolve

        Returns:
            Dictionary mapping user IDs to display names
        """
        result = {}
        uncached_ids = []

        for user_id in user_ids:
            cache_key = cache_keys.CacheKeys.display_name(user_id, guild_id)
            cached = await self.cache.get(cache_key)
            if cached:
                result[user_id] = cached
            else:
                uncached_ids.append(user_id)

        if uncached_ids:
            try:
                members = await self.discord_api.get_guild_members_batch(guild_id, uncached_ids)

                for member in members:
                    user_id = member["user"]["id"]
                    display_name = (
                        member.get("nick")
                        or member["user"].get("global_name")
                        or member["user"]["username"]
                    )
                    result[user_id] = display_name

                    cache_key = cache_keys.CacheKeys.display_name(user_id, guild_id)
                    await self.cache.set(
                        cache_key, display_name, ttl=cache_ttl.CacheTTL.DISPLAY_NAME
                    )

                found_ids = {m["user"]["id"] for m in members}
                for user_id in uncached_ids:
                    if user_id not in found_ids:
                        result[user_id] = "Unknown User"

            except discord_client.DiscordAPIError as e:
                logger.error(f"Failed to fetch display names: {e}")
                for user_id in uncached_ids:
                    result[user_id] = f"User#{user_id[-4:]}"

        return result

    async def resolve_single(self, guild_id: str, user_id: str) -> str:
        """
        Resolve single user display name.

        Args:
            guild_id: Discord guild (server) ID
            user_id: Discord user ID to resolve

        Returns:
            Display name for the user
        """
        result = await self.resolve_display_names(guild_id, [user_id])
        return result.get(user_id, "Unknown User")


_resolver_instance: DisplayNameResolver | None = None


def get_display_name_resolver() -> DisplayNameResolver:
    """Get display name resolver singleton."""
    global _resolver_instance
    if _resolver_instance is None:
        discord_api = discord_client.get_discord_client()
        cache = cache_client.get_redis_client()
        _resolver_instance = DisplayNameResolver(discord_api, cache)
    return _resolver_instance
