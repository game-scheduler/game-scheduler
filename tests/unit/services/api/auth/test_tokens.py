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


"""Unit tests for token management."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import tokens
from services.api.auth.tokens import (
    decrypt_token,
    delete_user_tokens,
    encrypt_token,
    get_encryption_key,
    get_user_tokens,
    is_token_expired,
    refresh_user_tokens,
    store_user_tokens,
)


class TestTokenEncryption:
    """Test token encryption and decryption."""

    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption round trip."""
        original_token = "test_access_token_123"

        encrypted = encrypt_token(original_token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original_token
        assert encrypted != original_token

    def test_encryption_key_generation(self):
        """Test encryption key is properly generated."""
        key = get_encryption_key()

        assert isinstance(key, bytes)
        assert len(key) == 44


class TestTokenStorage:
    """Test token storage and retrieval."""

    @pytest.mark.asyncio
    async def test_store_user_tokens(self):
        """Test storing user tokens in Redis."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            session_token = await store_user_tokens(
                user_id="123456789",
                access_token="test_access",
                refresh_token="test_refresh",
                expires_in=3600,
            )

            assert isinstance(session_token, str)
            assert len(session_token) == 36  # UUID4 format
            mock_redis_instance.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_tokens_success(self):
        """Test retrieving user tokens from Redis."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
            encrypted_access = encrypt_token("test_access")
            encrypted_refresh = encrypt_token("test_refresh")

            mock_redis_instance.get_json.return_value = {
                "user_id": "123456789",
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "expires_at": expires_at.isoformat(),
            }

            result = await get_user_tokens("123456789")

            assert result is not None
            assert result["access_token"] == "test_access"
            assert result["refresh_token"] == "test_refresh"
            assert result["user_id"] == "123456789"

    @pytest.mark.asyncio
    async def test_get_user_tokens_not_found(self):
        """Test retrieving non-existent user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get_json.return_value = None

            result = await get_user_tokens("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_user_tokens(self):
        """Test refreshing user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
            encrypted_access = encrypt_token("old_access")
            encrypted_refresh = encrypt_token("test_refresh")
            session_token = "test-uuid-token"

            mock_redis_instance.get_json.return_value = {
                "user_id": "123456789",
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "expires_at": expires_at.isoformat(),
            }

            await refresh_user_tokens(
                session_token=session_token, new_access_token="new_access", new_expires_in=7200
            )

            mock_redis_instance.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_tokens(self):
        """Test deleting user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            await delete_user_tokens("123456789")

            mock_redis_instance.delete.assert_called_once_with("session:123456789")


class TestTokenExpiry:
    """Test token expiry checking."""

    @pytest.mark.asyncio
    async def test_is_token_expired_true(self):
        """Test expired token detection."""
        past_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)

        is_expired = await is_token_expired(past_time)

        assert is_expired is True

    @pytest.mark.asyncio
    async def test_is_token_expired_false(self):
        """Test valid token detection."""
        future_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

        is_expired = await is_token_expired(future_time)

        assert is_expired is False

    @pytest.mark.asyncio
    async def test_is_token_expired_buffer(self):
        """Test token expiry with 5-minute buffer."""
        almost_expired = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=3)

        is_expired = await is_token_expired(almost_expired)

        assert is_expired is True


# ---------------------------------------------------------------------------
# Guild token and maintainer flag tests
# ---------------------------------------------------------------------------

_BOT_TOKEN = "Bot.test.token"


def _make_session(*, is_maintainer: bool = False) -> dict:
    return {
        "user_id": "123",
        "access_token": "plain_oauth_token",
        "refresh_token": "plain_refresh",
        "expires_at": "2099-01-01T00:00:00",
        "can_be_maintainer": True,
        "is_maintainer": is_maintainer,
    }


def test_get_guild_token_returns_bot_token_for_maintainer():
    """Test that a maintainer session returns the bot token."""
    session = _make_session(is_maintainer=True)

    with patch("services.api.auth.tokens.config") as mock_cfg:
        mock_cfg.get_api_config.return_value.discord_bot_token = _BOT_TOKEN
        result = tokens.get_guild_token(session)

    assert result == _BOT_TOKEN


def test_get_guild_token_returns_oauth_token_for_regular_user():
    """Test that a non-maintainer session returns the OAuth token."""
    session = _make_session(is_maintainer=False)

    result = tokens.get_guild_token(session)

    assert result == "plain_oauth_token"


def test_get_guild_token_returns_oauth_token_when_flag_missing():
    """Test that a session without is_maintainer falls back to the OAuth token."""
    session = {
        "user_id": "123",
        "access_token": "plain_oauth_token",
        "refresh_token": "plain_refresh",
        "expires_at": "2099-01-01T00:00:00",
    }

    result = tokens.get_guild_token(session)

    assert result == "plain_oauth_token"


@pytest.mark.asyncio
async def test_store_user_tokens_stores_can_be_maintainer_false_by_default():
    """Test that store_user_tokens stores can_be_maintainer=False
    and is_maintainer=False by default.
    """
    mock_redis = AsyncMock()
    mock_redis.set_json = AsyncMock()
    stored_data = {}

    async def capture_set_json(key, data, **kwargs):
        stored_data.update(data)

    mock_redis.set_json.side_effect = capture_set_json

    with (
        patch(
            "services.api.auth.tokens.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
        patch("services.api.auth.tokens.encrypt_token", return_value="enc"),
    ):
        await tokens.store_user_tokens("user1", "access", "refresh", 3600)

    assert stored_data.get("can_be_maintainer") is False
    assert stored_data.get("is_maintainer") is False


@pytest.mark.asyncio
async def test_store_user_tokens_stores_can_be_maintainer_true():
    """Test that store_user_tokens stores can_be_maintainer=True when passed."""
    mock_redis = AsyncMock()
    stored_data = {}

    async def capture_set_json(key, data, **kwargs):
        stored_data.update(data)

    mock_redis.set_json = AsyncMock(side_effect=capture_set_json)

    with (
        patch(
            "services.api.auth.tokens.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
        patch("services.api.auth.tokens.encrypt_token", return_value="enc"),
    ):
        await tokens.store_user_tokens("user1", "access", "refresh", 3600, can_be_maintainer=True)

    assert stored_data.get("can_be_maintainer") is True
    assert stored_data.get("is_maintainer") is False


@pytest.mark.asyncio
async def test_get_user_tokens_returns_maintainer_flags():
    """Test that get_user_tokens returns can_be_maintainer and is_maintainer from session."""
    session_in_redis = {
        "user_id": "user1",
        "access_token": "enc_access",
        "refresh_token": "enc_refresh",
        "expires_at": "2099-01-01T00:00:00",
        "can_be_maintainer": True,
        "is_maintainer": True,
    }
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value=session_in_redis)

    with (
        patch(
            "services.api.auth.tokens.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
        patch("services.api.auth.tokens.decrypt_token", return_value="plain"),
    ):
        result = await tokens.get_user_tokens("test-session-token")

    assert result is not None
    assert result.get("can_be_maintainer") is True
    assert result.get("is_maintainer") is True
