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

import logging
from typing import Any

import aiohttp

from services.api import config

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

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

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

        try:
            async with session.post(
                DISCORD_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                response_data = await response.json()

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

        try:
            async with session.post(
                DISCORD_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                response_data = await response.json()

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

        try:
            async with session.get(
                DISCORD_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                response_data = await response.json()

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching user info: {e}")
            raise DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def get_user_guilds(self, access_token: str) -> list[dict[str, Any]]:
        """
        Fetch guilds the user is a member of.

        Args:
            access_token: User's OAuth2 access token

        Returns:
            List of guild objects with id, name, icon, permissions, etc.

        Raises:
            DiscordAPIError: If fetching guilds fails
        """
        session = await self._get_session()

        try:
            async with session.get(
                DISCORD_GUILDS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                response_data = await response.json()

                if response.status != 200:
                    error_msg = response_data.get("message", "Unknown error")
                    raise DiscordAPIError(response.status, error_msg, dict(response.headers))

                return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching guilds: {e}")
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

        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bot {self.bot_token}"},
            ) as response:
                response_data = await response.json()

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
        return members


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
