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
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

import aiohttp
from opentelemetry import metrics
from starlette import status

from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl
from shared.cache.operations import CacheOperation
from shared.cache.ttl import DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND
from shared.utils.discord_tokens import DISCORD_BOT_TOKEN_DOT_COUNT

_T = TypeVar("_T")

_cache_meter = metrics.get_meter(__name__)
_cache_hit_counter = _cache_meter.create_counter(
    "discord.cache.hits", description="Discord cache hits", unit="1"
)
_cache_miss_counter = _cache_meter.create_counter(
    "discord.cache.misses", description="Discord cache misses", unit="1"
)
_cache_duration_histogram = _cache_meter.create_histogram("discord.cache.duration", unit="s")
_batch_size_histogram = _cache_meter.create_histogram(
    "discord.member_batch.size", description="Members requested per batch fetch", unit="1"
)
_batch_not_found_counter = _cache_meter.create_counter(
    "discord.member_batch.not_found",
    description="Members not found (404) during batch fetch",
    unit="1",
)
_batch_duration_histogram = _cache_meter.create_histogram(
    "discord.member_batch.duration",
    description="Wall-clock duration of concurrent batch member fetch",
    unit="s",
)

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
        global_max: int = 25,
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
            global_max: Global rate-limit budget (requests per 1000ms window, default 25)
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
                wait_ms = await redis.claim_global_and_channel_slot(
                    channel_id, global_max=global_max
                )
            else:
                wait_ms = await redis.claim_global_slot(global_max=global_max)
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

                if cache_key:
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
        return await self._get_or_fetch(
            cache_key=cache_keys.CacheKeys.app_info(),
            cache_ttl=ttl.CacheTTL.APP_INFO,
            fetch_fn=lambda: self._make_api_request(
                method="GET",
                url=f"{self._api_base_url}/oauth2/applications/@me",
                operation_name="get_application_info",
                headers={"Authorization": self._get_auth_header()},
            ),
            operation=CacheOperation.GET_APPLICATION_INFO,
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
                return await self._get_or_fetch(
                    cache_key=cache_key,
                    cache_ttl=ttl.CacheTTL.USER_GUILDS,
                    fetch_fn=lambda: self._fetch_guilds_uncached(use_token),
                    operation=CacheOperation.GET_USER_GUILDS,
                )

        # No caching for bot tokens or OAuth tokens without user_id
        # Bot tokens honor rate limits with retry logic in _fetch_guilds_uncached
        return await self._fetch_guilds_uncached(use_token)

    async def _get_or_fetch(
        self,
        cache_key: str,
        cache_ttl: int,
        fetch_fn: Callable[[], Awaitable[_T]],
        operation: CacheOperation,
    ) -> _T:
        """
        Read-through cache helper; falls back to REST only on cache miss.

        Delegates the cache read to _read_cache_only. On a 503 cache miss,
        calls fetch_fn(), writes the result back to Redis, and returns it.
        """
        try:
            return await self._read_cache_only(cache_key, operation)
        except DiscordAPIError as exc:
            if exc.status != status.HTTP_503_SERVICE_UNAVAILABLE:
                raise
        result = await fetch_fn()
        redis = await cache_client.get_redis_client()
        await redis.set(cache_key, json.dumps(result), ttl=cache_ttl)
        return result

    async def _read_cache_only(self, cache_key: str, operation: CacheOperation) -> Any:  # noqa: ANN401
        """
        Cache-only read with OTel recording; raises DiscordAPIError(503) on miss.

        Gateway events keep these keys current. A miss means the bot is not yet
        connected or the resource is genuinely absent — not a reason to call REST.
        """
        redis = await cache_client.get_redis_client()
        t0 = time.monotonic()
        cached = await redis.get(cache_key)
        if cached:
            _cache_hit_counter.add(1, {"operation": operation})
            _cache_duration_histogram.record(
                time.monotonic() - t0,
                attributes={"operation": operation, "result": "hit"},
            )
            return json.loads(cached)
        _cache_miss_counter.add(1, {"operation": operation})
        _cache_duration_histogram.record(
            time.monotonic() - t0,
            attributes={"operation": operation, "result": "miss"},
        )
        raise DiscordAPIError(
            503, f"Discord data unavailable: bot gateway not connected [{operation}]"
        )

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

    async def get_guild_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """
        Fetch all channels in a guild from the Redis gateway cache.

        The bot keeps this key current via channel create/update/delete gateway events.
        A cache miss means the bot is not yet connected — raises 503 instead of REST fallback.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            List of channel objects with id, name, type, etc.

        Raises:
            DiscordAPIError: 503 if guild channels are not in the gateway cache
        """
        return cast(
            "list[dict[str, Any]]",
            await self._read_cache_only(
                cache_keys.CacheKeys.discord_guild_channels(guild_id),
                CacheOperation.FETCH_GUILD_CHANNELS,
            ),
        )

    async def fetch_channel(self, channel_id: str) -> dict[str, Any]:
        """
        Fetch channel information from the Redis gateway cache.

        The bot keeps this key current via channel update gateway events.
        A cache miss means the bot is not connected — raises 503 instead of REST fallback.

        Args:
            channel_id: Discord channel ID

        Returns:
            Channel object with id, name, type, guild_id, etc.

        Raises:
            DiscordAPIError: 503 if channel data is not in the gateway cache
        """
        return cast(
            "dict[str, Any]",
            await self._read_cache_only(
                cache_keys.CacheKeys.discord_channel(channel_id),
                CacheOperation.FETCH_CHANNEL,
            ),
        )

    async def fetch_guild(self, guild_id: str) -> dict[str, Any]:
        """
        Fetch guild information from the Redis gateway cache.

        The bot keeps this key current via guild update gateway events.
        A cache miss means the bot is not connected — raises 503 instead of REST fallback.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            Guild object with id, name, icon, features, etc.

        Raises:
            DiscordAPIError: 503 if guild data is not in the gateway cache
        """
        return cast(
            "dict[str, Any]",
            await self._read_cache_only(
                cache_keys.CacheKeys.discord_guild(guild_id),
                CacheOperation.FETCH_GUILD,
            ),
        )

    async def fetch_guild_roles(self, guild_id: str) -> list[dict[str, Any]]:
        """
        Fetch guild roles from the Redis gateway cache.

        The bot keeps this key current via role create/update/delete gateway events.
        A cache miss means the bot is not connected — raises 503 instead of REST fallback.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            List of role objects with id, name, color, position, managed, etc.

        Raises:
            DiscordAPIError: 503 if guild role data is not in the gateway cache
        """
        return cast(
            "list[dict[str, Any]]",
            await self._read_cache_only(
                cache_keys.CacheKeys.discord_guild_roles(guild_id),
                CacheOperation.FETCH_GUILD_ROLES,
            ),
        )

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
        return await self._get_or_fetch(
            cache_key=cache_keys.CacheKeys.discord_user(user_id),
            cache_ttl=ttl.CacheTTL.DISCORD_USER,
            fetch_fn=lambda: self._make_api_request(
                method="GET",
                url=f"{self._api_base_url}/users/{user_id}",
                operation_name="fetch_user",
                headers={"Authorization": self._get_auth_header(token)},
            ),
            operation=CacheOperation.FETCH_USER,
        )

    async def get_guild_member(
        self, guild_id: str, user_id: str, global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND
    ) -> dict[str, Any]:
        """
        Fetch guild member information using bot token with Redis caching.

        Args:
            guild_id: Discord guild (server) ID
            user_id: Discord user ID
            global_max: Global rate-limit budget to use for this request (default 25).

        Returns:
            Guild member object with user, roles, nick, etc.

        Raises:
            DiscordAPIError: If fetching member fails
        """
        return await self._get_or_fetch(
            cache_key=cache_keys.CacheKeys.discord_member(guild_id, user_id),
            cache_ttl=ttl.CacheTTL.DISCORD_MEMBER,
            fetch_fn=lambda: self._make_api_request(
                method="GET",
                url=f"{self._api_base_url}/guilds/{guild_id}/members/{user_id}",
                operation_name="get_guild_member",
                headers={"Authorization": f"Bot {self.bot_token}"},
                global_max=global_max,
            ),
            operation=CacheOperation.GET_GUILD_MEMBER,
        )

    async def get_guild_members_batch(
        self,
        guild_id: str,
        user_ids: list[str],
        global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND,
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple guild members using bot token, concurrently.

        Args:
            guild_id: Discord guild (server) ID
            user_ids: List of Discord user IDs to fetch
            global_max: Global rate-limit budget per 1000ms window (default 25).

        Returns:
            List of guild member objects (may be fewer than requested if users left)

        Raises:
            DiscordAPIError: If a non-404 error occurs for any user
        """
        logger.info(
            "Discord API: Batch fetching %s members from guild %s",
            len(user_ids),
            guild_id,
        )
        _batch_size_histogram.record(len(user_ids))
        t0 = time.monotonic()

        async def _fetch_one(user_id: str) -> dict[str, Any] | None:
            try:
                return await self.get_guild_member(guild_id, user_id, global_max=global_max)
            except DiscordAPIError as e:
                if e.status == status.HTTP_404_NOT_FOUND:
                    logger.debug("User %s not found in guild %s", user_id, guild_id)
                    return None
                raise

        results = await asyncio.gather(*[_fetch_one(uid) for uid in user_ids])
        members = [r for r in results if r is not None]
        not_found = len(user_ids) - len(members)
        _batch_duration_histogram.record(time.monotonic() - t0)
        if not_found:
            _batch_not_found_counter.add(not_found)
        logger.info(
            "Discord API: Batch completed - fetched %s/%s members",
            len(members),
            len(user_ids),
        )
        return members

    async def get_current_user_guild_member(self, guild_id: str, token: str) -> dict[str, Any]:
        """
        Fetch the current user's guild member object using their OAuth token.

        Uses the user's own rate limit pool (Bearer token), leaving the bot token
        budget untouched.

        Args:
            guild_id: Discord guild (server) ID
            token: User's OAuth access token

        Returns:
            Discord guild member object

        Raises:
            DiscordAPIError: If the request fails
        """
        return await self._make_api_request(
            method="GET",
            url=f"{self._api_base_url}/users/@me/guilds/{guild_id}/member",
            operation_name="get_current_user_guild_member",
            headers={"Authorization": f"Bearer {token}"},
        )


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
