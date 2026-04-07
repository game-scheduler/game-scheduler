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
Discord API client for OAuth2 and user data fetching.

Provides async HTTP client for Discord REST API operations.
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp
from starlette import status

from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl
from shared.utils.discord_tokens import DISCORD_BOT_TOKEN_DOT_COUNT

logger = logging.getLogger(__name__)


class DiscordAPIError(Exception):
    """Exception raised for Discord API errors."""

    def __init__(self, status: int, message: str, headers: dict[str, str] | None = None) -> None:
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

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        bot_token: str,
        api_base_url: str = "https://discord.com/api/v10",
    ) -> None:
        """
        Initialize Discord API client.

        Args:
            client_id: Discord application client ID
            client_secret: Discord application client secret
            bot_token: Discord bot token for bot-level operations
            api_base_url: Base URL for Discord API (overridable for testing)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_token = bot_token
        self._api_base_url = api_base_url
        self._token_url = f"{api_base_url}/oauth2/token"
        self._user_url = f"{api_base_url}/users/@me"
        self._guilds_url = f"{api_base_url}/users/@me/guilds"
        self._session: aiohttp.ClientSession | None = None
        self._guild_locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    def _get_auth_header(self, token: str | None = None) -> str:
        """
        Detect token type and return appropriate Authorization header.

        Bot tokens have 3 dot-separated parts: BASE64.TIMESTAMP.SIGNATURE (2 dots)
        OAuth access tokens have 2 dot-separated parts (1 dot)

        Args:
            token: Discord bot token or OAuth access token (defaults to self.bot_token)

        Returns:
            Authorization header value ("Bot {token}" or "Bearer {token}")

        Raises:
            ValueError: If token format is invalid (not 1 or 2 dots)
        """
        token = token or self.bot_token
        dot_count = token.count(".")
        if dot_count == DISCORD_BOT_TOKEN_DOT_COUNT:
            return f"Bot {token}"
        if dot_count == 1:
            return f"Bearer {token}"
        msg = (
            f"Invalid Discord token format: expected 1 or {DISCORD_BOT_TOKEN_DOT_COUNT} dots, "
            f"got {dot_count}"
        )
        raise ValueError(msg)

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
        logger.info("Discord API: %s %s (%s)", method, url, operation)

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

        logger.info("Discord API Response: %s - %s", response.status, rate_limit_info)

    async def _parse_response_json(self, response: aiohttp.ClientResponse) -> Any:  # noqa: ANN401
        """Parse response body as JSON, raising DiscordAPIError on non-JSON payloads."""
        try:
            return await response.json(content_type=None)
        except (json.JSONDecodeError, ValueError) as exc:
            raise DiscordAPIError(
                response.status,
                f"Non-JSON response (HTTP {response.status}): {exc}",
                dict(response.headers),
            ) from exc

    async def _raise_for_error_status(
        self,
        response: aiohttp.ClientResponse,
        response_data: Any,  # noqa: ANN401
        cache_key: str | None,
    ) -> None:
        """Raise DiscordAPIError for non-200 responses, caching 404s."""
        if response.status == status.HTTP_200_OK:
            return
        error_msg = (
            response_data.get("message", response_data.get("error_description", "Unknown error"))
            if isinstance(response_data, dict)
            else "Unknown error"
        )
        redis = await cache_client.get_redis_client()
        if response.status == status.HTTP_404_NOT_FOUND and cache_key:
            await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
        raise DiscordAPIError(response.status, error_msg, dict(response.headers))

    async def _make_api_request(
        self,
        method: str,
        url: str,
        operation_name: str,
        headers: dict[str, str],
        cache_key: str | None = None,
        cache_ttl: int | None = None,
        session: aiohttp.ClientSession | None = None,
        channel_id: str | None = None,
        **request_kwargs: Any,  # noqa: ANN401
    ) -> dict[str, Any]:
        """
        Generic Discord API request handler with error handling and caching.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full request URL
            operation_name: Human-readable operation name for logging
            headers: Request headers
            cache_key: Optional cache key for GET requests
            cache_ttl: Optional cache TTL in seconds
            session: Optional existing session
            channel_id: Discord channel ID for per-channel rate limiting (global-only if None)
            **request_kwargs: Additional arguments for aiohttp request

        Returns:
            Response JSON data

        Raises:
            DiscordAPIError: On non-200 status
        """
        redis = await cache_client.get_redis_client()
        self._log_request(method, url, operation_name)

        while True:
            if channel_id is not None:
                wait_ms = await redis.claim_global_and_channel_slot(channel_id)
            else:
                wait_ms = await redis.claim_global_slot()
            if wait_ms == 0:
                break
            await asyncio.sleep(wait_ms / 1000)

        try:
            session_to_use = session or await self._get_session()
            async with session_to_use.request(
                method,
                url,
                headers=headers,
                **request_kwargs,
            ) as response:
                response_data = await self._parse_response_json(response)
                self._log_response(response)

                await self._raise_for_error_status(response, response_data, cache_key)

                if cache_key and cache_ttl:
                    await redis.set(cache_key, json.dumps(response_data), ttl=cache_ttl)

                return response_data

        except aiohttp.ClientError as e:
            logger.error("Network error in %s: %s", operation_name, e)
            raise DiscordAPIError(500, f"Network error: {e!s}") from e

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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        return await self._make_api_request(
            method="POST",
            url=self._token_url,
            operation_name="exchange_code",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )

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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        return await self._make_api_request(
            method="POST",
            url=self._token_url,
            operation_name="refresh_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )

    async def get_application_info(self) -> dict[str, Any]:
        """Fetch Discord application info for the bot, with 1-hour caching."""
        redis = await cache_client.get_redis_client()
        cached = await redis.get(cache_keys.CacheKeys.app_info())
        if cached:
            logger.debug("Cache hit for application info")
            return json.loads(cached)
        return await self._make_api_request(
            method="GET",
            url=f"{self._api_base_url}/oauth2/applications/@me",
            operation_name="get_application_info",
            headers={"Authorization": self._get_auth_header()},
            cache_key=cache_keys.CacheKeys.app_info(),
            cache_ttl=ttl.CacheTTL.APP_INFO,
        )

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

        self._log_request("GET", self._user_url, "get_user_info")
        try:
            async with session.get(
                self._user_url,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != status.HTTP_200_OK:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error("Network error fetching user info: %s", e)
            raise DiscordAPIError(500, f"Network error: {e!s}") from e

    async def get_guilds(
        self, token: str | None = None, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch guilds accessible with the given token (bot or OAuth).

        Automatically detects token type and applies appropriate caching strategy:
        - Bot tokens: No caching (honors rate limits with retry logic)
          Rationale: We need fresh guild lists to handle back-to-back guild join events.
          Caching would risk missing new guilds when processing rapid join notifications.
          Instead, we handle Discord's rate limits by sleeping and retrying when we receive
          429 responses.
        - OAuth tokens with user_id: Cached with double-checked locking
        - OAuth tokens without user_id: No caching

        Args:
            token: Discord bot token or OAuth access token (defaults to self.bot_token)
            user_id: Discord user ID for cache key (optional, improves cache efficiency for OAuth)

        Returns:
            List of guild objects with id, name, icon, permissions, etc.

        Raises:
            DiscordAPIError: If fetching guilds fails
        """
        use_token = token or self.bot_token

        # Fast path: check cache for OAuth tokens with user_id
        if user_id:
            cache_key = cache_keys.CacheKeys.user_guilds(user_id)
            redis = await cache_client.get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                logger.debug("Cache hit for user guilds: %s", user_id)
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
                    logger.debug("Cache hit after lock for user guilds: %s", user_id)
                    return json.loads(cached)

                # Fetch from Discord and cache
                guilds_data = await self._fetch_guilds_uncached(use_token)
                await redis.set(cache_key, json.dumps(guilds_data), ttl=ttl.CacheTTL.USER_GUILDS)
                logger.debug("Cached %s guilds for user: %s", len(guilds_data), user_id)
                return guilds_data

        # No caching for bot tokens or OAuth tokens without user_id
        # Bot tokens honor rate limits with retry logic in _fetch_guilds_uncached
        return await self._fetch_guilds_uncached(use_token)

    def _get_error_message(
        self,
        response_data: Any,  # noqa: ANN401
        default: str,
    ) -> str:
        """Extract error message from response data."""
        if isinstance(response_data, dict):
            return response_data.get("message", default)
        return default

    def _get_retry_wait_time(self, headers: dict[str, str]) -> float:
        """Extract retry wait time from rate limit headers."""
        retry_after = headers.get("retry-after")
        reset_after = headers.get("x-ratelimit-reset-after")
        return float(retry_after or reset_after or 1.0)

    async def _handle_rate_limit_response(
        self,
        response: aiohttp.ClientResponse,
        response_data: Any,  # noqa: ANN401
        attempt: int,
        max_retries: int,
    ) -> bool:
        """
        Handle 429 rate limit response.

        Args:
            response: HTTP response object
            response_data: Parsed JSON response data
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries

        Returns:
            True if should retry, False if should raise error

        Raises:
            DiscordAPIError: If final retry attempt failed
        """
        wait_time = self._get_retry_wait_time(dict(response.headers))

        if attempt < max_retries - 1:
            logger.warning(
                "Rate limited on guilds fetch (attempt %d/%d), waiting %.2fs",
                attempt + 1,
                max_retries,
                wait_time,
            )
            await asyncio.sleep(wait_time)
            return True

        # Final attempt failed
        error_msg = self._get_error_message(response_data, "Rate limited")
        raise DiscordAPIError(response.status, error_msg, dict(response.headers))

    async def _process_guilds_response(
        self,
        response: aiohttp.ClientResponse,
        attempt: int,
        max_retries: int,
    ) -> list[dict[str, Any]] | None:
        """
        Process guilds API response and handle errors.

        Args:
            response: HTTP response object
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries

        Returns:
            List of guild data if successful, None if should retry

        Raises:
            DiscordAPIError: If response indicates non-retryable error
        """
        response_data = await self._parse_response_json(response)
        guild_count = len(response_data) if isinstance(response_data, list) else "N/A"
        self._log_response(response, f"Returned {guild_count} guilds")

        if response.status == status.HTTP_429_TOO_MANY_REQUESTS:
            should_retry = await self._handle_rate_limit_response(
                response, response_data, attempt, max_retries
            )
            return None if should_retry else response_data

        if response.status != status.HTTP_200_OK:
            error_msg = self._get_error_message(response_data, "Unknown error")
            raise DiscordAPIError(response.status, error_msg, dict(response.headers))

        return response_data

    async def _fetch_guilds_uncached(self, token: str) -> list[dict[str, Any]]:
        """
        Internal method to fetch guilds from Discord API without caching.

        Handles rate limiting by retrying with exponential backoff when receiving 429.

        Args:
            token: Discord bot token or OAuth access token

        Returns:
            List of guild objects from Discord API

        Raises:
            DiscordAPIError: If fetching guilds fails after retries
        """
        session = await self._get_session()
        url = self._guilds_url

        max_retries = 3
        for attempt in range(max_retries):
            self._log_request("GET", url, "get_guilds")
            try:
                async with session.get(
                    url,
                    headers={"Authorization": self._get_auth_header(token)},
                ) as response:
                    result = await self._process_guilds_response(response, attempt, max_retries)
                    if result is not None:
                        return result
            except aiohttp.ClientError as e:
                logger.error("Network error fetching guilds: %s", e)
                raise DiscordAPIError(500, f"Network error: {e!s}") from e

        # Should never reach here, but just in case
        raise DiscordAPIError(429, "Rate limit exceeded after max retries", {})

    async def get_guild_channels(
        self, guild_id: str, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Fetch all channels in a guild using bot token with Redis caching.

        Args:
            guild_id: Discord guild (server) ID
            force_refresh: When True, bypass cache and fetch directly from Discord.
                           Use when channel list may have changed since last cache write.

        Returns:
            List of channel objects with id, name, type, etc.

        Raises:
            DiscordAPIError: If fetching channels fails
        """
        cache_key = cache_keys.CacheKeys.discord_guild_channels(guild_id)
        redis = await cache_client.get_redis_client()

        if not force_refresh:
            cached = await redis.get(cache_key)
            if cached:
                logger.debug("Cache hit for guild channels: %s", guild_id)
                return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{self._api_base_url}/guilds/{guild_id}/channels"

        self._log_request("GET", url, "get_guild_channels")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await self._parse_response_json(response)
                channel_count = len(response_data) if isinstance(response_data, list) else "N/A"
                self._log_response(response, f"Returned {channel_count} channels")

                if response.status != status.HTTP_200_OK:
                    error_msg = (
                        response_data.get("message", "Unknown error")
                        if isinstance(response_data, dict)
                        else "Unknown error"
                    )
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache the result
                await redis.set(
                    cache_key,
                    json.dumps(response_data),
                    ttl=ttl.CacheTTL.DISCORD_GUILD_CHANNELS,
                )
                logger.debug("Cached %s channels for guild: %s", channel_count, guild_id)

                return response_data
        except aiohttp.ClientError as e:
            logger.error("Network error fetching guild channels: %s", e)
            raise DiscordAPIError(500, f"Network error: {e!s}") from e

    async def fetch_channel(self, channel_id: str, token: str | None = None) -> dict[str, Any]:
        """
        Fetch channel information with Redis caching.

        Args:
            channel_id: Discord channel ID
            token: Discord bot token or OAuth access token (defaults to self.bot_token)

        Returns:
            Channel object with id, name, type, guild_id, etc.

        Raises:
            DiscordAPIError: If fetching channel fails
        """
        cache_key = cache_keys.CacheKeys.discord_channel(channel_id)
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Cache hit for channel: %s", channel_id)
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{self._api_base_url}/channels/{channel_id}"

        self._log_request("GET", url, "fetch_channel")
        try:
            async with session.get(
                url,
                headers={"Authorization": self._get_auth_header(token)},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != status.HTTP_200_OK:
                    error_msg = response_data.get("message", "Unknown error")
                    if response.status == status.HTTP_404_NOT_FOUND:
                        # Cache negative result briefly
                        await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result
                await redis.set(
                    cache_key,
                    json.dumps(response_data),
                    ttl=ttl.CacheTTL.DISCORD_CHANNEL,
                )
                logger.debug("Cached channel: %s", channel_id)
                return response_data
        except aiohttp.ClientError as e:
            logger.error("Network error fetching channel: %s", e)
            raise DiscordAPIError(500, f"Network error: {e!s}") from e

    async def fetch_guild(self, guild_id: str, token: str | None = None) -> dict[str, Any]:
        """
        Fetch guild information with Redis caching.

        Args:
            guild_id: Discord guild (server) ID
            token: Discord bot token or OAuth access token (defaults to self.bot_token)

        Returns:
            Guild object with id, name, icon, features, etc.

        Raises:
            DiscordAPIError: If fetching guild fails
        """
        cache_key = cache_keys.CacheKeys.discord_guild(guild_id)
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Cache hit for guild: %s", guild_id)
            return json.loads(cached)

        url = f"{self._api_base_url}/guilds/{guild_id}"
        result = await self._make_api_request(
            method="GET",
            url=url,
            operation_name="fetch_guild",
            headers={"Authorization": self._get_auth_header(token)},
            cache_key=cache_key,
            cache_ttl=ttl.CacheTTL.DISCORD_GUILD,
        )
        logger.debug("Cached guild: %s", guild_id)
        return result

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
        cache_key = cache_keys.CacheKeys.discord_guild_roles(guild_id)
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Cache hit for guild roles: %s", guild_id)
            return json.loads(cached)

        # Fetch from Discord API
        session = await self._get_session()
        url = f"{self._api_base_url}/guilds/{guild_id}/roles"

        self._log_request("GET", url, "fetch_guild_roles")
        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()
                self._log_response(response)

                if response.status != status.HTTP_200_OK:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                # Cache successful result for 5 minutes
                await redis.set(cache_key, json.dumps(response_data), ttl=300)
                logger.debug("Cached guild roles: %s", guild_id)
                return response_data
        except aiohttp.ClientError as e:
            logger.error("Network error fetching guild roles: %s", e)
            raise DiscordAPIError(500, f"Network error: {e!s}") from e

    async def fetch_user(self, user_id: str, token: str | None = None) -> dict[str, Any]:
        """
        Fetch user information with Redis caching.

        Args:
            user_id: Discord user ID
            token: Discord bot token or OAuth access token (defaults to self.bot_token)

        Returns:
            User object with id, username, avatar, discriminator, etc.

        Raises:
            DiscordAPIError: If fetching user fails
        """
        cache_key = cache_keys.CacheKeys.discord_user(user_id)
        redis = await cache_client.get_redis_client()

        # Check cache first
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Cache hit for user: %s", user_id)
            return json.loads(cached)

        url = f"{self._api_base_url}/users/{user_id}"
        result = await self._make_api_request(
            method="GET",
            url=url,
            operation_name="fetch_user",
            headers={"Authorization": self._get_auth_header(token)},
            cache_key=cache_key,
            cache_ttl=ttl.CacheTTL.DISCORD_USER,
        )
        logger.debug("Cached user: %s", user_id)
        return result

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
        url = f"{self._api_base_url}/guilds/{guild_id}/members/{user_id}"
        return await self._make_api_request(
            method="GET",
            url=url,
            operation_name="get_guild_member",
            headers={"Authorization": f"Bot {self.bot_token}"},
        )

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
        logger.info(
            "Discord API: Batch fetching %s members from guild %s",
            len(user_ids),
            guild_id,
        )
        members = []
        for user_id in user_ids:
            try:
                member = await self.get_guild_member(guild_id, user_id)
                members.append(member)
            except DiscordAPIError as e:
                if e.status == status.HTTP_404_NOT_FOUND:
                    logger.debug("User %s not found in guild %s", user_id, guild_id)
                    continue
                raise
        logger.info(
            "Discord API: Batch completed - fetched %s/%s members",
            len(members),
            len(user_ids),
        )
        return members


# Global client instance for helper functions (lazy-initialized)
_global_client_instance: DiscordAPIClient | None = None


def _get_global_client() -> DiscordAPIClient:
    """
    Get or create global Discord API client for helper functions.

    This is a fallback for legacy helper functions that don't accept a client parameter.
    New code should use get_discord_client() from service-specific dependencies.
    """
    global _global_client_instance  # noqa: PLW0603 - Singleton pattern for legacy Discord client
    if _global_client_instance is None:
        from services.api.dependencies.discord import (  # noqa: PLC0415
            get_discord_client,
        )

        _global_client_instance = get_discord_client()
    return _global_client_instance


async def fetch_channel_name_safe(channel_id: str, client: DiscordAPIClient | None = None) -> str:
    """
    Fetch channel name from Discord API with error handling.

    This is a convenience wrapper around fetch_channel that handles errors
    gracefully and returns "Unknown Channel" if the fetch fails.

    Args:
        channel_id: Discord channel ID
        client: DiscordAPIClient instance (optional, uses global if not provided)

    Returns:
        Channel name or "Unknown Channel" if fetch fails
    """
    if client is None:
        client = _get_global_client()
    try:
        channel_data = await client.fetch_channel(channel_id)
        return channel_data.get("name", "Unknown Channel")
    except DiscordAPIError as e:
        logger.warning("Could not fetch channel name for %s: %s", channel_id, e)
        return "Unknown Channel"


async def fetch_user_display_name_safe(
    discord_id: str, client: DiscordAPIClient | None = None
) -> str:
    """
    Fetch user display name from Discord API with error handling.

    Args:
        discord_id: Discord user ID
        client: DiscordAPIClient instance (optional, uses global if not provided)

    Returns:
        User display name in format "@username" or fallback to "@{id}"
    """
    if client is None:
        client = _get_global_client()
    try:
        user_data = await client.fetch_user(discord_id)
        username = user_data.get("username", discord_id)
        return f"@{username}"
    except DiscordAPIError as e:
        logger.warning("Could not fetch user name for %s: %s", discord_id, e)
        return f"@{discord_id}"


async def fetch_guild_name_safe(guild_id: str, client: DiscordAPIClient | None = None) -> str:
    """
    Fetch guild/server name from Discord API with error handling.

    Args:
        guild_id: Discord guild ID
        client: DiscordAPIClient instance (optional, uses global if not provided)

    Returns:
        Guild name or fallback to guild ID
    """
    if client is None:
        client = _get_global_client()
    try:
        guild_data = await client.fetch_guild(guild_id)
        return guild_data.get("name", guild_id)
    except DiscordAPIError as e:
        logger.warning("Could not fetch guild name for %s: %s", guild_id, e)
        return guild_id


async def get_guild_channels_safe(
    guild_id: str, client: DiscordAPIClient | None = None
) -> list[dict]:
    """
    Fetch guild channels from Discord API with error handling.

    Args:
        guild_id: Discord guild ID
        client: DiscordAPIClient instance (optional, uses global if not provided)

    Returns:
        List of channel dicts, or empty list on error
    """
    if client is None:
        client = _get_global_client()
    try:
        return await client.get_guild_channels(guild_id)
    except DiscordAPIError as e:
        logger.warning("Could not fetch guild channels for %s: %s", guild_id, e)
        return []
