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
) -> tuple[str, dict]:
    """
    Create test session in Redis with encrypted tokens.

    Args:
        discord_token: Discord bot token to encrypt and store
        bot_discord_id: Discord ID of the bot user
        ttl_seconds: Session TTL in seconds (default: 7 days)

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
    }

    session_key = f"session:{session_token}"
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
    session_key = f"session:{session_token}"
    await redis_client.delete(session_key)
    await redis_client.disconnect()
