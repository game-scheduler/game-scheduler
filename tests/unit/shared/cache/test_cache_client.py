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


"""Unit tests for Redis cache client."""

import json
from unittest.mock import AsyncMock, patch

import pytest

import shared.cache.client
from shared.cache.client import RedisClient, get_redis_client


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.setex = AsyncMock()
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=300)
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def mock_pool():
    """Create mock connection pool."""
    mock = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
async def redis_client(mock_redis, mock_pool):
    """Create RedisClient with mocked connection."""
    with (
        patch("shared.cache.client.ConnectionPool") as mock_pool_class,
        patch(
            "shared.cache.client.Redis",
        ) as mock_redis_class,
    ):
        mock_pool_class.from_url.return_value = mock_pool
        mock_redis_class.return_value = mock_redis

        client = RedisClient("redis://localhost:6379/0")
        await client.connect()

        yield client

        await client.disconnect()


class TestRedisClient:
    """Test suite for RedisClient."""

    async def test_connect_success(self, mock_redis, mock_pool):
        """Test successful Redis connection."""
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch(
                "shared.cache.client.Redis",
            ) as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = mock_pool
            mock_redis_class.return_value = mock_redis

            client = RedisClient()
            await client.connect()

            assert client._client is not None
            mock_redis.ping.assert_awaited_once()

    async def test_connect_idempotent(self, redis_client):
        """Test connect is idempotent (doesn't reconnect if already connected)."""
        initial_client = redis_client._client

        await redis_client.connect()

        assert redis_client._client is initial_client

    async def test_disconnect(self, redis_client, mock_redis, mock_pool):
        """Test Redis disconnection."""
        await redis_client.disconnect()

        mock_redis.aclose.assert_awaited_once()
        mock_pool.aclose.assert_awaited_once()
        assert redis_client._client is None
        assert redis_client._pool is None

    async def test_get_success(self, redis_client, mock_redis):
        """Test successful cache GET."""
        mock_redis.get.return_value = "test_value"

        result = await redis_client.get("test_key")

        assert result == "test_value"
        mock_redis.get.assert_awaited_once_with("test_key")

    async def test_get_not_found(self, redis_client, mock_redis):
        """Test cache GET for non-existent key."""
        mock_redis.get.return_value = None

        result = await redis_client.get("missing_key")

        assert result is None

    async def test_get_error_handling(self, redis_client, mock_redis):
        """Test cache GET error handling."""
        mock_redis.get.side_effect = Exception("Connection error")

        result = await redis_client.get("test_key")

        assert result is None

    async def test_set_without_ttl(self, redis_client, mock_redis):
        """Test cache SET without TTL."""
        result = await redis_client.set("test_key", "test_value")

        assert result is True
        mock_redis.set.assert_awaited_once_with("test_key", "test_value")

    async def test_set_with_ttl(self, redis_client, mock_redis):
        """Test cache SET with TTL."""
        result = await redis_client.set("test_key", "test_value", ttl=300)

        assert result is True
        mock_redis.setex.assert_awaited_once_with("test_key", 300, "test_value")

    async def test_set_error_handling(self, redis_client, mock_redis):
        """Test cache SET error handling."""
        mock_redis.set.side_effect = Exception("Write error")

        result = await redis_client.set("test_key", "test_value")

        assert result is False

    async def test_get_json_success(self, redis_client, mock_redis):
        """Test successful JSON cache GET."""
        test_data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(test_data)

        result = await redis_client.get_json("test_key")

        assert result == test_data

    async def test_get_json_not_found(self, redis_client, mock_redis):
        """Test JSON cache GET for non-existent key."""
        mock_redis.get.return_value = None

        result = await redis_client.get_json("missing_key")

        assert result is None

    async def test_get_json_invalid(self, redis_client, mock_redis):
        """Test JSON cache GET with invalid JSON."""
        mock_redis.get.return_value = "invalid json {"

        result = await redis_client.get_json("test_key")

        assert result is None

    async def test_set_json_success(self, redis_client, mock_redis):
        """Test successful JSON cache SET."""
        test_data = {"name": "test", "value": 123}

        result = await redis_client.set_json("test_key", test_data, ttl=300)

        assert result is True
        mock_redis.setex.assert_awaited_once_with(
            "test_key",
            300,
            json.dumps(test_data),
        )

    async def test_set_json_serialization_error(self, redis_client):
        """Test JSON cache SET with non-serializable data."""

        class NotSerializable:
            pass

        result = await redis_client.set_json("test_key", NotSerializable())

        assert result is False

    async def test_delete_success(self, redis_client, mock_redis):
        """Test successful cache DELETE."""
        mock_redis.delete.return_value = 1

        result = await redis_client.delete("test_key")

        assert result is True
        mock_redis.delete.assert_awaited_once_with("test_key")

    async def test_delete_not_found(self, redis_client, mock_redis):
        """Test cache DELETE for non-existent key."""
        mock_redis.delete.return_value = 0

        result = await redis_client.delete("missing_key")

        assert result is False

    async def test_exists_true(self, redis_client, mock_redis):
        """Test cache EXISTS for existing key."""
        mock_redis.exists.return_value = 1

        result = await redis_client.exists("test_key")

        assert result is True

    async def test_exists_false(self, redis_client, mock_redis):
        """Test cache EXISTS for non-existent key."""
        mock_redis.exists.return_value = 0

        result = await redis_client.exists("missing_key")

        assert result is False

    async def test_expire_success(self, redis_client, mock_redis):
        """Test successful TTL update."""
        mock_redis.expire.return_value = True

        result = await redis_client.expire("test_key", 600)

        assert result is True
        mock_redis.expire.assert_awaited_once_with("test_key", 600)

    async def test_ttl_success(self, redis_client, mock_redis):
        """Test successful TTL retrieval."""
        mock_redis.ttl.return_value = 300

        result = await redis_client.ttl("test_key")

        assert result == 300

    async def test_ttl_no_expiry(self, redis_client, mock_redis):
        """Test TTL for key without expiry."""
        mock_redis.ttl.return_value = -1

        result = await redis_client.ttl("test_key")

        assert result == -1

    async def test_ttl_not_found(self, redis_client, mock_redis):
        """Test TTL for non-existent key."""
        mock_redis.ttl.return_value = -2

        result = await redis_client.ttl("missing_key")

        assert result == -2


class TestGetRedisClient:
    """Test suite for get_redis_client singleton."""

    async def test_singleton_returns_same_instance(self):
        """Test get_redis_client returns singleton instance."""
        with patch("shared.cache.client.RedisClient") as mock_class:
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_class.return_value = mock_instance

            # Reset the singleton

            shared.cache.client._redis_client = None

            client1 = await get_redis_client()
            client2 = await get_redis_client()

            assert client1 is client2
            mock_class.assert_called_once()
            mock_instance.connect.assert_awaited_once()
