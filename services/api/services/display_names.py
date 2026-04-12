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
Display name resolution service for Discord users.

Resolves Discord user IDs to guild-specific display names and avatar URLs
with Redis caching.
"""

import json
import logging

from services.api.dependencies.discord import get_discord_client
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl as cache_ttl
from shared.cache.operations import CacheOperation, cache_get
from shared.discord import client as discord_client

logger = logging.getLogger(__name__)


class DisplayNameResolver:
    """Service to resolve Discord user IDs to display names and avatar URLs."""

    def __init__(
        self,
        discord_api: discord_client.DiscordAPIClient,
        cache: cache_client.RedisClient,
    ) -> None:
        """
        Initialize display name resolver.

        Args:
            discord_api: Discord API client for fetching member data
            cache: Redis cache client for caching display names and avatars
        """
        self.discord_api = discord_api
        self.cache = cache

    @staticmethod
    def _resolve_display_name(member: dict) -> str:
        """
        Resolve display name from Discord member data.

        Args:
            member: Discord member dictionary with 'user' and optional 'nick'

        Returns:
            Display name using fallback: nick -> global_name -> username
        """
        return member.get("nick") or member["user"].get("global_name") or member["user"]["username"]

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
        if user_avatar:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png?size={size}"
        return None

    async def _fetch_and_cache_display_names(
        self, guild_id: str, uncached_ids: list[str]
    ) -> dict[str, str]:
        """
        Fetch display names from Discord API and cache them.

        Args:
            guild_id: Discord guild ID
            uncached_ids: List of user IDs not found in cache

        Returns:
            Dictionary mapping user IDs to display names
        """
        result = {}
        members = await self.discord_api.get_guild_members_batch(guild_id, uncached_ids)

        for member in members:
            user_id = member["user"]["id"]
            display_name = self._resolve_display_name(member)
            result[user_id] = display_name

            cache_key = cache_keys.CacheKeys.display_name(user_id, guild_id)
            await self.cache.set_json(cache_key, display_name, ttl=cache_ttl.CacheTTL.DISPLAY_NAME)

        found_ids = {m["user"]["id"] for m in members}
        for user_id in uncached_ids:
            if user_id not in found_ids:
                result[user_id] = "Unknown User"

        return result

    async def _check_cache_for_display_names(
        self, guild_id: str, user_ids: list[str]
    ) -> tuple[dict[str, str], list[str]]:
        """
        Check cache for display names.

        Args:
            guild_id: Discord guild ID
            user_ids: List of user IDs to check

        Returns:
            Tuple of (cached_results, uncached_ids)
        """
        result = {}
        uncached_ids = []

        for user_id in user_ids:
            cache_key = cache_keys.CacheKeys.display_name(user_id, guild_id)
            cached = await cache_get(cache_key, CacheOperation.DISPLAY_NAME)
            if cached:
                result[user_id] = cached
            else:
                uncached_ids.append(user_id)

        return result, uncached_ids

    def _create_fallback_display_names(self, uncached_ids: list[str]) -> dict[str, str]:
        """
        Create fallback display names for failed API calls.

        Args:
            uncached_ids: List of user IDs that failed to fetch

        Returns:
            Dictionary mapping user IDs to fallback names
        """
        return {user_id: f"User#{user_id[-4:]}" for user_id in uncached_ids}

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
        result, uncached_ids = await self._check_cache_for_display_names(guild_id, user_ids)

        if uncached_ids:
            try:
                fetched_data = await self._fetch_and_cache_display_names(guild_id, uncached_ids)
                result.update(fetched_data)
            except discord_client.DiscordAPIError as e:
                logger.error("Failed to fetch display names: %s", e)
                fallback_data = self._create_fallback_display_names(uncached_ids)
                result.update(fallback_data)

        return result

    async def _check_cache_for_users(
        self, guild_id: str, user_ids: list[str]
    ) -> tuple[dict[str, dict[str, str | None]], list[str]]:
        """
        Check cache for user display names and avatars.

        Args:
            guild_id: Discord guild ID
            user_ids: List of user IDs to check

        Returns:
            Tuple of (cached_results, uncached_ids)
        """
        cached_results = {}
        uncached_ids = []

        for user_id in user_ids:
            cache_key = cache_keys.CacheKeys.display_name_avatar(user_id, guild_id)
            if self.cache:
                cached = await cache_get(cache_key, CacheOperation.DISPLAY_NAME_AVATAR)
                if cached:
                    cached_results[user_id] = cached
                    continue
            uncached_ids.append(user_id)

        return cached_results, uncached_ids

    async def _fetch_and_cache_display_names_avatars(
        self, guild_id: str, uncached_ids: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """
        Fetch display names and avatars from Discord API and cache them.

        Args:
            guild_id: Discord guild ID
            uncached_ids: User IDs not found in cache

        Returns:
            Dictionary mapping user IDs to display_name and avatar_url
        """
        result = {}
        members = await self.discord_api.get_guild_members_batch(guild_id, uncached_ids)

        for member in members:
            user_id = member["user"]["id"]
            display_name = self._resolve_display_name(member)

            member_avatar = member.get("avatar")
            user_avatar = member["user"].get("avatar")
            avatar_url = self._build_avatar_url(user_id, guild_id, member_avatar, user_avatar)

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
                result[user_id] = {"display_name": "Unknown User", "avatar_url": None}

        return result

    @staticmethod
    def _create_fallback_user_data(
        user_ids: list[str],
    ) -> dict[str, dict[str, str | None]]:
        """
        Create fallback user data for error cases.

        Args:
            user_ids: User IDs to create fallback data for

        Returns:
            Dictionary mapping user IDs to fallback display names
        """
        return {
            user_id: {"display_name": f"User#{user_id[-4:]}", "avatar_url": None}
            for user_id in user_ids
        }

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
        result, uncached_ids = await self._check_cache_for_users(guild_id, user_ids)

        if uncached_ids:
            try:
                fetched_data = await self._fetch_and_cache_display_names_avatars(
                    guild_id, uncached_ids
                )
                result.update(fetched_data)
            except discord_client.DiscordAPIError as e:
                logger.error("Failed to fetch display names and avatars: %s", e)
                fallback_data = self._create_fallback_user_data(uncached_ids)
                result.update(fallback_data)

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
    discord_api = get_discord_client()
    cache = await cache_client.get_redis_client()
    return DisplayNameResolver(discord_api, cache)
