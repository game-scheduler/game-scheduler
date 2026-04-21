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
Shared authentication helpers for integration and E2E tests.

Provides utilities for creating authenticated HTTP clients by setting up
session tokens in Redis with encrypted Discord credentials.
"""

import uuid
from datetime import UTC, datetime, timedelta

from services.api.auth.tokens import encrypt_token
from shared.cache.client import RedisClient


async def create_test_session(
    discord_token: str,
    bot_discord_id: str,
    ttl_seconds: int = 604800,
    can_be_maintainer: bool = False,
    is_maintainer: bool = False,
    username: str = "",
) -> tuple[str, dict]:
    """
    Create test session in Redis with encrypted tokens.

    Args:
        discord_token: Discord bot token to encrypt and store
        bot_discord_id: Discord ID of the bot user
        ttl_seconds: Session TTL in seconds (default: 7 days)
        can_be_maintainer: Whether user is eligible for maintainer mode
        is_maintainer: Whether maintainer mode is currently active
        username: Discord username to store in session

    Returns:
        Tuple of (session_token, session_data) where session_token is the
        cookie value and session_data is the stored session information

    Example:
        session_token, session_data = await create_test_session(
            discord_token="bot_token_here",
            bot_discord_id="123456789",
        )
        client.cookies.set("session_token", session_token)
    """
    redis_client = RedisClient()
    await redis_client.connect()

    session_token = str(uuid.uuid4())
    encrypted_access = encrypt_token(discord_token)
    encrypted_refresh = encrypt_token(f"test_refresh_{session_token}")
    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=ttl_seconds)

    session_data = {
        "user_id": bot_discord_id,
        "access_token": encrypted_access,
        "refresh_token": encrypted_refresh,
        "expires_at": expiry.isoformat(),
        "can_be_maintainer": can_be_maintainer,
        "is_maintainer": is_maintainer,
        "username": username,
    }

    session_key = f"api:session:{session_token}"
    await redis_client.set_json(session_key, session_data, ttl=ttl_seconds)
    await redis_client.disconnect()

    return session_token, session_data


async def cleanup_test_session(session_token: str) -> None:
    """
    Remove test session from Redis.

    Args:
        session_token: Session token to remove

    Example:
        await cleanup_test_session(session_token)
    """
    redis_client = RedisClient()
    await redis_client.connect()
    session_key = f"api:session:{session_token}"
    await redis_client.delete(session_key)
    await redis_client.disconnect()
