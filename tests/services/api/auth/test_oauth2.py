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


"""Unit tests for OAuth2 flow implementation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth.oauth2 import (
    OAuth2StateError,
    calculate_token_expiry,
    exchange_code_for_tokens,
    generate_authorization_url,
    get_user_from_token,
    get_user_guilds,
    refresh_access_token,
    validate_state,
)


class TestOAuth2Flow:
    """Test OAuth2 authorization flow functions."""

    @pytest.mark.asyncio
    async def test_generate_authorization_url(self):
        """Test authorization URL generation with state token."""
        with patch("services.api.auth.oauth2.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            auth_url, state = await generate_authorization_url("http://localhost:3000/callback")

            assert "discord.com/api/oauth2/authorize" in auth_url
            assert "client_id=" in auth_url
            assert "scope=identify" in auth_url
            assert f"state={state}" in auth_url
            mock_redis_instance.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_state_success(self):
        """Test successful state validation."""
        with patch("services.api.auth.oauth2.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = "http://localhost:3000/callback"

            redirect_uri = await validate_state("test_state")

            assert redirect_uri == "http://localhost:3000/callback"
            mock_redis_instance.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_state_invalid(self):
        """Test state validation with invalid token."""
        with patch("services.api.auth.oauth2.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = None

            with pytest.raises(OAuth2StateError):
                await validate_state("invalid_state")

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self):
        """Test authorization code exchange."""
        with patch("services.api.auth.oauth2.discord_client.get_discord_client") as mock_client:
            mock_discord = AsyncMock()
            mock_client.return_value = mock_discord
            mock_discord.exchange_code.return_value = {
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 604800,
            }

            result = await exchange_code_for_tokens("test_code", "http://localhost:3000/callback")

            assert result["access_token"] == "test_token"
            assert result["refresh_token"] == "test_refresh"

    @pytest.mark.asyncio
    async def test_refresh_access_token(self):
        """Test access token refresh."""
        with patch("services.api.auth.oauth2.discord_client.get_discord_client") as mock_client:
            mock_discord = AsyncMock()
            mock_client.return_value = mock_discord
            mock_discord.refresh_token.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_in": 604800,
            }

            result = await refresh_access_token("old_refresh_token")

            assert result["access_token"] == "new_token"

    @pytest.mark.asyncio
    async def test_get_user_from_token(self):
        """Test user info fetching."""
        with patch("services.api.auth.oauth2.discord_client.get_discord_client") as mock_client:
            mock_discord = AsyncMock()
            mock_client.return_value = mock_discord
            mock_discord.get_user_info.return_value = {
                "id": "123456789",
                "username": "testuser",
            }

            result = await get_user_from_token("test_token")

            assert result["id"] == "123456789"
            assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_guilds(self):
        """Test user guilds fetching."""
        with patch("services.api.auth.oauth2.discord_client.get_discord_client") as mock_client:
            mock_discord = AsyncMock()
            mock_client.return_value = mock_discord
            mock_discord.get_user_guilds.return_value = [
                {"id": "guild1", "name": "Test Guild 1"},
                {"id": "guild2", "name": "Test Guild 2"},
            ]

            result = await get_user_guilds("test_token")

            assert len(result) == 2
            assert result[0]["name"] == "Test Guild 1"

    def test_calculate_token_expiry(self):
        """Test token expiry calculation."""
        now = datetime.now(UTC)
        expires_in = 3600

        expiry = calculate_token_expiry(expires_in)

        assert expiry > now
        assert expiry <= now + timedelta(seconds=3610)
