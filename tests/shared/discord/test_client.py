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


"""Comprehensive unit tests for shared Discord API client."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from shared.discord.client import DiscordAPIClient, DiscordAPIError


@pytest.fixture
def discord_client():
    """Create Discord API client for testing."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="test_bot_token",
    )


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
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


class TestOAuth2Methods:
    """Test OAuth2 authentication methods."""

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, discord_client):
        """Test successful authorization code exchange."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(
            return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 604800,
                "token_type": "Bearer",
            }
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.exchange_code(
            code="auth_code_123", redirect_uri="http://localhost:3000/callback"
        )

        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_in"] == 604800
        assert result["token_type"] == "Bearer"

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "client_id" in call_args.kwargs["data"]
        assert "client_secret" in call_args.kwargs["data"]
        assert call_args.kwargs["data"]["code"] == "auth_code_123"

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_code(self, discord_client):
        """Test code exchange with invalid authorization code."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(
            return_value={"error_description": "Invalid authorization code"}
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.exchange_code(
                code="invalid_code", redirect_uri="http://localhost:3000/callback"
            )

        assert exc_info.value.status == 400
        assert "Invalid authorization code" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_exchange_code_network_error(self, discord_client):
        """Test network error during code exchange."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        mock_session.post = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.exchange_code(
                code="test_code", redirect_uri="http://localhost:3000/callback"
            )

        assert exc_info.value.status == 500
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, discord_client):
        """Test successful token refresh."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(
            return_value={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 604800,
            }
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.refresh_token(refresh_token="old_refresh_token")

        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_in"] == 604800

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self, discord_client):
        """Test token refresh with invalid refresh token."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value={"error_description": "Invalid refresh token"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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
    async def test_get_user_guilds_without_cache(self, discord_client):
        """Test fetching user guilds without caching (no user_id provided)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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

        result = await discord_client.get_user_guilds(access_token="test_token")

        assert len(result) == 2
        assert result[0]["name"] == "Test Guild 1"
        assert result[1]["name"] == "Test Guild 2"

    @pytest.mark.asyncio
    async def test_get_user_guilds_with_cache_miss(self, discord_client, mock_redis):
        """Test fetching user guilds with cache miss."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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

            result = await discord_client.get_user_guilds(
                access_token="test_token", user_id="user123"
            )

            assert len(result) == 2
            assert result[0]["name"] == "Test Guild 1"
            # Double-checked locking means get is called twice (before and after acquiring lock)
            assert mock_redis.get.call_count == 2
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_guilds_with_cache_hit(self, discord_client, mock_redis):
        """Test fetching user guilds with cache hit."""
        cached_guilds = [{"id": "guild1", "name": "Cached Guild"}]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_guilds))

        with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            result = await discord_client.get_user_guilds(
                access_token="test_token", user_id="user123"
            )

            assert len(result) == 1
            assert result[0]["name"] == "Cached Guild"
            mock_redis.get.assert_called_once_with("user_guilds:user123")
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_bot_guilds_success(self, discord_client):
        """Test fetching bot guilds."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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

        result = await discord_client.get_bot_guilds()

        assert len(result) == 2
        assert result[0]["name"] == "Bot Guild 1"

    @pytest.mark.asyncio
    async def test_get_guild_channels_success(self, discord_client):
        """Test fetching guild channels."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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

        result = await discord_client.get_guild_channels(guild_id="guild123")

        assert len(result) == 2
        assert result[0]["name"] == "general"


class TestCachedResourceMethods:
    """Test methods that use Redis caching."""

    @pytest.mark.asyncio
    async def test_fetch_channel_cache_miss(self, discord_client, mock_redis):
        """Test fetching channel with cache miss."""
        channel_data = {"id": "channel123", "name": "general", "type": 0}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value=guild_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value=roles_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
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
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value=user_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
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
    async def test_get_guild_member_success(self, discord_client):
        """Test successful guild member fetch."""
        member_data = {
            "user": {"id": "123456789", "username": "testuser"},
            "roles": ["role1", "role2"],
            "nick": "TestNick",
        }
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value=member_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_guild_member(guild_id="guild123", user_id="123456789")

        assert result["user"]["id"] == "123456789"
        assert result["nick"] == "TestNick"
        assert len(result["roles"]) == 2

    @pytest.mark.asyncio
    async def test_get_guild_member_not_found(self, discord_client):
        """Test guild member fetch when user not in guild."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value={"message": "Unknown Member"})

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        with pytest.raises(DiscordAPIError) as exc_info:
            await discord_client.get_guild_member(guild_id="guild123", user_id="nonexistent")

        assert exc_info.value.status == 404

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


class TestConcurrencyAndLocking:
    """Test concurrency control and locking mechanisms."""

    @pytest.mark.asyncio
    async def test_user_guilds_double_checked_locking(self, discord_client, mock_redis):
        """Test double-checked locking prevents duplicate API calls."""
        guilds_data = [{"id": "guild1", "name": "Test Guild"}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")
        mock_response.json = AsyncMock(return_value=guilds_data)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
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
                return await discord_client.get_user_guilds(
                    access_token="test_token", user_id="user123"
                )

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
            discord_client, "_fetch_user_guilds_uncached", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = [{"id": "guild1", "name": "Test Guild"}]

            with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
                mock_redis = AsyncMock()
                mock_redis.get = AsyncMock(return_value=None)
                mock_redis.set = AsyncMock()
                mock_get_redis.return_value = mock_redis

                await discord_client.get_user_guilds(access_token="token1", user_id="user1")
                await discord_client.get_user_guilds(access_token="token2", user_id="user2")

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
            call_args = mock_logger.info.call_args[0][0]
            assert "GET" in call_args
            assert "test_op" in call_args

    def test_log_response(self, discord_client):
        """Test response logging."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(
            side_effect=lambda key, default="N/A": {
                "x-ratelimit-remaining": "100",
                "x-ratelimit-limit": "5000",
                "x-ratelimit-reset-after": "60",
            }.get(key, default)
        )

        with patch("shared.discord.client.logger") as mock_logger:
            discord_client._log_response(mock_response, "extra info")

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "200" in call_args
            assert "100" in call_args
            assert "extra info" in call_args

    def test_log_response_without_rate_limit_headers(self, discord_client):
        """Test response logging when rate limit headers are missing."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="N/A")

        with patch("shared.discord.client.logger") as mock_logger:
            discord_client._log_response(mock_response)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "N/A" in call_args
