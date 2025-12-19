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
Discord API client for OAuth2 and user data fetching.

Provides async HTTP client for Discord REST API operations.
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp

from services.api import config
from shared.cache import client as cache_client
from shared.cache import ttl

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_BASE}/users/@me"
DISCORD_GUILDS_URL = f"{DISCORD_API_BASE}/users/@me/guilds"


class DiscordAPIError(Exception):
    """Exception raised for Discord API errors."""

    def __init__(self, status: int, message: str, headers: dict[str, str] | None = None):
        """
        Initialize Discord API error.

        Args:
            status: HTTP status code from Discord API
            message: Error message or response body
            headers: Response headers (may contain rate limit info)
        """
        self.status = status
        self.message = message
        self.headers = headers or {}
        super().__init__(f"Discord API error {status}: {message}")


class DiscordAPIClient:
    """Async client for Discord REST API operations."""

    def __init__(self, client_id: str, client_secret: str, bot_token: str):
        """
        Initialize Discord API client.

        Args:
            client_id: Discord application client ID
            client_secret: Discord application client secret
            bot_token: Discord bot token for bot-level operations
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_token = bot_token
        self._session: aiohttp.ClientSession | None = None
        self._guild_locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _log_request(self, method: str, url: str, operation: str) -> None:
        """Log Discord API request."""
        logger.info(f"Discord API: {method} {url} ({operation})")

    def _log_response(
        self,
        response: aiohttp.ClientResponse,
        extra_info: str = "",
    ) -> None:
        """Log Discord API response with rate limit information."""
        rate_limit_info = (
            f"Rate Limit: "
            f"remaining={response.headers.get('x-ratelimit-remaining', 'N/A')}, "
            f"limit={response.headers.get('x-ratelimit-limit', 'N/A')}, "
            f"reset_after={response.headers.get('x-ratelimit-reset-after', 'N/A')}s"
        )

        if extra_info:
            rate_limit_info += f" - {extra_info}"

        logger.info(f"Discord API Response: {response.status} - {rate_limit_info}")

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Discord OAuth2 callback
            redirect_uri: Redirect URI that was used in authorization request

        Returns:
            Token response with access_token, refresh_token, expires_in

        Raises:
            DiscordAPIError: If token exchange fails
        """
        session = await self._get_session()

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        self._log_request("POST", DISCORD_TOKEN_URL, "exchange_code")
        try:
            async with session.post(
                DISCORD_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("error_description", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg)

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error exchanging code: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous token exchange

        Returns:
            Token response with new access_token, refresh_token, expires_in

        Raises:
            DiscordAPIError: If token refresh fails
        """
        session = await self._get_session()

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        self._log_request("POST", DISCORD_TOKEN_URL, "refresh_token")
        try:
            async with session.post(
                DISCORD_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("error_description", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg)

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error refreshing token: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Fetch current user information.

        Args:
            access_token: User's OAuth2 access token

        Returns:
            User object with id, username, avatar, etc.

        Raises:
            DiscordAPIError: If fetching user info fails
        """
        session = await self._get_session()

        self._log_request("GET", DISCORD_USER_URL, "get_user_info")
        try:
            async with session.get(
                DISCORD_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching user info: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_user_guilds(
        self, access_token: str, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch guilds the user is a member of with Redis caching.

        Uses double-checked locking to prevent duplicate API calls for concurrent requests.
        Caches results for 300 seconds to avoid Discord rate limits.

        Args:
            access_token: User's OAuth2 access token
            user_id: Discord user ID for cache key (optional, improves cache efficiency)

        Returns:
            List of guild objects with id, name, icon, permissions, etc.

        Raises:
            DiscordAPIError: If fetching guilds fails
        """
        # Fast path: check cache without lock if user_id provided
        if user_id:
            cache_key = f"user_guilds:{user_id}"
            redis = await cache_client.get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for user guilds: {user_id}")
                return json.loads(cached)

            # Get or create per-user lock
            async with self._locks_lock:
                if user_id not in self._guild_locks:
                    self._guild_locks[user_id] = asyncio.Lock()
                user_lock = self._guild_locks[user_id]

            # Slow path: check cache again after acquiring lock
            async with user_lock:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit after lock for user guilds: {user_id}")
                    return json.loads(cached)

                # Fetch from Discord and cache
                guilds_data = await self._fetch_user_guilds_uncached(access_token)
                await redis.set(cache_key, json.dumps(guilds_data), ttl=ttl.CacheTTL.USER_GUILDS)
                logger.debug(f"Cached {len(guilds_data)} guilds for user: {user_id}")
                return guilds_data
        else:
            # No user_id provided, skip caching
            return await self._fetch_user_guilds_uncached(access_token)

    async def _fetch_user_guilds_uncached(self, access_token: str) -> list[dict[str, Any]]:
        """
        Internal method to fetch guilds from Discord API without caching.

        Args:
            access_token: User's OAuth2 access token

        Returns:
            List of guild objects from Discord API

        Raises:
            DiscordAPIError: If fetching guilds fails
        """
        session = await self._get_session()

        self._log_request("GET", DISCORD_GUILDS_URL, "get_user_guilds")
        try:
            async with session.get(
                DISCORD_GUILDS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                response_data = await response.json()
                guild_count = len(response_data) if isinstance(response_data, list) else "N/A"
                self._log_response(response, f"Returned {guild_count} guilds")

                if response.status != 200:
                    error_msg = (
                        response_data.get("message", "Unknown error")
                        if isinstance(response_data, dict)
                        else "Unknown error"
                    )
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guilds: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_bot_guilds(self) -> list[dict[str, Any]]:
        """
        Fetch guilds the bot is a member of using bot token.

        Returns:
            List of guild objects with id, name, icon, etc.

        Raises:
            DiscordAPIError: If fetching bot guilds fails
        """
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/users/@me/guilds"

        self._log_request("GET", url, "get_bot_guilds")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                guild_count = len(response_data) if isinstance(response_data, list) else "N/A"
                self._log_response(response, f"Returned {guild_count} bot guilds")

                if response.status != 200:
                    error_msg = (
                        response_data.get("message", "Unknown error")
                        if isinstance(response_data, dict)
                        else "Unknown error"
                    )
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching bot guilds: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_guild_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """
        Fetch all channels in a guild using bot token.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            List of channel objects with id, name, type, etc.

        Raises:
            DiscordAPIError: If fetching channels fails
        """
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"

        self._log_request("GET", url, "get_guild_channels")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                channel_count = len(response_data) if isinstance(response_data, list) else "N/A"
                self._log_response(response, f"Returned {channel_count} channels")

                if response.status != 200:
                    error_msg = (
                        response_data.get("message", "Unknown error")
                        if isinstance(response_data, dict)
                        else "Unknown error"
                    )
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guild channels: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def fetch_channel(self, channel_id: str) -> dict[str, Any]:
        """
        Fetch channel information using bot token with Redis caching.

        Args:
            channel_id: Discord channel ID

        Returns:
            Channel object with id, name, type, guild_id, etc.

        Raises:
            DiscordAPIError: If fetching channel fails
        """
        cache_key = f"discord:channel:{channel_id}"
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for channel: {channel_id}")
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/channels/{channel_id}"

        self._log_request("GET", url, "fetch_channel")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    if response.status == 404:
                        # Cache negative result briefly
                        await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result
                await redis.set(
                    cache_key,
                    json.dumps(response_data),
                    ttl=ttl.CacheTTL.DISCORD_CHANNEL,
                )
                logger.debug(f"Cached channel: {channel_id}")
                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching channel: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def fetch_guild(self, guild_id: str) -> dict[str, Any]:
        """
        Fetch guild information using bot token with Redis caching.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            Guild object with id, name, icon, features, etc.

        Raises:
            DiscordAPIError: If fetching guild fails
        """
        cache_key = f"discord:guild:{guild_id}"
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for guild: {guild_id}")
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/guilds/{guild_id}"

        self._log_request("GET", url, "fetch_guild")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    if response.status == 404:
                        # Cache negative result briefly
                        await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result
                await redis.set(
                    cache_key, json.dumps(response_data), ttl=ttl.CacheTTL.DISCORD_GUILD
                )
                logger.debug(f"Cached guild: {guild_id}")
                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guild: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def fetch_guild_roles(self, guild_id: str) -> list[dict[str, Any]]:
        """
        Fetch guild roles using bot token with Redis caching.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            List of role objects with id, name, color, position, managed, etc.

        Raises:
            DiscordAPIError: If fetching roles fails
        """
        cache_key = f"discord:guild_roles:{guild_id}"
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for guild roles: {guild_id}")
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles"

        self._log_request("GET", url, "fetch_guild_roles")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result for 5 minutes
                await redis.set(cache_key, json.dumps(response_data), ttl=300)
                logger.debug(f"Cached guild roles: {guild_id}")
                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guild roles: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def fetch_user(self, user_id: str) -> dict[str, Any]:
        """
        Fetch user information using bot token with Redis caching.

        Args:
            user_id: Discord user ID

        Returns:
            User object with id, username, avatar, discriminator, etc.

        Raises:
            DiscordAPIError: If fetching user fails
        """
        cache_key = f"discord:user:{user_id}"
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for user: {user_id}")
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/users/{user_id}"

        self._log_request("GET", url, "fetch_user")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    if response.status == 404:
                        # Cache negative result briefly
                        await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result
                await redis.set(cache_key, json.dumps(response_data), ttl=ttl.CacheTTL.DISCORD_USER)
                logger.debug(f"Cached user: {user_id}")
                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching user: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_guild_member(self, guild_id: str, user_id: str) -> dict[str, Any]:
        """
        Fetch guild member information using bot token.

        Args:
            guild_id: Discord guild (server) ID
            user_id: Discord user ID

        Returns:
            Guild member object with user, roles, nick, etc.

        Raises:
            DiscordAPIError: If fetching member fails
        """
        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}"

        self._log_request("GET", url, "get_guild_member")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guild member: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_guild_members_batch(
        self, guild_id: str, user_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple guild members using bot token.

        Args:
            guild_id: Discord guild (server) ID
            user_ids: List of Discord user IDs to fetch

        Returns:
            List of guild member objects (may be fewer than requested if users left)

        Raises:
            DiscordAPIError: If fetching members fails
        """
        logger.info(f"Discord API: Batch fetching {len(user_ids)} members from guild {guild_id}")
        members = []
        for user_id in user_ids:
            try:
                member = await self.get_guild_member(guild_id, user_id)
                members.append(member)
            except DiscordAPIError as e:
                if e.status == 404:
                    logger.debug(f"User {user_id} not found in guild {guild_id}")
                    continue
                raise
        logger.info(
            f"Discord API: Batch completed - fetched {len(members)}/{len(user_ids)} members"
        )
        return members


async def fetch_channel_name_safe(channel_id: str) -> str:
    """
    Fetch channel name from Discord API with error handling.

    This is a convenience wrapper around fetch_channel that handles errors
    gracefully and returns "Unknown Channel" if the fetch fails.

    Args:
        channel_id: Discord channel ID

    Returns:
        Channel name or "Unknown Channel" if fetch fails
    """
    client = get_discord_client()
    try:
        channel_data = await client.fetch_channel(channel_id)
        return channel_data.get("name", "Unknown Channel")
    except DiscordAPIError as e:
        logger.warning(f"Could not fetch channel name for {channel_id}: {e}")
        return "Unknown Channel"


async def fetch_user_display_name_safe(discord_id: str) -> str:
    """
    Fetch user display name from Discord API with error handling.

    Args:
        discord_id: Discord user ID

    Returns:
        User display name in format "@username" or fallback to "@{id}"
    """
    client = get_discord_client()
    try:
        user_data = await client.fetch_user(discord_id)
        username = user_data.get("username", discord_id)
        return f"@{username}"
    except DiscordAPIError as e:
        logger.warning(f"Could not fetch user name for {discord_id}: {e}")
        return f"@{discord_id}"


async def fetch_guild_name_safe(guild_id: str) -> str:
    """
    Fetch guild/server name from Discord API with error handling.

    Args:
        guild_id: Discord guild ID

    Returns:
        Guild name or fallback to guild ID
    """
    client = get_discord_client()
    try:
        guild_data = await client.fetch_guild(guild_id)
        return guild_data.get("name", guild_id)
    except DiscordAPIError as e:
        logger.warning(f"Could not fetch guild name for {guild_id}: {e}")
        return guild_id


_discord_client_instance: DiscordAPIClient | None = None


def get_discord_client() -> DiscordAPIClient:
    """Get Discord API client singleton."""
    global _discord_client_instance
    if _discord_client_instance is None:
        api_config = config.get_api_config()
        _discord_client_instance = DiscordAPIClient(
            client_id=api_config.discord_client_id,
            client_secret=api_config.discord_client_secret,
            bot_token=api_config.discord_bot_token,
        )
    return _discord_client_instance
