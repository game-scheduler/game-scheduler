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

Resolves Discord user IDs to guild-specific display names and avatar URLs
with Redis caching.
"""

import json
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
    """Service to resolve Discord user IDs to display names and avatar URLs."""

    def __init__(
        self,
        discord_api: discord_client.DiscordAPIClient,
        cache: cache_client.RedisClient,
    ):
        """
        Initialize display name resolver.

        Args:
            discord_api: Discord API client for fetching member data
            cache: Redis cache client for caching display names and avatars
        """
        self.discord_api = discord_api
        self.cache = cache

    @staticmethod
    def _build_avatar_url(
        user_id: str,
        guild_id: str,
        member_avatar: str | None,
        user_avatar: str | None,
        size: int = 64,
    ) -> str | None:
        """
        Build Discord CDN avatar URL with proper priority.

        Priority: guild member avatar > user avatar > None.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            member_avatar: Guild-specific avatar hash (optional)
            user_avatar: User's global avatar hash (optional)
            size: Image size in pixels (default 64)

        Returns:
            Discord CDN avatar URL or None if no avatar
        """
        if member_avatar:
            return f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{member_avatar}.png?size={size}"
        elif user_avatar:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png?size={size}"
        else:
            return None

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

    async def resolve_display_names_and_avatars(
        self, guild_id: str, user_ids: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """
        Resolve Discord user IDs to display names and avatar URLs.

        Checks cache first, then fetches uncached IDs from Discord API.
        Names are resolved using priority: nick > global_name > username.
        Avatar URLs use priority: guild member avatar > user avatar > None.

        Args:
            guild_id: Discord guild (server) ID
            user_ids: List of Discord user IDs to resolve

        Returns:
            Dictionary mapping user IDs to dicts with display_name and avatar_url
        """
        result = {}
        uncached_ids = []

        for user_id in user_ids:
            cache_key = cache_keys.CacheKeys.display_name_avatar(user_id, guild_id)
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    try:
                        result[user_id] = json.loads(cached)
                        continue
                    except (json.JSONDecodeError, TypeError):
                        pass
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

                    member_avatar = member.get("avatar")
                    user_avatar = member["user"].get("avatar")
                    avatar_url = self._build_avatar_url(
                        user_id, guild_id, member_avatar, user_avatar
                    )

                    user_data = {"display_name": display_name, "avatar_url": avatar_url}
                    result[user_id] = user_data

                    if self.cache:
                        cache_key = cache_keys.CacheKeys.display_name_avatar(user_id, guild_id)
                        await self.cache.set(
                            cache_key,
                            json.dumps(user_data),
                            ttl=cache_ttl.CacheTTL.DISPLAY_NAME,
                        )

                found_ids = {m["user"]["id"] for m in members}
                for user_id in uncached_ids:
                    if user_id not in found_ids:
                        user_data = {"display_name": "Unknown User", "avatar_url": None}
                        result[user_id] = user_data

            except discord_client.DiscordAPIError as e:
                logger.error(f"Failed to fetch display names and avatars: {e}")
                for user_id in uncached_ids:
                    user_data = {
                        "display_name": f"User#{user_id[-4:]}",
                        "avatar_url": None,
                    }
                    result[user_id] = user_data

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


async def get_display_name_resolver() -> DisplayNameResolver:
    """Get display name resolver instance with initialized dependencies."""
    discord_api = discord_client.get_discord_client()
    cache = await cache_client.get_redis_client()
    return DisplayNameResolver(discord_api, cache)
