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


"""Unit tests for OAuth2 flow implementation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import oauth2
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
            mock_redis_instance.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_state_success(self):
        """Test successful state validation."""
        with (
            patch("services.api.auth.oauth2.cache_client.get_redis_client") as mock_redis,
            patch(
                "services.api.auth.oauth2.cache_get",
                new_callable=AsyncMock,
                return_value="http://localhost:3000/callback",
            ),
        ):
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            redirect_uri = await validate_state("test_state")

            assert redirect_uri == "http://localhost:3000/callback"
            mock_redis_instance.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_state_invalid(self):
        """Test state validation with invalid token."""
        with (
            patch("services.api.auth.oauth2.cache_client.get_redis_client"),
            patch(
                "services.api.auth.oauth2.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            with pytest.raises(OAuth2StateError):
                await validate_state("invalid_state")

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self):
        """Test authorization code exchange."""
        with patch("services.api.auth.oauth2.get_discord_client") as mock_client:
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
        with patch("services.api.auth.oauth2.get_discord_client") as mock_client:
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
        with patch("services.api.auth.oauth2.get_discord_client") as mock_client:
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
        with patch("services.api.auth.oauth2.get_discord_client") as mock_client:
            mock_discord = AsyncMock()
            mock_client.return_value = mock_discord
            mock_discord.get_guilds.return_value = [
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


# ---------------------------------------------------------------------------
# is_app_maintainer tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_true_for_owner():
    """Test that an application owner is identified as a maintainer."""
    app_info = {"owner": {"id": "111"}, "team": None}
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("111")

    assert result is True


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_true_for_team_member():
    """Test that a team member is identified as a maintainer."""
    app_info = {
        "owner": {"id": "999"},
        "team": {
            "members": [
                {"user": {"id": "222"}},
                {"user": {"id": "333"}},
            ]
        },
    }
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("222")

    assert result is True


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_false_for_non_member():
    """Test that a non-owner, non-team-member returns False."""
    app_info = {
        "owner": {"id": "999"},
        "team": {
            "members": [
                {"user": {"id": "222"}},
            ]
        },
    }
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("444")

    assert result is False


@pytest.mark.asyncio
async def test_is_app_maintainer_falls_back_to_owner_when_no_team():
    """Test that when team is absent, only the owner is a maintainer."""
    app_info = {"owner": {"id": "111"}}
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        owner_result = await oauth2.is_app_maintainer("111")
        other_result = await oauth2.is_app_maintainer("999")

    assert owner_result is True
    assert other_result is False
