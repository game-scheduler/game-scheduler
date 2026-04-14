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


"""Comprehensive unit tests for shared Discord API client."""

import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

import shared.discord.client as discord_client_module
from shared.cache.keys import CacheKeys
from shared.cache.operations import CacheOperation
from shared.cache.ttl import CacheTTL
from shared.discord.client import (
    DiscordAPIClient,
    DiscordAPIError,
    _get_global_client,
    fetch_channel_name_safe,
    fetch_guild_name_safe,
    fetch_user_display_name_safe,
    get_guild_channels_safe,
)


@pytest.fixture
def discord_client():
    """Create Discord API client for testing."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="test.bot.token123456789",
    )


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.claim_global_slot = AsyncMock(return_value=0)
    redis.claim_global_and_channel_slot = AsyncMock(return_value=0)
    return redis


class TestDiscordAPIError:
    """Test DiscordAPIError exception class."""

    def test_error_initialization(self):
        """Test error is properly initialized with all fields."""
        headers = {"x-ratelimit-remaining": "0"}
        error = DiscordAPIError(429, "Rate limit exceeded", headers)

        assert error.status == 429
        assert error.message == "Rate limit exceeded"
        assert error.headers == headers
        assert "Discord API error 429" in str(error)

    def test_error_without_headers(self):
        """Test error initialization without headers."""
        error = DiscordAPIError(404, "Not found")

        assert error.status == 404
        assert error.message == "Not found"
        assert error.headers == {}


class TestDiscordAPIClientInitialization:
    """Test DiscordAPIClient initialization and lifecycle."""

    def test_client_initialization(self):
        """Test client is properly initialized with credentials."""
        client = DiscordAPIClient(
            client_id="my_client_id",
            client_secret="my_secret",
            bot_token="my_bot_token",
        )

        assert client.client_id == "my_client_id"
        assert client.client_secret == "my_secret"
        assert client.bot_token == "my_bot_token"
        assert client._session is None
        assert isinstance(client._guild_locks, dict)
        assert len(client._guild_locks) == 0

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, discord_client):
        """Test session is created when none exists."""
        assert discord_client._session is None

        session = await discord_client._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)
        await session.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self, discord_client):
        """Test existing session is reused."""
        session1 = await discord_client._get_session()
        session2 = await discord_client._get_session()

        assert session1 is session2
        await session1.close()

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed_session(self, discord_client):
        """Test new session is created if existing one is closed."""
        session1 = await discord_client._get_session()
        await session1.close()

        session2 = await discord_client._get_session()

        assert session2 is not session1
        assert not session2.closed
        await session2.close()

    @pytest.mark.asyncio
    async def test_close_session(self, discord_client):
        """Test session cleanup."""
        mock_session = AsyncMock()
        mock_session.closed = False
        discord_client._session = mock_session

        await discord_client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_already_closed_session(self, discord_client):
        """Test closing already closed session does nothing."""
        mock_session = AsyncMock()
        mock_session.closed = True
        discord_client._session = mock_session

        await discord_client.close()

        mock_session.close.assert_not_called()


class TestTokenDetection:
    """Test token type detection and authorization header generation."""

    def test_bot_token_detection(self, discord_client):
        """Test bot token is correctly identified (2 dots)."""
        bot_token = "test.bot.token123456789"

        header = discord_client._get_auth_header(bot_token)

        assert header == f"Bot {bot_token}"

    def test_oauth_token_detection(self, discord_client):
        """Test OAuth token (1 dot) is detected and uses Bearer auth."""
        oauth_token = "oauth.token"

        header = discord_client._get_auth_header(oauth_token)

        assert header == f"Bearer {oauth_token}"

    def test_invalid_token_with_zero_dots(self, discord_client):
        """Test token with 0 dots raises ValueError."""
        token_with_zero_dots = "6qrZcUqja7812RVdnEKjpzOL4CvHBFG"

        with pytest.raises(
            ValueError,
            match="Invalid Discord token format.*expected 1 or 2 dots, got 0",
        ):
            discord_client._get_auth_header(token_with_zero_dots)

    def test_invalid_token_with_three_dots(self, discord_client):
        """Test token with 3 dots raises ValueError."""
        token_with_three_dots = "part1.part2.part3.part4"

        with pytest.raises(
            ValueError,
            match="Invalid Discord token format.*expected 1 or 2 dots, got 3",
        ):
            discord_client._get_auth_header(token_with_three_dots)

    def test_invalid_token_with_many_dots(self, discord_client):
        """Test token with many dots raises ValueError."""
        token_with_many_dots = "part1.part2.part3.part4.part5"

        with pytest.raises(
            ValueError,
            match="Invalid Discord token format.*expected 1 or 2 dots, got 4",
        ):
            discord_client._get_auth_header(token_with_many_dots)

    def test_default_to_bot_token_when_none(self, discord_client):
        """Test that None token defaults to self.bot_token."""
        header = discord_client._get_auth_header(None)

        assert header == f"Bot {discord_client.bot_token}"

    def test_default_to_bot_token_when_omitted(self, discord_client):
        """Test that omitted token defaults to self.bot_token."""
        header = discord_client._get_auth_header()

        assert header == f"Bot {discord_client.bot_token}"


class TestMakeAPIRequest:
    """Test _make_api_request base method."""

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_successful_get_request_with_caching(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """Test successful GET request with caching."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"id": "123", "name": "test"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/users/123",
            operation_name="test_operation",
            headers={"Authorization": "Bot token"},
            cache_key="test:key",
            cache_ttl=300,
        )

        assert result == {"id": "123", "name": "test"}
        mock_session.request.assert_called_once_with(
            "GET",
            "https://discord.com/api/v10/users/123",
            headers={"Authorization": "Bot token"},
        )
        mock_redis.set.assert_called_once_with(
            "test:key", json.dumps({"id": "123", "name": "test"}), ttl=300
        )

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_cache_key_with_ttl_none_writes_to_redis(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """_make_api_request writes to Redis when cache_key is set and cache_ttl=None."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"id": "42", "name": "general"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/channels/42",
            operation_name="get_channel",
            headers={"Authorization": "Bot token"},
            cache_key="discord:channel:42",
            cache_ttl=None,
        )

        mock_redis.set.assert_called_once_with(
            "discord:channel:42", json.dumps({"id": "42", "name": "general"}), ttl=None
        )

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_cache_key_with_ttl_int_writes_to_redis(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """Regression guard: _make_api_request still writes to Redis when cache_ttl is an int."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"id": "99", "name": "TestRole"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/guilds/1/roles",
            operation_name="get_roles",
            headers={"Authorization": "Bot token"},
            cache_key="discord:guild_roles:1",
            cache_ttl=300,
        )

        mock_redis.set.assert_called_once_with(
            "discord:guild_roles:1", json.dumps({"id": "99", "name": "TestRole"}), ttl=300
        )

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_successful_post_request_without_caching(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """Test successful POST request without caching."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"access_token": "token123"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client._make_api_request(
            method="POST",
            url="https://discord.com/api/v10/oauth2/token",
            operation_name="exchange_code",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "authorization_code"},
        )

        assert result == {"access_token": "token123"}
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_404_error_with_cache_invalidation(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """Test 404 error caches negative result."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Not Found"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client._make_api_request(
                method="GET",
                url="https://discord.com/api/v10/users/999",
                operation_name="fetch_user",
                headers={"Authorization": "Bot token"},
                cache_key="test:user:999",
            )

        assert exc_info.value.status == 404
        mock_redis.set.assert_called_once_with(
            "test:user:999", json.dumps({"error": "not_found"}), ttl=60
        )

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_400_error_raises_exception(self, mock_get_redis, discord_client, mock_redis):
        """Test 400 error raises DiscordAPIError."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Bad Request"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client._make_api_request(
                method="POST",
                url="https://discord.com/api/v10/channels/123",
                operation_name="create_channel",
                headers={"Authorization": "Bot token"},
            )

        assert exc_info.value.status == 400
        assert exc_info.value.message == "Bad Request"

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_500_error_raises_exception(self, mock_get_redis, discord_client, mock_redis):
        """Test 500 error raises DiscordAPIError."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Internal Server Error"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client._make_api_request(
                method="GET",
                url="https://discord.com/api/v10/guilds/123",
                operation_name="fetch_guild",
                headers={"Authorization": "Bot token"},
            )

        assert exc_info.value.status == 500
        assert exc_info.value.message == "Internal Server Error"

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_network_error_handling(self, mock_get_redis, discord_client, mock_redis):
        """Test network error is properly handled."""
        mock_get_redis.return_value = mock_redis

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("Connection timeout")
        )
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client._make_api_request(
                method="GET",
                url="https://discord.com/api/v10/users/123",
                operation_name="fetch_user",
                headers={"Authorization": "Bot token"},
            )

        assert exc_info.value.status == 500
        assert "Network error" in exc_info.value.message
        assert "Connection timeout" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_non_json_response_raises_error(self, mock_get_redis, discord_client, mock_redis):
        """Non-JSON response body raises DiscordAPIError with HTTP status."""
        mock_get_redis.return_value = mock_redis

        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client._make_api_request(
                method="GET",
                url="https://discord.com/api/v10/guilds/123",
                operation_name="fetch_guild",
                headers={"Authorization": "Bot token"},
            )

        assert exc_info.value.status == 503
        assert "Non-JSON response" in exc_info.value.message


class TestMakeAPIRequestRateLimit:
    """Verify _make_api_request enforces global (and optionally per-channel) rate limits."""

    def _make_mock_session(self, response_data: dict) -> MagicMock:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value=response_data)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_response)
        ctx.__aexit__ = AsyncMock(return_value=None)
        session = MagicMock()
        session.closed = False
        session.request = MagicMock(return_value=ctx)
        return session

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_global_slot_claimed_before_http_when_no_channel(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """When no channel_id, claim_global_slot is awaited before the HTTP call."""
        mock_get_redis.return_value = mock_redis
        mock_redis.claim_global_slot = AsyncMock(return_value=0)
        discord_client._session = self._make_mock_session({"id": "1"})

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/users/1",
            operation_name="test_op",
            headers={"Authorization": "Bot token"},
        )

        mock_redis.claim_global_slot.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_global_and_channel_slot_claimed_when_channel_id_provided(
        self, mock_get_redis, discord_client, mock_redis
    ):
        """When channel_id is provided, claim_global_and_channel_slot is used."""
        mock_get_redis.return_value = mock_redis
        mock_redis.claim_global_and_channel_slot = AsyncMock(return_value=0)
        discord_client._session = self._make_mock_session({"id": "1"})

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/users/1",
            operation_name="test_op",
            headers={"Authorization": "Bot token"},
            channel_id="123456789",
        )

        mock_redis.claim_global_and_channel_slot.assert_awaited_once_with(
            "123456789", global_max=25
        )

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("shared.cache.client.get_redis_client")
    async def test_sleeps_when_rate_limit_returns_nonzero(
        self, mock_get_redis, mock_sleep, discord_client, mock_redis
    ):
        """When rate limiter returns > 0, asyncio.sleep is called with wait_s before HTTP."""
        mock_get_redis.return_value = mock_redis
        mock_redis.claim_global_slot = AsyncMock(side_effect=[40, 0])
        discord_client._session = self._make_mock_session({"id": "1"})

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/users/1",
            operation_name="test_op",
            headers={"Authorization": "Bot token"},
        )

        mock_sleep.assert_awaited_once_with(pytest.approx(0.04, rel=1e-3))
        assert discord_client._session.request.call_count == 1

    @pytest.mark.asyncio
    @patch("shared.cache.client.get_redis_client")
    async def test_accepts_global_max_kwarg(self, mock_get_redis, discord_client, mock_redis):
        """_make_api_request accepts global_max and forwards it to the rate-limit claim call."""
        mock_get_redis.return_value = mock_redis
        mock_redis.claim_global_slot = AsyncMock(return_value=0)
        discord_client._session = self._make_mock_session({"id": "1"})

        await discord_client._make_api_request(
            method="GET",
            url="https://discord.com/api/v10/users/1",
            operation_name="test_op",
            headers={"Authorization": "Bot token"},
            global_max=45,
        )

        mock_redis.claim_global_slot.assert_awaited_once_with(global_max=45)


class TestOAuth2Methods:
    """Test OAuth2 authentication methods."""

    @pytest.mark.asyncio
    @patch.object(DiscordAPIClient, "_make_api_request")
    async def test_exchange_code_success(self, mock_make_request, discord_client):
        """Test successful authorization code exchange."""
        mock_make_request.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 604800,
            "token_type": "Bearer",
        }

        result = await discord_client.exchange_code(
            code="auth_code_123", redirect_uri="http://localhost:3000/callback"
        )

        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_in"] == 604800
        assert result["token_type"] == "Bearer"

        mock_make_request.assert_called_once()
        call_kwargs = mock_make_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert "oauth2/token" in call_kwargs["url"]
        assert "client_id" in call_kwargs["data"]
        assert "client_secret" in call_kwargs["data"]
        assert call_kwargs["data"]["code"] == "auth_code_123"

    @pytest.mark.asyncio
    @patch.object(DiscordAPIClient, "_make_api_request")
    async def test_exchange_code_invalid_code(self, mock_make_request, discord_client):
        """Test code exchange with invalid authorization code."""
        mock_make_request.side_effect = DiscordAPIError(400, "Invalid authorization code", {})

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.exchange_code(
                code="invalid_code", redirect_uri="http://localhost:3000/callback"
            )

        assert exc_info.value.status == 400
        assert "Invalid authorization code" in exc_info.value.message

    @pytest.mark.asyncio
    @patch.object(DiscordAPIClient, "_make_api_request")
    async def test_exchange_code_network_error(self, mock_make_request, discord_client):
        """Test network error during code exchange."""
        mock_make_request.side_effect = DiscordAPIError(500, "Network error: Connection failed")

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.exchange_code(
                code="test_code", redirect_uri="http://localhost:3000/callback"
            )

        assert exc_info.value.status == 500
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    @patch.object(DiscordAPIClient, "_make_api_request")
    async def test_refresh_token_success(self, mock_make_request, discord_client):
        """Test successful token refresh."""
        mock_make_request.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 604800,
        }

        result = await discord_client.refresh_token(refresh_token="old_refresh_token")

        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_in"] == 604800

    @pytest.mark.asyncio
    @patch.object(DiscordAPIClient, "_make_api_request")
    async def test_refresh_token_invalid_token(self, mock_make_request, discord_client):
        """Test token refresh with invalid refresh token."""
        mock_make_request.side_effect = DiscordAPIError(400, "Invalid refresh token", {})

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.refresh_token(refresh_token="invalid_token")

        assert exc_info.value.status == 400
        assert "Invalid refresh token" in exc_info.value.message


class TestUserDataMethods:
    """Test user data fetching methods."""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, discord_client):
        """Test successful user info fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value={
                "id": "123456789",
                "username": "testuser",
                "avatar": "avatar_hash",
                "discriminator": "0001",
            }
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_user_info(access_token="user_access_token")

        assert result["id"] == "123456789"
        assert result["username"] == "testuser"
        assert result["avatar"] == "avatar_hash"

    @pytest.mark.asyncio
    async def test_get_user_info_unauthorized(self, discord_client):
        """Test user info fetch with invalid token."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Unauthorized"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_user_info(access_token="invalid_token")

        assert exc_info.value.status == 401
        assert exc_info.value.headers is not None


class TestGuildMethods:
    """Test guild-related methods."""

    @pytest.mark.asyncio
    async def test_get_guilds_without_user_id(self, discord_client):
        """Test fetching guilds without user_id (no caching by user)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "guild1", "name": "Test Guild 1", "icon": "icon1"},
                {"id": "guild2", "name": "Test Guild 2", "icon": "icon2"},
            ]
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_guilds(token="test.token")

        assert len(result) == 2
        assert result[0]["name"] == "Test Guild 1"
        assert result[1]["name"] == "Test Guild 2"

    @pytest.mark.asyncio
    async def test_get_guilds_with_cache_miss(self, discord_client, mock_redis):
        """Test fetching guilds with cache miss."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        guilds_data = [
            {"id": "guild1", "name": "Test Guild 1"},
            {"id": "guild2", "name": "Test Guild 2"},
        ]
        mock_response.json = AsyncMock(return_value=guilds_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guilds(token="test.token", user_id="user123")

            assert len(result) == 2
            assert result[0]["name"] == "Test Guild 1"
            # Double-checked locking means get is called twice (before and after acquiring lock)
            assert mock_redis.get.call_count == 2
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_guilds_with_cache_hit(self, discord_client, mock_redis):
        """Test fetching guilds with cache hit."""
        cached_guilds = [{"id": "guild1", "name": "Cached Guild"}]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_guilds))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guilds(token="test_token", user_id="user123")

            assert len(result) == 1
            assert result[0]["name"] == "Cached Guild"
            mock_redis.get.assert_called_once_with("user_guilds:user123")
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_guilds_with_bot_token(self, discord_client):
        """Test fetching guilds with bot token (default)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "guild1", "name": "Bot Guild 1"},
                {"id": "guild2", "name": "Bot Guild 2"},
            ]
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_guilds()

        assert len(result) == 2
        assert result[0]["name"] == "Bot Guild 1"

    @pytest.mark.asyncio
    async def test_get_guild_channels_success(self, discord_client):
        """Test fetching guild channels."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "channel1", "name": "general", "type": 0},
                {"id": "channel2", "name": "announcements", "type": 0},
            ]
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        # Mock Redis cache to return None (cache miss)
        with patch("shared.cache.client.get_redis_client") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guild_channels(guild_id="guild123")

            assert len(result) == 2
            assert result[0]["name"] == "general"

    @pytest.mark.asyncio
    async def test_get_guild_channels_cache_hit(self, discord_client):
        """Test get_guild_channels() returns cached data."""
        cached_data = [
            {"id": "channel1", "name": "cached-general", "type": 0},
            {"id": "channel2", "name": "cached-announcements", "type": 0},
        ]

        with patch("shared.cache.client.get_redis_client") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guild_channels(guild_id="guild123")

            assert len(result) == 2
            assert result[0]["name"] == "cached-general"
            # Verify no Discord API call was made
            assert discord_client._session is None

    @pytest.mark.asyncio
    async def test_get_guild_channels_force_refresh_bypasses_cache(self, discord_client):
        """Test get_guild_channels() skips cache when force_refresh=True."""
        cached_data = [{"id": "channel1", "name": "stale-channel", "type": 0}]
        fresh_data = [{"id": "channel2", "name": "new-channel", "type": 0}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=fresh_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.cache.client.get_redis_client") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
            mock_redis.set = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guild_channels(
                guild_id="guild123", force_refresh=True
            )

            assert len(result) == 1
            assert result[0]["name"] == "new-channel"
            # Cache was not read
            mock_redis.get.assert_not_called()
            # Fresh data was written back to cache
            mock_redis.set.assert_called_once()


class TestUnifiedTokenFunctionality:
    """Test that unified methods work with both bot and OAuth tokens."""

    @pytest.mark.asyncio
    async def test_get_guilds_with_bot_token_default(self, discord_client, mock_redis):
        """Test get_guilds() uses bot token by default."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "guild1", "name": "Bot Guild 1"},
            ]
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guilds()

            # Verify bot token was used (Bot prefix)
            call_args = mock_session.get.call_args
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"].startswith("Bot ")
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_guilds_with_explicit_oauth_token(self, discord_client, mock_redis):
        """Test get_guilds() accepts OAuth token."""
        oauth_token = "6qrZcUqja7812RVdnEKjpzOL.4CvHBFG"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "guild1", "name": "OAuth Guild 1"},
            ]
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guilds(token=oauth_token)

            # Verify OAuth token was used (Bearer prefix)
            call_args = mock_session.get.call_args
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {oauth_token}"
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_guilds_retry_429_with_retry_after(self, discord_client):
        """Test get_guilds() retries on 429 with retry-after header."""
        # First attempt: 429 with retry-after header
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {
            "retry-after": "0.1",
            "x-ratelimit-remaining": "0",
        }
        mock_response_429.json = AsyncMock(return_value={"message": "You are being rate limited"})

        # Second attempt: success
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.headers = {"x-ratelimit-remaining": "50"}
        mock_response_200.json = AsyncMock(return_value=[{"id": "guild1", "name": "Test Guild"}])

        mock_session = MagicMock()
        mock_session.closed = False

        # Create context managers for each response
        mock_cm_429 = MagicMock()
        mock_cm_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_cm_429.__aexit__ = AsyncMock(return_value=None)

        mock_cm_200 = MagicMock()
        mock_cm_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_cm_200.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(side_effect=[mock_cm_429, mock_cm_200])
        discord_client._session = mock_session

        # Execute and verify retry succeeded
        result = await discord_client.get_guilds()
        assert len(result) == 1
        assert result[0]["name"] == "Test Guild"
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_guilds_retry_429_with_reset_after(self, discord_client):
        """Test get_guilds() retries on 429 with x-ratelimit-reset-after header."""
        # First attempt: 429 with x-ratelimit-reset-after header
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {
            "x-ratelimit-reset-after": "0.1",
            "x-ratelimit-remaining": "0",
        }
        mock_response_429.json = AsyncMock(return_value={"message": "You are being rate limited"})

        # Second attempt: success
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.headers = {"x-ratelimit-remaining": "50"}
        mock_response_200.json = AsyncMock(return_value=[{"id": "guild1", "name": "Test Guild"}])

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm_429 = MagicMock()
        mock_cm_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_cm_429.__aexit__ = AsyncMock(return_value=None)

        mock_cm_200 = MagicMock()
        mock_cm_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_cm_200.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(side_effect=[mock_cm_429, mock_cm_200])
        discord_client._session = mock_session

        result = await discord_client.get_guilds()
        assert len(result) == 1
        assert result[0]["name"] == "Test Guild"
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_guilds_retry_exhausted(self, discord_client):
        """Test get_guilds() raises error after max retries exhausted."""
        # All attempts return 429
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {
            "retry-after": "0.01",
            "x-ratelimit-remaining": "0",
        }
        mock_response_429.json = AsyncMock(return_value={"message": "You are being rate limited"})

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        # Return same 429 response for all 3 attempts
        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        # Verify it raises after exhausting retries
        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guilds()

        assert exc_info.value.status == 429
        assert "rate limited" in exc_info.value.message.lower()
        assert mock_session.get.call_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_get_guilds_network_error(self, discord_client):
        """Test get_guilds() raises error on network failure."""
        mock_session = MagicMock()
        mock_session.closed = False

        # Network error during request
        mock_cm_error = MagicMock()
        mock_cm_error.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection timeout"))
        mock_cm_error.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm_error)
        discord_client._session = mock_session

        # Verify network error raises DiscordAPIError with status 500
        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guilds()

        assert exc_info.value.status == 500
        assert "network error" in exc_info.value.message.lower()
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_guild_with_bot_token(self, discord_client, mock_redis):
        """Test fetch_guild() works with bot token."""
        guild_data = {"id": "guild123", "name": "Test Guild"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=guild_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild("guild123")

            # Verify bot token was used by default
            call_args = mock_session.request.call_args
            assert call_args[1]["headers"]["Authorization"].startswith("Bot ")
            assert result["id"] == "guild123"

    @pytest.mark.asyncio
    async def test_fetch_guild_with_oauth_token(self, discord_client, mock_redis):
        """Test fetch_guild() accepts OAuth token parameter."""
        oauth_token = "6qrZcUqja7812RVdnEKjpzOL.4CvHBFG"
        guild_data = {"id": "guild123", "name": "Test Guild"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=guild_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild("guild123", token=oauth_token)

            # Verify OAuth token was used
            call_args = mock_session.request.call_args
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {oauth_token}"
            assert result["id"] == "guild123"

    @pytest.mark.asyncio
    async def test_fetch_channel_with_oauth_token(self, discord_client, mock_redis):
        """Test fetch_channel() accepts OAuth token parameter."""
        oauth_token = "6qrZcUqja7812RVdnEKjpzOL.4CvHBFG"
        channel_data = {"id": "channel123", "name": "general", "type": 0}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=channel_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_channel("channel123", token=oauth_token)

            # Verify OAuth token was used
            call_args = mock_session.get.call_args
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {oauth_token}"
            assert result["id"] == "channel123"

    @pytest.mark.asyncio
    async def test_fetch_user_with_oauth_token(self, discord_client, mock_redis):
        """Test fetch_user() accepts OAuth token parameter."""
        oauth_token = "6qrZcUqja7812RVdnEKjpzOL.4CvHBFG"
        user_data = {"id": "user123", "username": "testuser", "discriminator": "1234"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=user_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_user("user123", token=oauth_token)

            # Verify OAuth token was used
            call_args = mock_session.request.call_args
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {oauth_token}"
            assert result["id"] == "user123"


class TestCachedResourceMethods:
    """Test methods that use Redis caching."""

    @pytest.mark.asyncio
    async def test_fetch_channel_cache_miss(self, discord_client, mock_redis):
        """Test fetching channel with cache miss."""
        channel_data = {"id": "channel123", "name": "general", "type": 0}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=channel_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch(
            "shared.discord.client.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await discord_client.fetch_channel(channel_id="channel123")

            assert result["name"] == "general"
            mock_redis.get.assert_called_once_with("discord:channel:channel123")
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_channel_cache_hit(self, discord_client, mock_redis):
        """Test fetching channel with cache hit."""
        cached_channel = {"id": "channel123", "name": "cached-general"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_channel))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_channel(channel_id="channel123")

            assert result["name"] == "cached-general"
            mock_redis.get.assert_called_once()
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_channel_not_found(self, discord_client, mock_redis):
        """Test fetching non-existent channel caches 404."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Unknown Channel"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.fetch_channel(channel_id="nonexistent")

            assert exc_info.value.status == 404
            mock_redis.set.assert_called_once()
            cached_args = mock_redis.set.call_args
            assert "error" in json.loads(cached_args[0][1])

    @pytest.mark.asyncio
    async def test_fetch_guild_cache_miss(self, discord_client, mock_redis):
        """Test fetching guild with cache miss."""
        guild_data = {"id": "guild123", "name": "Test Server"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=guild_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild(guild_id="guild123")

            assert result["name"] == "Test Server"
            mock_redis.get.assert_called_once_with("discord:guild:guild123")
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_guild_cache_hit(self, discord_client, mock_redis):
        """Test fetching guild with cache hit."""
        cached_guild = {"id": "guild123", "name": "Cached Server"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_guild))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild(guild_id="guild123")

            assert result["name"] == "Cached Server"
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_guild_roles_cache_miss(self, discord_client, mock_redis):
        """Test fetching guild roles with cache miss."""
        roles_data = [
            {"id": "role1", "name": "Admin"},
            {"id": "role2", "name": "Member"},
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=roles_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild_roles(guild_id="guild123")

            assert len(result) == 2
            assert result[0]["name"] == "Admin"
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_user_cache_miss(self, discord_client, mock_redis):
        """Test fetching user with cache miss."""
        user_data = {"id": "user123", "username": "testuser", "avatar": "avatar_hash"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=user_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_user(user_id="user123")

            assert result["username"] == "testuser"
            mock_redis.get.assert_called_once_with("discord:user:user123")
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_user_cache_hit(self, discord_client, mock_redis):
        """Test fetching user with cache hit."""
        cached_user = {"id": "user123", "username": "cacheduser"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_user))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_user(user_id="user123")

            assert result["username"] == "cacheduser"
            mock_redis.set.assert_not_called()


class TestGuildMemberMethods:
    """Test guild member related methods."""

    @pytest.mark.asyncio
    async def test_get_guild_member_success(self, discord_client, mock_redis):
        """Test successful guild member fetch."""
        member_data = {
            "user": {"id": "123456789", "username": "testuser"},
            "roles": ["role1", "role2"],
            "nick": "TestNick",
        }
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=member_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch(
            "shared.discord.client.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await discord_client.get_guild_member(guild_id="guild123", user_id="123456789")

            assert result["user"]["id"] == "123456789"
            assert result["nick"] == "TestNick"
            assert len(result["roles"]) == 2

    @pytest.mark.asyncio
    async def test_get_guild_member_not_found(self, discord_client, mock_redis):
        """Test guild member fetch when user not in guild."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Unknown Member"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            pytest.raises(DiscordAPIError) as exc_info,
        ):
            await discord_client.get_guild_member(guild_id="guild123", user_id="nonexistent")

        assert exc_info.value.status == 404

    @pytest.mark.asyncio
    async def test_get_guild_member_cache_miss(self, discord_client, mock_redis):
        """Test that a cache miss fetches from Discord and stores the result in Redis."""
        member_data = {
            "user": {"id": "123456789", "username": "testuser"},
            "roles": ["role1", "role2"],
        }
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=member_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guild_member(guild_id="guild123", user_id="123456789")

            assert result["user"]["id"] == "123456789"
            mock_redis.get.assert_called_once_with("discord:member:guild123:123456789")
            mock_redis.set.assert_called_once()
            set_args = mock_redis.set.call_args
            assert set_args[0][0] == "discord:member:guild123:123456789"
            assert set_args[1]["ttl"] == CacheTTL.DISCORD_MEMBER

    @pytest.mark.asyncio
    async def test_get_guild_member_cache_hit(self, discord_client, mock_redis):
        """Test that a cache hit returns stored data without a REST call."""
        cached_member = {
            "user": {"id": "123456789", "username": "cacheduser"},
            "roles": ["role1"],
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_member))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_guild_member(guild_id="guild123", user_id="123456789")

            assert result["user"]["username"] == "cacheduser"
            mock_redis.get.assert_called_once_with("discord:member:guild123:123456789")
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_success(self, discord_client):
        """Test successful batch guild members fetch."""
        with patch.object(
            discord_client, "get_guild_member", new_callable=AsyncMock
        ) as mock_get_member:
            mock_get_member.side_effect = [
                {"user": {"id": "user1"}, "nick": "Nick1"},
                {"user": {"id": "user2"}, "nick": "Nick2"},
                {"user": {"id": "user3"}, "nick": "Nick3"},
            ]

            result = await discord_client.get_guild_members_batch(
                guild_id="guild123", user_ids=["user1", "user2", "user3"]
            )

            assert len(result) == 3
            assert result[0]["user"]["id"] == "user1"
            assert result[1]["user"]["id"] == "user2"
            assert result[2]["user"]["id"] == "user3"
            assert mock_get_member.call_count == 3

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_skip_not_found(self, discord_client):
        """Test batch fetch skips users who left guild (404 errors)."""
        with patch.object(
            discord_client, "get_guild_member", new_callable=AsyncMock
        ) as mock_get_member:
            mock_get_member.side_effect = [
                {"user": {"id": "user1"}, "nick": "Nick1"},
                DiscordAPIError(404, "Unknown Member"),
                {"user": {"id": "user3"}, "nick": "Nick3"},
                DiscordAPIError(404, "Unknown Member"),
            ]

            result = await discord_client.get_guild_members_batch(
                guild_id="guild123", user_ids=["user1", "user2", "user3", "user4"]
            )

            assert len(result) == 2
            assert result[0]["user"]["id"] == "user1"
            assert result[1]["user"]["id"] == "user3"
            assert mock_get_member.call_count == 4

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_raises_on_other_errors(self, discord_client):
        """Test batch fetch raises on non-404 API errors."""
        with patch.object(
            discord_client, "get_guild_member", new_callable=AsyncMock
        ) as mock_get_member:
            mock_get_member.side_effect = DiscordAPIError(500, "Internal Server Error")

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.get_guild_members_batch(
                    guild_id="guild123", user_ids=["user1"]
                )

            assert exc_info.value.status == 500
            assert "Internal Server Error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_empty_list(self, discord_client):
        """Test batch fetch with empty user list."""
        result = await discord_client.get_guild_members_batch(guild_id="guild123", user_ids=[])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_guild_member_accepts_global_max(self, discord_client, mock_redis):
        """get_guild_member accepts global_max and passes it to _make_api_request."""
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        member_data = {"user": {"id": "u1"}, "roles": []}

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis
            with patch.object(
                discord_client, "_make_api_request", new_callable=AsyncMock
            ) as mock_api:
                mock_api.return_value = member_data
                await discord_client.get_guild_member("guild1", "u1", global_max=45)
                call_kwargs = mock_api.call_args.kwargs
                assert call_kwargs.get("global_max") == 45

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_forwards_global_max(self, discord_client):
        """get_guild_members_batch forwards global_max to each get_guild_member call."""
        with patch.object(
            discord_client, "get_guild_member", new_callable=AsyncMock
        ) as mock_get_member:
            mock_get_member.side_effect = [
                {"user": {"id": "u1"}},
                {"user": {"id": "u2"}},
            ]
            await discord_client.get_guild_members_batch(
                guild_id="guild1", user_ids=["u1", "u2"], global_max=45
            )
            for call in mock_get_member.call_args_list:
                assert call.kwargs.get("global_max") == 45

    @pytest.mark.asyncio
    async def test_get_guild_members_batch_concurrent(self, discord_client):
        """get_guild_members_batch uses asyncio.gather for concurrent dispatch."""
        with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
            with patch.object(
                discord_client, "get_guild_member", new_callable=AsyncMock
            ) as mock_get_member:
                mock_get_member.side_effect = [
                    {"user": {"id": "u1"}},
                    {"user": {"id": "u2"}},
                    {"user": {"id": "u3"}},
                ]
                await discord_client.get_guild_members_batch(
                    guild_id="guild1", user_ids=["u1", "u2", "u3"]
                )
            mock_gather.assert_called_once()


class TestConcurrencyAndLocking:
    """Test concurrency control and locking mechanisms."""

    @pytest.mark.asyncio
    async def test_user_guilds_double_checked_locking(self, discord_client, mock_redis):
        """Test double-checked locking prevents duplicate API calls."""
        guilds_data = [{"id": "guild1", "name": "Test Guild"}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=guilds_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        call_count = 0

        async def mock_get_side_effect(key):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return json.dumps(guilds_data)

        mock_redis.get = AsyncMock(side_effect=mock_get_side_effect)

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            async def concurrent_fetch():
                return await discord_client.get_guilds(token="test_token", user_id="user123")

            results = await asyncio.gather(concurrent_fetch(), concurrent_fetch())

            assert len(results[0]) == 1
            assert len(results[1]) == 1
            # With the side effect returning cached data on second call, no API call is made
            # Both requests hit the cache after the first one populates it
            assert mock_session.get.call_count == 0

    @pytest.mark.asyncio
    async def test_guild_locks_created_per_user(self, discord_client):
        """Test that separate locks are created for different users."""
        with patch.object(
            discord_client, "_fetch_guilds_uncached", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = [{"id": "guild1", "name": "Test Guild"}]

            with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
                mock_redis = AsyncMock()
                mock_redis.get = AsyncMock(return_value=None)
                mock_redis.set = AsyncMock()
                mock_get_redis.return_value = mock_redis

                await discord_client.get_guilds(token="token1", user_id="user1")
                await discord_client.get_guilds(token="token2", user_id="user2")

                assert "user1" in discord_client._guild_locks
                assert "user2" in discord_client._guild_locks
                assert discord_client._guild_locks["user1"] != discord_client._guild_locks["user2"]


class TestLoggingMethods:
    """Test logging helper methods."""

    def test_log_request(self, discord_client):
        """Test request logging."""
        with patch("shared.discord.client.logger") as mock_logger:
            discord_client._log_request("GET", "https://discord.com/api/v10/users/@me", "test_op")

            mock_logger.info.assert_called_once()
            # Check that the call has the format string and the method as an argument
            call_args = mock_logger.info.call_args[0]
            assert call_args[0] == "Discord API: %s %s (%s)"
            assert call_args[1] == "GET"
            assert "test_op" in call_args

    def test_log_response(self, discord_client):
        """Test response logging."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "x-ratelimit-remaining": "100",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset-after": "60",
        }

        with patch("shared.discord.client.logger") as mock_logger:
            discord_client._log_response(mock_response, "extra info")

            mock_logger.info.assert_called_once()
            # Check format string and status code argument
            call_args = mock_logger.info.call_args[0]
            assert call_args[0] == "Discord API Response: %s - %s"
            assert call_args[1] == 200
            # Check response details (3rd argument)
            assert "100" in call_args[2]
            assert "extra info" in call_args[2]

    def test_log_response_without_rate_limit_headers(self, discord_client):
        """Test response logging when rate limit headers are missing."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "50"}

        with patch("shared.discord.client.logger") as mock_logger:
            discord_client._log_response(mock_response)

            mock_logger.info.assert_called_once()
            # Check format string and response details argument which contains N/A
            call_args = mock_logger.info.call_args[0]
            assert call_args[0] == "Discord API Response: %s - %s"
            assert "N/A" in call_args[2]


# ---------------------------------------------------------------------------
# get_application_info and api_base_url tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis_cache_miss():
    """Mock Redis as a cache miss so tests exercise the _make_api_request path."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    with patch(
        "shared.discord.client.cache_client.get_redis_client",
        AsyncMock(return_value=mock_redis),
    ):
        yield mock_redis


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_url(discord_client, mock_redis_cache_miss):
    """Test that get_application_info calls the Discord applications/@me endpoint."""
    expected_url = "https://discord.com/api/v10/oauth2/applications/@me"
    mock_request = AsyncMock(return_value={"id": "123", "name": "TestBot"})

    with patch.object(discord_client, "_make_api_request", mock_request):
        await discord_client.get_application_info()

    call_kwargs = mock_request.call_args
    assert call_kwargs.kwargs.get("url") == expected_url or (
        len(call_kwargs.args) > 1 and call_kwargs.args[1] == expected_url
    )


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_cache_key(discord_client, mock_redis_cache_miss):
    """Test that get_application_info passes app_info() cache key to _get_or_fetch."""
    with patch.object(
        discord_client, "_get_or_fetch", new=AsyncMock(return_value={"id": "123", "name": "Bot"})
    ) as mock_gof:
        await discord_client.get_application_info()
    assert mock_gof.call_args.kwargs.get("cache_key") == CacheKeys.app_info()


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_ttl(discord_client, mock_redis_cache_miss):
    """Test that get_application_info passes APP_INFO TTL to _get_or_fetch."""
    with patch.object(
        discord_client, "_get_or_fetch", new=AsyncMock(return_value={"id": "123", "name": "Bot"})
    ) as mock_gof:
        await discord_client.get_application_info()
    assert mock_gof.call_args.kwargs.get("cache_ttl") == CacheTTL.APP_INFO


@pytest.mark.asyncio
async def test_get_application_info_returns_dict(discord_client, mock_redis_cache_miss):
    """Test that get_application_info returns the application info dict."""
    app_data = {"id": "123", "name": "TestBot", "owner": {"id": "456"}}
    mock_request = AsyncMock(return_value=app_data)

    with patch.object(discord_client, "_make_api_request", mock_request):
        result = await discord_client.get_application_info()

    assert result == app_data


@pytest.mark.asyncio
async def test_get_application_info_returns_cached_data(discord_client, mock_redis_cache_miss):
    """Test that get_application_info returns cached data without calling Discord."""
    app_data = {"id": "123", "name": "TestBot", "owner": {"id": "456"}}
    mock_redis_cache_miss.get.return_value = json.dumps(app_data)
    mock_request = AsyncMock()

    with patch.object(discord_client, "_make_api_request", mock_request):
        result = await discord_client.get_application_info()

    assert result == app_data
    mock_request.assert_not_awaited()


@pytest.fixture
def discord_client_fake_base():
    """Return a DiscordAPIClient with a fake api_base_url."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="Bot.test.bot_token",
        api_base_url="http://fake:9999",
    )


def _mock_session_returning(response_data: object) -> MagicMock:
    """Return a mock aiohttp session whose .get() yields a successful response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.headers = MagicMock()
    mock_response.headers.get = MagicMock(return_value="N/A")

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_response)
    ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = ctx
    return mock_session


@pytest.mark.asyncio
async def test_exchange_code_uses_api_base_url(
    discord_client_fake_base: DiscordAPIClient,
) -> None:
    """exchange_code must POST to api_base_url/oauth2/token, not the hardcoded Discord URL."""
    fake_token = {
        "access_token": "tok",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "ref",
        "scope": "identify",
    }
    mock_request = AsyncMock(return_value=fake_token)

    with patch.object(discord_client_fake_base, "_make_api_request", mock_request):
        await discord_client_fake_base.exchange_code("code123", "http://redirect")

    url_used = mock_request.call_args.kwargs.get("url")
    assert url_used == "http://fake:9999/oauth2/token"


@pytest.mark.asyncio
async def test_refresh_token_uses_api_base_url(
    discord_client_fake_base: DiscordAPIClient,
) -> None:
    """refresh_token must POST to api_base_url/oauth2/token, not the hardcoded Discord URL."""
    fake_token = {
        "access_token": "tok2",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "ref2",
        "scope": "identify",
    }
    mock_request = AsyncMock(return_value=fake_token)

    with patch.object(discord_client_fake_base, "_make_api_request", mock_request):
        await discord_client_fake_base.refresh_token("old_refresh_token.abc")

    url_used = mock_request.call_args.kwargs.get("url")
    assert url_used == "http://fake:9999/oauth2/token"


@pytest.mark.asyncio
async def test_get_user_info_uses_api_base_url(
    discord_client_fake_base: DiscordAPIClient,
) -> None:
    """get_user_info must GET api_base_url/users/@me, not the hardcoded Discord URL."""
    mock_session = _mock_session_returning({"id": "user123", "username": "testuser"})
    session_patch = patch.object(
        discord_client_fake_base, "_get_session", AsyncMock(return_value=mock_session)
    )
    with session_patch:
        await discord_client_fake_base.get_user_info("oauth_token.abc")

    actual_url = mock_session.get.call_args[0][0]
    assert actual_url == "http://fake:9999/users/@me"


@pytest.mark.asyncio
async def test_get_guilds_uses_api_base_url(
    discord_client_fake_base: DiscordAPIClient,
) -> None:
    """get_guilds must GET api_base_url/users/@me/guilds, not the hardcoded Discord URL."""
    mock_session = _mock_session_returning([{"id": "guild1", "name": "Test Guild"}])
    session_patch = patch.object(
        discord_client_fake_base, "_get_session", AsyncMock(return_value=mock_session)
    )
    with session_patch:
        await discord_client_fake_base.get_guilds()

    actual_url = mock_session.get.call_args[0][0]
    assert actual_url == "http://fake:9999/users/@me/guilds"


# ---------------------------------------------------------------------------
# Tests for uncovered error branches
# ---------------------------------------------------------------------------


class TestGetUserInfoNetworkError:
    """Test get_user_info() network error path."""

    @pytest.mark.asyncio
    async def test_get_user_info_network_error(self, discord_client):
        """get_user_info() raises DiscordAPIError(500) on network failure."""
        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_user_info("test_access_token")

        assert exc_info.value.status == 500
        assert "network error" in exc_info.value.message.lower()


class TestGetErrorMessageNonDict:
    """Test _get_error_message() with non-dict response data."""

    def test_get_error_message_non_dict_returns_default(self, discord_client):
        """_get_error_message() returns the default when response_data is not a dict."""
        result = discord_client._get_error_message(["item1", "item2"], "fallback_message")

        assert result == "fallback_message"


class TestProcessGuildsResponseHttpError:
    """Test _process_guilds_response() non-200/non-429 error path."""

    @pytest.mark.asyncio
    async def test_get_guilds_http_error_response(self, discord_client):
        """get_guilds() raises DiscordAPIError for non-200/non-429 HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Missing Permissions"})

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guilds()

        assert exc_info.value.status == 403

    @pytest.mark.asyncio
    async def test_get_guilds_http_error_non_dict_body(self, discord_client):
        """_process_guilds_response() uses default message when body is not a dict."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value=["unexpected", "list"])

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guilds()

        assert exc_info.value.status == 503
        assert exc_info.value.message == "Unknown error"

    @pytest.mark.asyncio
    async def test_get_guilds_non_json_response(self, discord_client):
        """_process_guilds_response() raises DiscordAPIError when body is not JSON."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guilds()

        assert exc_info.value.status == 503
        assert "Non-JSON response" in exc_info.value.message


class TestFetchGuildsUncachedSafetyRaise:
    """Test the safety raise at the end of _fetch_guilds_uncached."""

    @pytest.mark.asyncio
    async def test_fetch_guilds_uncached_raises_after_all_retries_return_none(self, discord_client):
        """Final safety raise in _fetch_guilds_uncached fires when all retries return None."""
        mock_session = MagicMock()
        mock_session.closed = False

        mock_response = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch.object(
            discord_client, "_process_guilds_response", new_callable=AsyncMock
        ) as mock_pgr:
            mock_pgr.return_value = None

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client._fetch_guilds_uncached(discord_client.bot_token)

        assert exc_info.value.status == 429
        assert "rate limit" in exc_info.value.message.lower()
        assert mock_pgr.await_count == 3


class TestGuildChannelsErrorPaths:
    """Test get_guild_channels() error branches."""

    @pytest.mark.asyncio
    async def test_get_guild_channels_http_error(self, discord_client, mock_redis):
        """get_guild_channels() raises DiscordAPIError for non-200 HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Missing Permissions"})

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.get_guild_channels("guild123")

        assert exc_info.value.status == 403

    @pytest.mark.asyncio
    async def test_get_guild_channels_network_error(self, discord_client, mock_redis):
        """get_guild_channels() raises DiscordAPIError(500) on network failure."""
        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Timeout"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.get_guild_channels("guild123")

        assert exc_info.value.status == 500
        assert "network error" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_get_guild_channels_non_json_response(self, discord_client, mock_redis):
        """get_guild_channels() raises DiscordAPIError when body is not JSON."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.get_guild_channels("guild123")

        assert exc_info.value.status == 503
        assert "Non-JSON response" in exc_info.value.message


class TestFetchChannelAndRolesErrorPaths:
    """Test fetch_channel(), fetch_guild_roles() error branches."""

    @pytest.mark.asyncio
    async def test_fetch_channel_network_error(self, discord_client, mock_redis):
        """fetch_channel() raises DiscordAPIError(500) on network failure."""
        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection reset"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.fetch_channel("channel123")

        assert exc_info.value.status == 500
        assert "network error" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_fetch_guild_roles_cache_hit(self, discord_client, mock_redis):
        """fetch_guild_roles() returns cached data without hitting Discord API."""
        roles_data = [
            {"id": "role1", "name": "Admin"},
            {"id": "role2", "name": "Member"},
        ]
        mock_redis.get = AsyncMock(return_value=json.dumps(roles_data))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.fetch_guild_roles("guild123")

        assert len(result) == 2
        assert result[0]["name"] == "Admin"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_guild_roles_http_error(self, discord_client, mock_redis):
        """fetch_guild_roles() raises DiscordAPIError for non-200 HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {"x-ratelimit-remaining": "50"}
        mock_response.json = AsyncMock(return_value={"message": "Missing Permissions"})

        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.request = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.fetch_guild_roles("guild123")

        assert exc_info.value.status == 403
        assert exc_info.value.message == "Missing Permissions"

    @pytest.mark.asyncio
    async def test_fetch_guild_roles_network_error(self, discord_client, mock_redis):
        """fetch_guild_roles() raises DiscordAPIError(500) on network failure."""
        mock_session = MagicMock()
        mock_session.closed = False

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Timeout"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.request = MagicMock(return_value=mock_cm)
        discord_client._session = mock_session

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            with pytest.raises(DiscordAPIError) as exc_info:
                await discord_client.fetch_guild_roles("guild123")

        assert exc_info.value.status == 500
        assert "network error" in exc_info.value.message.lower()


class TestHelperFunctions:
    """Test module-level helper functions."""

    def test_get_global_client_creates_instance(self):
        """_get_global_client() imports and calls get_discord_client when no instance exists."""
        saved = discord_client_module._global_client_instance
        discord_client_module._global_client_instance = None
        try:
            mock_client = MagicMock()
            mock_discord_dep = MagicMock()
            mock_discord_dep.get_discord_client.return_value = mock_client

            with patch.dict(sys.modules, {"services.api.dependencies.discord": mock_discord_dep}):
                result = _get_global_client()

            assert result is mock_client
            assert discord_client_module._global_client_instance is mock_client
        finally:
            discord_client_module._global_client_instance = saved

    @pytest.mark.asyncio
    async def test_fetch_channel_name_safe_success(self):
        """fetch_channel_name_safe() returns channel name on success."""
        mock_client = MagicMock()
        mock_client.fetch_channel = AsyncMock(return_value={"name": "general", "id": "123"})

        result = await fetch_channel_name_safe("123", client=mock_client)

        assert result == "general"

    @pytest.mark.asyncio
    async def test_fetch_channel_name_safe_error(self):
        """fetch_channel_name_safe() returns 'Unknown Channel' on DiscordAPIError."""
        mock_client = MagicMock()
        mock_client.fetch_channel = AsyncMock(side_effect=DiscordAPIError(404, "Unknown Channel"))

        result = await fetch_channel_name_safe("nonexistent", client=mock_client)

        assert result == "Unknown Channel"

    @pytest.mark.asyncio
    async def test_fetch_channel_name_safe_uses_global_client_when_none(self):
        """fetch_channel_name_safe() calls _get_global_client() when no client is provided."""
        mock_client = MagicMock()
        mock_client.fetch_channel = AsyncMock(return_value={"name": "announcements"})

        with patch("shared.discord.client._get_global_client", return_value=mock_client):
            result = await fetch_channel_name_safe("channel_id")

        assert result == "announcements"

    @pytest.mark.asyncio
    async def test_fetch_user_display_name_safe_success(self):
        """fetch_user_display_name_safe() returns formatted username on success."""
        mock_client = MagicMock()
        mock_client.fetch_user = AsyncMock(return_value={"username": "testuser", "id": "456"})

        result = await fetch_user_display_name_safe("456", client=mock_client)

        assert result == "@testuser"

    @pytest.mark.asyncio
    async def test_fetch_user_display_name_safe_error(self):
        """fetch_user_display_name_safe() returns '@{id}' fallback on DiscordAPIError."""
        mock_client = MagicMock()
        mock_client.fetch_user = AsyncMock(side_effect=DiscordAPIError(404, "Unknown User"))

        result = await fetch_user_display_name_safe("user_id_123", client=mock_client)

        assert result == "@user_id_123"

    @pytest.mark.asyncio
    async def test_fetch_user_display_name_safe_uses_global_client_when_none(self):
        """fetch_user_display_name_safe() calls _get_global_client() when no client is provided."""
        mock_client = MagicMock()
        mock_client.fetch_user = AsyncMock(return_value={"username": "globaluser"})

        with patch("shared.discord.client._get_global_client", return_value=mock_client):
            result = await fetch_user_display_name_safe("user_id")

        assert result == "@globaluser"

    @pytest.mark.asyncio
    async def test_fetch_guild_name_safe_success(self):
        """fetch_guild_name_safe() returns guild name on success."""
        mock_client = MagicMock()
        mock_client.fetch_guild = AsyncMock(return_value={"name": "My Server", "id": "789"})

        result = await fetch_guild_name_safe("789", client=mock_client)

        assert result == "My Server"

    @pytest.mark.asyncio
    async def test_fetch_guild_name_safe_error(self):
        """fetch_guild_name_safe() returns guild_id fallback on DiscordAPIError."""
        mock_client = MagicMock()
        mock_client.fetch_guild = AsyncMock(side_effect=DiscordAPIError(404, "Unknown Guild"))

        result = await fetch_guild_name_safe("guild_789", client=mock_client)

        assert result == "guild_789"

    @pytest.mark.asyncio
    async def test_fetch_guild_name_safe_uses_global_client_when_none(self):
        """fetch_guild_name_safe() calls _get_global_client() when no client is provided."""
        mock_client = MagicMock()
        mock_client.fetch_guild = AsyncMock(return_value={"name": "Global Server"})

        with patch("shared.discord.client._get_global_client", return_value=mock_client):
            result = await fetch_guild_name_safe("guild_id")

        assert result == "Global Server"

    @pytest.mark.asyncio
    async def test_get_guild_channels_safe_success(self):
        """get_guild_channels_safe() returns channel list on success."""
        channels = [{"id": "111", "name": "general", "type": 0}]
        mock_client = MagicMock()
        mock_client.get_guild_channels = AsyncMock(return_value=channels)

        result = await get_guild_channels_safe("guild123", client=mock_client)

        assert result == channels

    @pytest.mark.asyncio
    async def test_get_guild_channels_safe_error(self):
        """get_guild_channels_safe() returns empty list on DiscordAPIError."""
        mock_client = MagicMock()
        mock_client.get_guild_channels = AsyncMock(
            side_effect=DiscordAPIError(500, "Internal Error")
        )

        result = await get_guild_channels_safe("guild123", client=mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_guild_channels_safe_uses_global_client_when_none(self):
        """get_guild_channels_safe() calls _get_global_client() when no client provided."""
        channels = [{"id": "222", "name": "announcements", "type": 0}]
        mock_client = MagicMock()
        mock_client.get_guild_channels = AsyncMock(return_value=channels)

        with patch("shared.discord.client._get_global_client", return_value=mock_client):
            result = await get_guild_channels_safe("guild_id")

        assert result == channels


class TestGetOrFetch:
    """Tests for DiscordAPIClient._get_or_fetch cache helper."""

    @pytest.fixture
    def client(self):
        return DiscordAPIClient(
            client_id="cid",
            client_secret="csecret",
            bot_token="tok.en.val",
        )

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self, client, mock_redis):
        """On a cache hit, _get_or_fetch returns the cached value without calling fetch_fn."""
        cached_data = {"id": "guild1", "name": "My Guild"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        fetch_fn = AsyncMock()

        with patch(
            "shared.discord.client.cache_client.get_redis_client",
            new=AsyncMock(return_value=mock_redis),
        ):
            with patch("shared.discord.client._cache_hit_counter") as hit_ctr:
                result = await client._get_or_fetch(
                    cache_key="key:1",
                    cache_ttl=300,
                    fetch_fn=fetch_fn,
                    operation=CacheOperation.FETCH_GUILD,
                )

        assert result == cached_data
        fetch_fn.assert_not_called()
        hit_ctr.add.assert_called_once_with(1, {"operation": CacheOperation.FETCH_GUILD})

    @pytest.mark.asyncio
    async def test_cache_miss_calls_fetch_fn(self, client, mock_redis):
        """On a cache miss, _get_or_fetch calls fetch_fn and returns its result."""
        fetched_data = {"id": "ch1", "name": "general"}
        mock_redis.get = AsyncMock(return_value=None)
        fetch_fn = AsyncMock(return_value=fetched_data)

        with (
            patch("shared.discord.client._cache_miss_counter") as miss_ctr,
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
        ):
            result = await client._get_or_fetch(
                cache_key="key:2",
                cache_ttl=60,
                fetch_fn=fetch_fn,
                operation=CacheOperation.FETCH_CHANNEL,
            )

        assert result == fetched_data
        miss_ctr.add.assert_called_once_with(1, {"operation": CacheOperation.FETCH_CHANNEL})

    @pytest.mark.asyncio
    async def test_cache_miss_writes_result_to_redis(self, client, mock_redis):
        """After a miss, _get_or_fetch writes the fetched result back to Redis."""
        fetched_data = {"id": "role1", "name": "Admin"}
        mock_redis.get = AsyncMock(return_value=None)
        fetch_fn = AsyncMock(return_value=fetched_data)

        with patch(
            "shared.discord.client.cache_client.get_redis_client",
            new=AsyncMock(return_value=mock_redis),
        ):
            await client._get_or_fetch(
                cache_key="key:3",
                cache_ttl=120,
                fetch_fn=fetch_fn,
                operation=CacheOperation.FETCH_GUILD_ROLES,
            )

        mock_redis.set.assert_called_once_with("key:3", json.dumps(fetched_data), ttl=120)

    @pytest.mark.asyncio
    async def test_duration_recorded_on_hit(self, client, mock_redis):
        """_get_or_fetch records discord.cache.duration histogram on a cache hit."""
        cached_data = {"id": "u1"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch("shared.discord.client._cache_duration_histogram") as hist,
        ):
            await client._get_or_fetch(
                cache_key="key:4",
                cache_ttl=300,
                fetch_fn=AsyncMock(),
                operation=CacheOperation.FETCH_USER,
            )

        assert hist.record.called
        _, kwargs = hist.record.call_args
        assert kwargs.get("attributes", {}).get("result") == "hit"

    @pytest.mark.asyncio
    async def test_duration_recorded_on_miss(self, client, mock_redis):
        """_get_or_fetch records discord.cache.duration histogram on a cache miss."""
        mock_redis.get = AsyncMock(return_value=None)
        fetch_fn = AsyncMock(return_value={"id": "u2"})

        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch("shared.discord.client._cache_duration_histogram") as hist,
        ):
            await client._get_or_fetch(
                cache_key="key:5",
                cache_ttl=300,
                fetch_fn=fetch_fn,
                operation=CacheOperation.FETCH_USER,
            )

        assert hist.record.called
        _, kwargs = hist.record.call_args
        assert kwargs.get("attributes", {}).get("result") == "miss"


class TestReadThroughDelegatesToGetOrFetch:
    """Phase 3: each read-through method must delegate to _get_or_fetch."""

    CACHE_HIT = json.dumps({"id": "1", "name": "test"})

    @pytest.fixture
    def client(self):
        return DiscordAPIClient(
            client_id="cid",
            client_secret="csecret",
            bot_token="tok.en.val",
        )

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=self.CACHE_HIT)
        return redis

    @pytest.mark.asyncio
    async def test_get_application_info_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value={"id": "app1"})
            ) as mock_gof,
        ):
            await client.get_application_info()
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_guild_channels_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value=[{"id": "ch1"}])
            ) as mock_gof,
        ):
            await client.get_guild_channels("111")
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_channel_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value={"id": "ch1"})
            ) as mock_gof,
        ):
            await client.fetch_channel("123")
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_guild_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value={"id": "g1"})
            ) as mock_gof,
        ):
            await client.fetch_guild("111")
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_guild_roles_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value=[{"id": "r1"}])
            ) as mock_gof,
        ):
            await client.fetch_guild_roles("111")
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_user_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value={"id": "u1"})
            ) as mock_gof,
        ):
            await client.fetch_user("456")
        mock_gof.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_guild_member_delegates_to_get_or_fetch(self, client, mock_redis):
        with (
            patch(
                "shared.discord.client.cache_client.get_redis_client",
                new=AsyncMock(return_value=mock_redis),
            ),
            patch.object(
                client, "_get_or_fetch", new=AsyncMock(return_value={"user": {"id": "u1"}})
            ) as mock_gof,
        ):
            await client.get_guild_member("111", "456")
        mock_gof.assert_called_once()


class TestGetCurrentUserGuildMember:
    """Tests for get_current_user_guild_member using Bearer token."""

    @pytest.fixture
    def client(self):
        return DiscordAPIClient(
            client_id="cid",
            client_secret="csecret",
            bot_token="bot.token.abc",
        )

    @pytest.mark.asyncio
    async def test_uses_bearer_token_not_bot_token(self, client):
        """get_current_user_guild_member must use Bearer token, not the bot token."""
        captured_headers: dict = {}

        async def _capture_request(method, url, operation_name, headers, **kwargs):
            captured_headers.update(headers)
            return {"user": {"id": "u1"}, "nick": "Nick"}

        with patch.object(client, "_make_api_request", side_effect=_capture_request):
            result = await client.get_current_user_guild_member("111222", "user-oauth-token")

        assert result == {"user": {"id": "u1"}, "nick": "Nick"}
        assert captured_headers.get("Authorization") == "Bearer user-oauth-token"
        assert "Bot" not in captured_headers.get("Authorization", "")
