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
OAuth2 authorization flow implementation for Discord.

Handles authorization URL generation, state management, and callback processing.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from services.api import config
from services.api.auth import discord_client
from shared.cache import client as cache_client

logger = logging.getLogger(__name__)

DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
OAUTH_SCOPES = ["identify", "guilds", "guilds.members.read"]


class OAuth2StateError(Exception):
    """Exception raised for invalid OAuth2 state validation."""

    pass


async def generate_authorization_url(redirect_uri: str) -> tuple[str, str]:
    """
    Generate Discord OAuth2 authorization URL with state token.

    Args:
        redirect_uri: Callback URL for OAuth2 redirect

    Returns:
        Tuple of (authorization_url, state_token)
    """
    api_config = config.get_api_config()
    state = secrets.token_urlsafe(32)

    redis = await cache_client.get_redis_client()
    state_key = f"oauth_state:{state}"
    await redis.set(state_key, redirect_uri, ttl=600)

    params = {
        "client_id": api_config.discord_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{DISCORD_OAUTH_URL}?{query_string}"

    logger.info(f"Generated OAuth2 authorization URL with state: {state}")
    return auth_url, state


async def validate_state(state: str) -> str:
    """
    Validate OAuth2 state token and retrieve redirect URI.

    Args:
        state: State token from OAuth2 callback

    Returns:
        Original redirect URI that was stored with state

    Raises:
        OAuth2StateError: If state is invalid or expired
    """
    redis = await cache_client.get_redis_client()
    state_key = f"oauth_state:{state}"

    redirect_uri = await redis.get(state_key)
    if redirect_uri is None:
        logger.warning(f"Invalid or expired OAuth2 state: {state}")
        raise OAuth2StateError("Invalid or expired state token")

    await redis.delete(state_key)
    logger.info(f"Validated OAuth2 state: {state}")
    return redirect_uri


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from Discord callback
        redirect_uri: Redirect URI used in authorization request

    Returns:
        Token data with access_token, refresh_token, expires_in, token_type

    Raises:
        DiscordAPIError: If token exchange fails
    """
    discord = discord_client.get_discord_client()
    token_data = await discord.exchange_code(code, redirect_uri)

    logger.info("Successfully exchanged authorization code for tokens")
    return token_data


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token from previous token exchange

    Returns:
        New token data with access_token, refresh_token, expires_in

    Raises:
        DiscordAPIError: If token refresh fails
    """
    discord = discord_client.get_discord_client()
    token_data = await discord.refresh_token(refresh_token)

    logger.info("Successfully refreshed access token")
    return token_data


async def get_user_from_token(access_token: str) -> dict[str, Any]:
    """
    Fetch user information using access token.

    Args:
        access_token: User's OAuth2 access token

    Returns:
        User data with id, username, avatar, discriminator, etc.

    Raises:
        DiscordAPIError: If fetching user fails
    """
    discord = discord_client.get_discord_client()
    user_data = await discord.get_user_info(access_token)

    logger.info(f"Fetched user info for Discord ID: {user_data.get('id')}")
    return user_data


async def get_user_guilds(access_token: str, user_id: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch guilds the user is a member of with automatic caching.

    Args:
        access_token: User's OAuth2 access token
        user_id: Discord user ID for cache key (optional, enables caching)

    Returns:
        List of guild data with id, name, icon, permissions, etc.

    Raises:
        DiscordAPIError: If fetching guilds fails
    """
    discord = discord_client.get_discord_client()
    guilds_data = await discord.get_user_guilds(access_token, user_id)

    logger.info(f"Fetched {len(guilds_data)} guilds for user")
    return guilds_data


def calculate_token_expiry(expires_in: int) -> datetime:
    """
    Calculate absolute expiry datetime from relative expires_in seconds.

    Args:
        expires_in: Seconds until token expires (from Discord API)

    Returns:
        UTC datetime when token will expire
    """
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=expires_in)
