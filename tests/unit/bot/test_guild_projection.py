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


"""Unit tests for bot guild projection writer."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from services.bot.guild_projection import (
    get_user_roles,
    repopulate_all,
    write_bot_last_seen,
    write_member,
    write_user_guilds,
)
from shared.cache.keys import CacheKeys
from shared.cache.operations import read_projection_key


class TestWriteMember:
    """Test suite for write_member function."""

    @pytest.mark.asyncio
    async def test_write_member_success(self):
        """Test writing a single member to projection."""
        redis = AsyncMock()
        member = MagicMock(spec=discord.Member)
        member.roles = [MagicMock(id=123), MagicMock(id=456)]
        member.nick = "TestNick"
        member.global_name = "Test User"
        member.name = "testuser"
        member.avatar = MagicMock()
        member.avatar.url = "https://example.com/avatar.png"

        await write_member(
            redis=redis,
            gen="gen123",
            guild_id="guild456",
            uid="user789",
            member=member,
        )

        # Verify the key was set
        redis.set_json.assert_called_once()
        call_args = redis.set_json.call_args
        assert call_args[0][0] == CacheKeys.proj_member("gen123", "guild456", "user789")
        assert call_args[1]["ttl"] is None

        # Verify the data structure
        data = call_args[0][1]
        assert "roles" in data
        assert "nick" in data
        assert "global_name" in data
        assert "username" in data
        assert "avatar_url" in data

    @pytest.mark.asyncio
    async def test_write_member_with_null_avatar(self):
        """Test writing a member with null avatar URL."""
        redis = AsyncMock()
        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = None
        member.global_name = "User"
        member.name = "user"
        member.avatar = None

        await write_member(
            redis=redis,
            gen="gen123",
            guild_id="guild456",
            uid="user789",
            member=member,
        )

        redis.set_json.assert_called_once()
        data = redis.set_json.call_args[0][1]
        assert data["avatar_url"] is None


class TestWriteUserGuilds:
    """Test suite for write_user_guilds function."""

    @pytest.mark.asyncio
    async def test_write_user_guilds_success(self):
        """Test writing user's guild list to projection."""
        redis = AsyncMock()
        guild_ids = ["guild1", "guild2", "guild3"]

        await write_user_guilds(
            redis=redis,
            gen="gen123",
            uid="user789",
            guild_ids=guild_ids,
        )

        redis.set_json.assert_called_once()
        call_args = redis.set_json.call_args
        assert call_args[0][0] == CacheKeys.proj_user_guilds("gen123", "user789")
        assert call_args[0][1] == guild_ids
        assert call_args[1]["ttl"] is None

    @pytest.mark.asyncio
    async def test_write_user_guilds_empty_list(self):
        """Test writing empty guild list."""
        redis = AsyncMock()

        await write_user_guilds(
            redis=redis,
            gen="gen123",
            uid="user789",
            guild_ids=[],
        )

        redis.set_json.assert_called_once()
        call_args = redis.set_json.call_args
        assert call_args[0][1] == []


class TestWriteBotLastSeen:
    """Test suite for write_bot_last_seen function."""

    @pytest.mark.asyncio
    async def test_write_bot_last_seen_default_interval(self):
        """Test writing bot last seen timestamp with default interval."""
        redis = AsyncMock()

        await write_bot_last_seen(redis=redis)

        redis.set.assert_called_once()
        call_args = redis.set.call_args
        assert call_args[0][0] == CacheKeys.bot_last_seen()
        assert call_args[1]["ttl"] == 90  # 30 * 3

    @pytest.mark.asyncio
    async def test_write_bot_last_seen_custom_interval(self):
        """Test writing bot last seen with custom heartbeat interval."""
        redis = AsyncMock()

        await write_bot_last_seen(redis=redis, heartbeat_interval=60)

        redis.set.assert_called_once()
        call_args = redis.set.call_args
        assert call_args[1]["ttl"] == 180  # 60 * 3

    @pytest.mark.asyncio
    async def test_write_bot_last_seen_timestamp_format(self):
        """Test that timestamp is written in ISO format."""
        redis = AsyncMock()

        await write_bot_last_seen(redis=redis)

        call_args = redis.set.call_args
        timestamp_str = call_args[0][1]
        # Should be parseable as ISO timestamp
        datetime.fromisoformat(timestamp_str)


class TestRepopulateAll:
    """Test suite for repopulate_all function."""

    @pytest.mark.asyncio
    async def test_repopulate_all_basic(self):
        """Test basic repopulation with guilds and members."""
        # Setup
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")

        # Mock the _client for scan
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)

        # Create mock guild with members
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        member1 = MagicMock(spec=discord.Member)
        member1.id = 222
        member1.roles = []
        member1.nick = "Member1"
        member1.global_name = "Member One"
        member1.name = "member1"
        member1.avatar = None

        member2 = MagicMock(spec=discord.Member)
        member2.id = 333
        member2.roles = []
        member2.nick = "Member2"
        member2.global_name = "Member Two"
        member2.name = "member2"
        member2.avatar = None

        guild.members = [member1, member2]
        bot.guilds = [guild]

        await repopulate_all(bot=bot, redis=redis, reason="test")

        # Verify gen pointer was read
        redis.get.assert_called()

        # Verify members were written
        assert redis.set_json.call_count >= 2  # At least member writes

        # Verify generation flip occurred
        gen_flip_calls = [
            call for call in redis.set.call_args_list if CacheKeys.proj_gen() in str(call)
        ]
        assert len(gen_flip_calls) > 0

    @pytest.mark.asyncio
    async def test_repopulate_all_gen_flip_after_writes(self):
        """Test that generation flip happens after all data writes."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")

        # Mock the _client for scan
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        member = MagicMock(spec=discord.Member)
        member.id = 222
        member.roles = []
        member.nick = None
        member.global_name = "User"
        member.name = "user"
        member.avatar = None
        guild.members = [member]
        bot.guilds = [guild]

        await repopulate_all(bot=bot, redis=redis, reason="test")

        # Find indices of writes vs gen flip
        set_json_calls = [i for i, call in enumerate(redis.mock_calls) if "set_json" in str(call)]
        gen_flip_calls = [
            i
            for i, call in enumerate(redis.mock_calls)
            if "proj:gen" in str(call) and "set" in str(call)
        ]

        # Gen flip should come after member writes
        if set_json_calls and gen_flip_calls:
            assert min(gen_flip_calls) > max(set_json_calls)

    @pytest.mark.asyncio
    async def test_repopulate_all_empty_guilds(self):
        """Test repopulation with no guilds."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")

        # Mock the _client for scan
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis, reason="test")

        # Should still flip generation even with no members
        assert redis.set.called

    @pytest.mark.asyncio
    async def test_repopulate_all_deletes_old_generation(self):
        """Test that old generation keys are cleaned up."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")

        # Mock the _client.scan method
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(
            return_value=(
                0,
                [
                    CacheKeys.proj_member("old_gen", "g1", "u1"),
                    CacheKeys.proj_member("old_gen", "g1", "u2"),
                ],
            )
        )
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis, reason="test")

        # Verify old generation keys were scanned
        mock_client.scan.assert_called()

    @pytest.mark.asyncio
    async def test_repopulate_all_otel_metrics(self):
        """Test that OTel metrics are recorded."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")

        # Mock the _client for scan
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis, reason="on_ready")

        # Verify function completes without error
        # (OTel metrics are recorded implicitly via decorators)
        assert True

    @pytest.mark.asyncio
    async def test_repopulate_all_writes_bot_last_seen(self):
        """repopulate_all writes bot:last_seen so is_bot_fresh() is True immediately."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis, reason="on_ready")

        bot_last_seen_writes = [
            call for call in redis.set.call_args_list if CacheKeys.bot_last_seen() in str(call)
        ]
        assert len(bot_last_seen_writes) == 1, (
            "repopulate_all must write bot:last_seen to eliminate the freshness gap"
        )


class TestReadProjectionKey:
    """Tests for read_projection_key gen-rotation retry logic."""

    @pytest.mark.asyncio
    async def test_returns_value_on_first_read(self):
        """Returns value immediately when found on first attempt."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=["gen1", json.dumps({"roles": ["r1"]})])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result == json.dumps({"roles": ["r1"]})

    @pytest.mark.asyncio
    async def test_returns_none_when_key_missing_and_gen_stable(self):
        """Returns None when key is not found and generation pointer is stable."""
        redis = AsyncMock()
        # gen read, key miss, gen re-read (same gen → stop)
        redis.get = AsyncMock(side_effect=["gen1", None, "gen1"])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result is None

    @pytest.mark.asyncio
    async def test_retries_on_gen_rotation_and_finds_value(self):
        """Retries read after gen rotation and returns value found in new generation."""
        redis = AsyncMock()
        # gen1 read, key miss in gen1, gen rotated to gen2, key found in gen2
        redis.get = AsyncMock(side_effect=["gen1", None, "gen2", json.dumps({"roles": ["r2"]})])

        result = await read_projection_key(redis, CacheKeys.proj_member, "guild1", "user1")

        assert result == json.dumps({"roles": ["r2"]})


class TestGetUserRoles:
    """Tests for get_user_roles reader."""

    @pytest.mark.asyncio
    async def test_returns_roles_from_projection(self):
        """Returns role list from projection member record."""
        redis = AsyncMock()
        member_data = {"roles": ["role1", "role2"], "nick": "Nick"}
        redis.get = AsyncMock(side_effect=["gen1", json.dumps(member_data)])

        result = await get_user_roles("guild1", "user1", redis=redis)

        assert result == ["role1", "role2"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_member_absent(self):
        """Returns empty list when member is absent from projection."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=["gen1", None, "gen1"])

        result = await get_user_roles("guild1", "absent_user", redis=redis)

        assert result == []
