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


"""Unit tests for Discord API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from services.api.auth.discord_client import (
    DiscordAPIClient,
    DiscordAPIError,
    get_discord_client,
)


@pytest.fixture
def discord_client():
    """Create Discord API client for testing."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="test_bot_token",
    )


@pytest.fixture
def mock_session():
    """Create mock aiohttp session."""
    session = AsyncMock()
    return session


class TestDiscordAPIClient:
    """Test Discord API client methods."""

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, discord_client):
        """Test successful authorization code exchange."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
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

        result = await discord_client.exchange_code(
            code="test_code", redirect_uri="http://localhost:3000/callback"
        )

        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_in"] == 604800

    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, discord_client):
        """Test authorization code exchange failure."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error_description": "Invalid code"})

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
        assert "Invalid code" in exc_info.value.message

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

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, discord_client):
        """Test successful user info fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "123456789",
                "username": "testuser",
                "avatar": "avatar_hash",
            }
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_user_info(access_token="test_token")

        assert result["id"] == "123456789"
        assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_guilds_success(self, discord_client):
        """Test successful guilds fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "guild1", "name": "Test Guild 1"},
                {"id": "guild2", "name": "Test Guild 2"},
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

    @pytest.mark.asyncio
    async def test_get_guild_member_success(self, discord_client):
        """Test successful guild member fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "user": {"id": "123456789"},
                "roles": ["role1", "role2"],
                "nick": "TestNick",
            }
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context_manager)
        discord_client._session = mock_session

        result = await discord_client.get_guild_member(guild_id="guild123", user_id="123456789")

        assert result["user"]["id"] == "123456789"
        assert len(result["roles"]) == 2

    @pytest.mark.asyncio
    async def test_close_session(self, discord_client):
        """Test session cleanup."""
        mock_session = AsyncMock()
        mock_session.closed = False
        discord_client._session = mock_session

        await discord_client.close()

        mock_session.close.assert_called_once()


def test_get_discord_client_singleton():
    """Test Discord client singleton pattern."""
    with patch("services.api.auth.discord_client.config.get_api_config") as mock_config:
        mock_config.return_value = MagicMock(
            discord_client_id="test_id",
            discord_client_secret="test_secret",
            discord_bot_token="test_token",
        )

        client1 = get_discord_client()
        client2 = get_discord_client()

        assert client1 is client2
