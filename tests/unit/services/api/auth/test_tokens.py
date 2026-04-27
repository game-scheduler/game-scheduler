# Copyright 2026 Bret McKee
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


"""Unit tests for tokens module."""

from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import tokens

BOT_TOKEN = "Bot.test.token"


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
        mock_cfg.get_api_config.return_value.discord_bot_token = BOT_TOKEN
        result = tokens.get_guild_token(session)
        mock_cfg.get_api_config.assert_called_once_with()

    assert result == BOT_TOKEN


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

    with (
        patch(
            "services.api.auth.tokens.cache_get",
            new_callable=AsyncMock,
            return_value=session_in_redis,
        ),
        patch("services.api.auth.tokens.decrypt_token", return_value="plain"),
    ):
        result = await tokens.get_user_tokens("test-session-token")

    assert result is not None
    assert result.get("can_be_maintainer") is True
    assert result.get("is_maintainer") is True


@pytest.mark.asyncio
async def test_store_user_tokens_stores_username():
    """Test that store_user_tokens persists username in session."""
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
        await tokens.store_user_tokens("user1", "access", "refresh", 3600, username="testuser")

    assert stored_data.get("username") == "testuser"


@pytest.mark.asyncio
async def test_store_user_tokens_stores_avatar():
    """Test that store_user_tokens persists a non-None avatar hash in session."""
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
        await tokens.store_user_tokens(
            "user1", "access", "refresh", 3600, username="testuser", avatar="abc123"
        )

    assert stored_data.get("avatar") == "abc123"


@pytest.mark.asyncio
async def test_store_user_tokens_stores_none_avatar():
    """Test that store_user_tokens persists None avatar (no avatar set)."""
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
        await tokens.store_user_tokens(
            "user1", "access", "refresh", 3600, username="testuser", avatar=None
        )

    assert stored_data.get("avatar") is None


@pytest.mark.asyncio
async def test_refresh_user_tokens_updates_session_in_redis():
    """refresh_user_tokens reads then writes the session at api:session:<token>."""
    session_token = "refresh-token-abc"
    existing_session = {
        "user_id": "user1",
        "access_token": "old_enc",
        "refresh_token": "old_ref",
        "expires_at": "2099-01-01T00:00:00",
    }
    mock_redis = AsyncMock()
    captured_key = {}

    async def capture_set_json(key, data, **kwargs):
        captured_key["key"] = key

    mock_redis.set_json = AsyncMock(side_effect=capture_set_json)

    with (
        patch(
            "services.api.auth.tokens.cache_get",
            new_callable=AsyncMock,
            return_value=existing_session,
        ),
        patch(
            "services.api.auth.tokens.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
        patch("services.api.auth.tokens.encrypt_token", return_value="new_enc"),
    ):
        await tokens.refresh_user_tokens(session_token, "new_access", 3600)

    assert captured_key["key"] == f"api:session:{session_token}"


@pytest.mark.asyncio
async def test_delete_user_tokens_deletes_session_key():
    """delete_user_tokens deletes the session at api:session:<token>."""
    session_token = "delete-token-xyz"
    mock_redis = AsyncMock()

    with patch(
        "services.api.auth.tokens.cache_client.get_redis_client",
        new_callable=AsyncMock,
        return_value=mock_redis,
    ):
        await tokens.delete_user_tokens(session_token)

    mock_redis.delete.assert_called_once_with(f"api:session:{session_token}")
