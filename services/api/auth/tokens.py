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


"""Token management for storing and retrieving OAuth2 tokens.

Uses Redis for session storage with encrypted token data.
"""

import base64
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet

from services.api import config
from shared.cache import client as cache_client
from shared.cache import ttl as cache_ttl
from shared.cache.operations import CacheOperation, cache_get
from shared.utils.security_constants import ENCRYPTION_KEY_LENGTH

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from JWT secret.

    Returns:
        Fernet-compatible encryption key
    """
    api_config = config.get_api_config()
    key = api_config.jwt_secret.encode()
    if len(key) < ENCRYPTION_KEY_LENGTH:
        key = key.ljust(ENCRYPTION_KEY_LENGTH, b"0")
    key = key[:ENCRYPTION_KEY_LENGTH]
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt token for secure storage.

    Args:
        token: Plain text token

    Returns:
        Encrypted token string
    """
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt token from storage.

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Decrypted plain text token
    """
    fernet = Fernet(get_encryption_key())
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()


async def store_user_tokens(
    user_id: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    can_be_maintainer: bool = False,
) -> str:
    """
    Store user OAuth2 tokens in Redis session.

    Args:
        user_id: Discord user ID
        access_token: OAuth2 access token
        refresh_token: OAuth2 refresh token
        expires_in: Seconds until access token expires

    Returns:
        Session token (UUID4) for retrieving tokens later
    """
    redis = await cache_client.get_redis_client()

    session_token = str(uuid.uuid4())
    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token)

    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=expires_in)

    session_data: dict[str, str | bool] = {
        "user_id": user_id,
        "access_token": encrypted_access,
        "refresh_token": encrypted_refresh,
        "expires_at": expiry.isoformat(),
        "can_be_maintainer": can_be_maintainer,
        "is_maintainer": False,
    }

    session_key = f"session:{session_token}"
    await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)

    logger.info("Stored tokens for user %s", user_id)
    return session_token


async def get_user_tokens(session_token: str) -> dict[str, Any] | None:
    """
    Retrieve user tokens from Redis session.

    Args:
        session_token: Session token (UUID4)

    Returns:
        Dictionary with user_id, access_token, refresh_token, expires_at or None
    """
    session_key = f"session:{session_token}"
    session_data_raw = await cache_get(session_key, CacheOperation.SESSION_LOOKUP)

    if session_data_raw is None:
        logger.warning("No session found for token %s", session_token)
        return None

    if not isinstance(session_data_raw, dict):
        logger.warning("Invalid session data format for token %s", session_token)
        return None

    session_data: dict[str, Any] = session_data_raw

    decrypted_access = decrypt_token(session_data.get("access_token", ""))
    decrypted_refresh = decrypt_token(session_data.get("refresh_token", ""))

    return {
        "user_id": str(session_data.get("user_id", "")),
        "access_token": decrypted_access,
        "refresh_token": decrypted_refresh,
        "expires_at": datetime.fromisoformat(str(session_data.get("expires_at", ""))),
        "can_be_maintainer": bool(session_data.get("can_be_maintainer")),
        "is_maintainer": bool(session_data.get("is_maintainer")),
    }


async def refresh_user_tokens(
    session_token: str, new_access_token: str, new_expires_in: int
) -> None:
    """
    Update user's access token after refresh.

    Args:
        session_token: Session token (UUID4)
        new_access_token: New access token from refresh
        new_expires_in: New expiration time in seconds
    """
    session_key = f"session:{session_token}"
    session_data_raw = await cache_get(session_key, CacheOperation.SESSION_REFRESH)

    if session_data_raw is None:
        logger.warning("No session found for token %s", session_token)
        return

    if not isinstance(session_data_raw, dict):
        logger.warning("Invalid session data format for token %s", session_token)
        return

    session_data: dict[str, Any] = session_data_raw

    redis = await cache_client.get_redis_client()

    encrypted_access = encrypt_token(new_access_token)
    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=new_expires_in)

    session_data["access_token"] = encrypted_access
    session_data["expires_at"] = expiry.isoformat()

    await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)
    logger.info("Refreshed tokens for session %s", session_token)


async def delete_user_tokens(session_token: str) -> None:
    """
    Delete user tokens from Redis session.

    Args:
        session_token: Session token (UUID4)
    """
    redis = await cache_client.get_redis_client()

    session_key = f"session:{session_token}"
    await redis.delete(session_key)

    logger.info("Deleted session %s", session_token)


async def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if access token is expired or expiring soon.

    Args:
        expires_at: Token expiration datetime

    Returns:
        True if token is expired or expires within 5 minutes
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    buffer = timedelta(minutes=5)
    return now >= (expires_at - buffer)


def get_guild_token(session_data: dict) -> str:
    """Return the bot token for maintainers or the OAuth token otherwise."""
    if session_data.get("is_maintainer"):
        return config.get_api_config().discord_bot_token
    return session_data["access_token"]
