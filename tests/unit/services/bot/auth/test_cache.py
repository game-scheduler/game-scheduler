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


"""Unit tests for role caching."""

import json
from unittest.mock import AsyncMock

import pytest

from services.bot.auth.cache import RoleCache


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def role_cache(mock_redis):
    """Create RoleCache with mock Redis."""
    return RoleCache(redis=mock_redis)


@pytest.mark.asyncio
async def test_get_user_roles_cache_hit(role_cache, mock_redis):
    """Test getting user roles from cache."""
    role_ids = ["123456", "789012"]
    mock_redis.get = AsyncMock(return_value=json.dumps(role_ids))

    result = await role_cache.get_user_roles("user123", "guild456")

    assert result == role_ids
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_roles_cache_miss(role_cache, mock_redis):
    """Test getting user roles with cache miss."""
    mock_redis.get = AsyncMock(return_value=None)

    result = await role_cache.get_user_roles("user123", "guild456")

    assert result is None
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_user_roles(role_cache, mock_redis):
    """Test caching user roles."""
    role_ids = ["123456", "789012"]

    await role_cache.set_user_roles("user123", "guild456", role_ids)

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0].endswith("user123:guild456")
    assert json.loads(call_args[0][1]) == role_ids
    assert call_args[1]["ttl"] == 300  # 5 minutes


@pytest.mark.asyncio
async def test_invalidate_user_roles(role_cache, mock_redis):
    """Test invalidating cached user roles."""
    await role_cache.invalidate_user_roles("user123", "guild456")

    mock_redis.delete.assert_called_once()
    call_args = mock_redis.delete.call_args
    assert call_args[0][0].endswith("user123:guild456")


@pytest.mark.asyncio
async def test_get_guild_roles_cache_hit(role_cache, mock_redis):
    """Test getting guild roles from cache."""
    roles = [
        {"id": "123", "name": "Admin"},
        {"id": "456", "name": "Member"},
    ]
    mock_redis.get = AsyncMock(return_value=json.dumps(roles))

    result = await role_cache.get_guild_roles("guild456")

    assert result == roles
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_guild_roles_cache_miss(role_cache, mock_redis):
    """Test getting guild roles with cache miss."""
    mock_redis.get = AsyncMock(return_value=None)

    result = await role_cache.get_guild_roles("guild456")

    assert result is None
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_guild_roles(role_cache, mock_redis):
    """Test caching guild roles."""
    roles = [
        {"id": "123", "name": "Admin"},
        {"id": "456", "name": "Member"},
    ]

    await role_cache.set_guild_roles("guild456", roles)

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert "guild456" in call_args[0][0]
    assert json.loads(call_args[0][1]) == roles
    assert call_args[1]["ttl"] == 600  # 10 minutes


@pytest.mark.asyncio
async def test_get_user_roles_redis_error(role_cache, mock_redis):
    """Test handling Redis error when getting user roles."""
    mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

    result = await role_cache.get_user_roles("user123", "guild456")

    assert result is None


@pytest.mark.asyncio
async def test_set_user_roles_redis_error(role_cache, mock_redis):
    """Test handling Redis error when setting user roles."""
    mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))

    # Should not raise exception
    await role_cache.set_user_roles("user123", "guild456", ["123"])


@pytest.mark.asyncio
async def test_invalidate_redis_error(role_cache, mock_redis):
    """Test handling Redis error when invalidating."""
    mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))

    # Should not raise exception
    await role_cache.invalidate_user_roles("user123", "guild456")
