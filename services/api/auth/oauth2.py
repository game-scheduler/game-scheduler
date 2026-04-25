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
OAuth2 authorization flow implementation for Discord.

Handles authorization URL generation, state management, and callback processing.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from services.api import config
from services.api.dependencies.discord import get_discord_client
from shared.cache import client as cache_client
from shared.cache.operations import CacheOperation, cache_get

logger = logging.getLogger(__name__)

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
    await redis.set_json(state_key, redirect_uri, ttl=600)

    params = {
        "client_id": api_config.discord_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{api_config.discord_oauth_url}?{query_string}"

    logger.info("Generated OAuth2 authorization URL with state: %s", state)
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

    redirect_uri = await cache_get(state_key, CacheOperation.OAUTH_STATE)
    if redirect_uri is None:
        logger.warning("Invalid or expired OAuth2 state: %s", state)
        msg = "Invalid or expired state token"
        raise OAuth2StateError(msg)

    await redis.delete(state_key)
    logger.info("Validated OAuth2 state: %s", state)
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
    discord = get_discord_client()
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
    discord = get_discord_client()
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
    discord = get_discord_client()
    user_data = await discord.get_user_info(access_token)

    logger.info("Fetched user info for Discord ID: %s", user_data.get("id"))
    return user_data


def calculate_token_expiry(expires_in: int) -> datetime:
    """
    Calculate absolute expiry datetime from relative expires_in seconds.

    Args:
        expires_in: Seconds until token expires (from Discord API)

    Returns:
        UTC datetime when token will expire
    """
    return datetime.now(UTC) + timedelta(seconds=expires_in)


async def is_app_maintainer(discord_id: str) -> bool:
    """Check whether a Discord user is an owner or team member of this application."""
    discord = get_discord_client()
    app_info = await discord.get_application_info()
    owner_id = app_info.get("owner", {}).get("id")
    if owner_id == discord_id:
        return True
    team = app_info.get("team")
    if team:
        return any(m.get("user", {}).get("id") == discord_id for m in team.get("members", []))
    return False
