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


"""Unit tests for API-side member projection reader."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from shared.cache.keys import CacheKeys
from shared.cache.operations import _MAX_GEN_RETRIES, read_projection_key
from shared.cache.projection import (
    get_member,
    get_user_guilds,
    get_user_roles,
    is_bot_fresh,
    search_members_by_prefix,
)


def _make_redis(get_return: str | None = None) -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=get_return)
    return redis


class TestReadProjectionKey:
    """Test suite for read_projection_key shared function."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_value(self):
        """Returns value immediately on first read when gen is stable."""
        redis = _make_redis(get_return="gen123")
        redis.get = AsyncMock(side_effect=["gen123", "value_data", "gen123"])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result == "value_data"

    @pytest.mark.asyncio
    async def test_stable_gen_miss_returns_none(self):
        """Returns None and increments not_found when key absent and gen stable."""
        redis = _make_redis()
        # gen read, key miss, gen re-read (same gen = stable miss)
        redis.get = AsyncMock(side_effect=["gen123", None, "gen123"])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result is None

    @pytest.mark.asyncio
    async def test_gen_rotation_retries(self):
        """Retries when gen changes between read attempts."""
        redis = _make_redis()
        # First attempt: get gen1, key miss, re-read gen2 (changed) → retry
        # Second attempt: get gen2, key hit → return value
        redis.get = AsyncMock(side_effect=["gen1", None, "gen2", "value_data", "gen2"])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result == "value_data"

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_returns_none(self):
        """Returns None after _MAX_GEN_RETRIES iterations without a hit."""
        redis = _make_redis()
        # Gen is read once before the loop, then (key miss, gen re-read) per iteration.
        # Each iteration sees a changed gen, triggering a retry until retries exhausted.
        side_effects = ["gen0"]
        for i in range(_MAX_GEN_RETRIES):
            side_effects.extend([None, f"gen{i + 1}"])
        redis.get = AsyncMock(side_effect=side_effects)

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result is None


class TestGetUserGuilds:
    """Test suite for get_user_guilds function."""

    @pytest.mark.asyncio
    async def test_returns_guild_list(self):
        """Returns parsed list when projection key exists."""
        redis = _make_redis()
        guild_list = ["guild1", "guild2"]
        redis.get = AsyncMock(side_effect=["gen123", json.dumps(guild_list), "gen123"])

        result = await get_user_guilds("user1", redis=redis)

        assert result == guild_list

    @pytest.mark.asyncio
    async def test_returns_none_when_absent(self):
        """Returns None when user has no projection entry."""
        redis = _make_redis()
        redis.get = AsyncMock(side_effect=["gen123", None, "gen123"])

        result = await get_user_guilds("user1", redis=redis)

        assert result is None


class TestGetMember:
    """Test suite for get_member function."""

    @pytest.mark.asyncio
    async def test_returns_member_dict(self):
        """Returns parsed member dict when projection key exists."""
        redis = _make_redis()
        member_data = {
            "roles": ["role1"],
            "nick": "TestNick",
            "global_name": "Test User",
            "username": "testuser",
            "avatar_url": None,
        }
        redis.get = AsyncMock(side_effect=["gen123", json.dumps(member_data), "gen123"])

        result = await get_member("guild1", "user1", redis=redis)

        assert result == member_data

    @pytest.mark.asyncio
    async def test_returns_none_when_absent(self):
        """Returns None when member has no projection entry."""
        redis = _make_redis()
        redis.get = AsyncMock(side_effect=["gen123", None, "gen123"])

        result = await get_member("guild1", "user1", redis=redis)

        assert result is None


class TestGetUserRoles:
    """Test suite for get_user_roles function."""

    @pytest.mark.asyncio
    async def test_returns_roles_from_member(self):
        """Returns role list from member projection entry."""
        redis = _make_redis()
        member_data = {
            "roles": ["role1", "role2"],
            "nick": None,
            "global_name": "U",
            "username": "u",
            "avatar_url": None,
        }
        redis.get = AsyncMock(side_effect=["gen123", json.dumps(member_data), "gen123"])

        result = await get_user_roles("guild1", "user1", redis=redis)

        assert result == ["role1", "role2"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_absent(self):
        """Returns empty list when member absent from projection."""
        redis = _make_redis()
        redis.get = AsyncMock(side_effect=["gen123", None, "gen123"])

        result = await get_user_roles("guild1", "user1", redis=redis)

        assert result == []


class TestIsBotFresh:
    """Test suite for is_bot_fresh function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_fresh(self):
        """Returns True when bot:last_seen key exists and is recent."""
        redis = _make_redis()
        recent = datetime.now(UTC).isoformat()
        redis.get = AsyncMock(return_value=recent)

        result = await is_bot_fresh(redis=redis)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_absent(self):
        """Returns False when bot:last_seen key is absent."""
        redis = _make_redis(get_return=None)

        result = await is_bot_fresh(redis=redis)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_stale(self):
        """Returns False when bot:last_seen timestamp is too old."""
        redis = _make_redis()
        stale = (datetime.now(UTC) - timedelta(seconds=300)).isoformat()
        redis.get = AsyncMock(return_value=stale)

        result = await is_bot_fresh(redis=redis)

        assert result is False


class TestSearchMembersByPrefix:
    """Test suite for search_members_by_prefix function."""

    @pytest.mark.asyncio
    async def test_returns_matching_members_by_prefix(self):
        """Returns members whose username/nick matches the prefix."""
        redis = _make_redis()
        redis.get = AsyncMock(return_value="gen1")

        member_data = {
            "roles": [],
            "nick": None,
            "global_name": "Alice",
            "username": "alice",
            "avatar_url": None,
        }
        mock_client = AsyncMock()
        mock_client.zrangebylex = AsyncMock(return_value=["alice\x00user1"])
        redis._client = mock_client
        # calls: own gen, read_projection_key gen, read_projection_key value
        redis.get = AsyncMock(side_effect=["gen1", "gen1", json.dumps(member_data)])

        results = await search_members_by_prefix("guild1", "ali", redis=redis)

        assert len(results) == 1
        assert results[0]["uid"] == "user1"
        assert results[0]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_deduplicates_same_member_matching_multiple_names(self):
        """Member matching both username and nick appears only once."""
        redis = _make_redis()
        member_data = {
            "roles": [],
            "nick": "ali_nick",
            "global_name": "Alice",
            "username": "alice",
            "avatar_url": None,
        }
        mock_client = AsyncMock()
        mock_client.zrangebylex = AsyncMock(return_value=["ali_nick\x00user1", "alice\x00user1"])
        redis._client = mock_client
        # calls: own gen, read_projection_key gen+value (uid seen, second entry skipped)
        redis.get = AsyncMock(side_effect=["gen1", "gen1", json.dumps(member_data)])

        results = await search_members_by_prefix("guild1", "ali", redis=redis)

        assert len(results) == 1
        assert results[0]["uid"] == "user1"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_gen_absent(self):
        """Returns empty list when projection gen pointer is absent (bot not ready)."""
        redis = _make_redis(get_return=None)

        results = await search_members_by_prefix("guild1", "ali", redis=redis)

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_prefix_match(self):
        """Returns empty list when no entries match the prefix."""
        redis = _make_redis()
        redis.get = AsyncMock(return_value="gen1")
        mock_client = AsyncMock()
        mock_client.zrangebylex = AsyncMock(return_value=[])
        redis._client = mock_client

        results = await search_members_by_prefix("guild1", "xyz", redis=redis)

        assert results == []
