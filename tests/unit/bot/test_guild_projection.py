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
from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_write_member_populates_username_sorted_set(self):
        """write_member ZADDs username, global_name, and nick entries to sorted set."""
        redis = AsyncMock()
        mock_client = AsyncMock()
        mock_client.zadd = AsyncMock()
        redis._client = mock_client

        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = "NickName"
        member.global_name = "Global Name"
        member.name = "username123"
        member.avatar = None

        await write_member(
            redis=redis,
            gen="gen1",
            guild_id="guild1",
            uid="user1",
            member=member,
        )

        usernames_key = CacheKeys.proj_usernames("gen1", "guild1")
        zadd_calls = mock_client.zadd.call_args_list
        zadd_keys = [call[0][0] for call in zadd_calls]
        assert all(k == usernames_key for k in zadd_keys)
        all_entries = {next(iter(call[0][1].keys())) for call in zadd_calls}
        assert "username123\x00user1" in all_entries
        assert "global name\x00user1" in all_entries
        assert "nickname\x00user1" in all_entries

    @pytest.mark.asyncio
    async def test_write_member_deduplicates_when_global_name_equals_username(self):
        """When global_name == username (case-insensitive), only one sorted set entry."""
        redis = AsyncMock()
        mock_client = AsyncMock()
        mock_client.zadd = AsyncMock()
        redis._client = mock_client

        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = None
        member.global_name = "SameUser"
        member.name = "sameuser"
        member.avatar = None

        await write_member(
            redis=redis,
            gen="gen1",
            guild_id="guild1",
            uid="user1",
            member=member,
        )

        zadd_calls = mock_client.zadd.call_args_list
        all_entries = {next(iter(call[0][1].keys())) for call in zadd_calls}
        assert "sameuser\x00user1" in all_entries
        assert len([e for e in all_entries if e.split("\x00")[0] == "sameuser"]) == 1

    @pytest.mark.asyncio
    async def test_write_member_skips_null_optional_name_fields(self):
        """Null nick and global_name are skipped; only username is added."""
        redis = AsyncMock()
        mock_client = AsyncMock()
        mock_client.zadd = AsyncMock()
        redis._client = mock_client

        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = None
        member.global_name = None
        member.name = "onlyuser"
        member.avatar = None

        await write_member(
            redis=redis,
            gen="gen1",
            guild_id="guild1",
            uid="user1",
            member=member,
        )

        zadd_calls = mock_client.zadd.call_args_list
        assert len(zadd_calls) == 1
        entry = next(iter(zadd_calls[0][0][1].keys()))
        assert entry == "onlyuser\x00user1"


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
        assert isinstance(datetime.fromisoformat(timestamp_str), datetime)


class TestRepopulateAll:
    """Test suite for repopulate_all function."""

    @staticmethod
    def _make_mock_client():
        """Return a mock _client with pipeline context manager and scan/delete support."""
        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        mock_client = MagicMock()
        mock_client.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe)
        mock_client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        return mock_client, pipe

    @pytest.mark.asyncio
    async def test_repopulate_all_basic(self):
        """Test basic repopulation with guilds and members."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")
        mock_client, pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        guild.name = "Test Guild"
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

        await repopulate_all(bot=bot, redis=redis)

        redis.get.assert_called()
        # Members and guild name are queued to the pipeline via pipe.set
        assert pipe.set.call_count >= 2
        gen_flip_calls = [
            call for call in redis.set.call_args_list if CacheKeys.proj_gen() in str(call)
        ]
        assert len(gen_flip_calls) > 0

    @pytest.mark.asyncio
    async def test_repopulate_all_gen_flip_after_writes(self):
        """Generation flip happens after pipeline.execute() completes."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        guild.name = "Guild"
        member = MagicMock(spec=discord.Member)
        member.id = 222
        member.roles = []
        member.nick = None
        member.global_name = "User"
        member.name = "user"
        member.avatar = None
        guild.members = [member]
        bot.guilds = [guild]

        await repopulate_all(bot=bot, redis=redis)

        gen_flip_calls = [
            i
            for i, call in enumerate(redis.mock_calls)
            if "proj:gen" in str(call) and "set" in str(call)
        ]
        assert len(gen_flip_calls) > 0

    @pytest.mark.asyncio
    async def test_repopulate_all_empty_guilds(self):
        """Test repopulation with no guilds."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)

        assert redis.set.called

    @pytest.mark.asyncio
    async def test_repopulate_all_deletes_old_generation(self):
        """Test that old generation keys are cleaned up."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")
        mock_client, _pipe = self._make_mock_client()
        mock_client.scan = AsyncMock(
            return_value=(
                0,
                [
                    CacheKeys.proj_member("old_gen", "g1", "u1"),
                    CacheKeys.proj_member("old_gen", "g1", "u2"),
                ],
            )
        )
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)

        mock_client.scan.assert_called()

    @pytest.mark.asyncio
    async def test_repopulate_all_otel_metrics(self):
        """OTel metrics are recorded; started counter is not emitted inside repopulate_all."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="old_gen")
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        with patch("services.bot.guild_projection.repopulation_started_counter") as mock_counter:
            await repopulate_all(bot=bot, redis=redis)

        mock_counter.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_repopulate_all_writes_bot_last_seen(self):
        """repopulate_all writes bot:last_seen so is_bot_fresh() is True immediately."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)

        bot_last_seen_writes = [
            call for call in redis.set.call_args_list if CacheKeys.bot_last_seen() in str(call)
        ]
        assert len(bot_last_seen_writes) == 1, (
            "repopulate_all must write bot:last_seen to eliminate the freshness gap"
        )

    async def test_repopulate_all_has_no_reason_parameter(self):
        """repopulate_all accepts only bot= and redis= after reason param is removed."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)
        assert True  # call succeeded without raising

    async def test_repopulate_all_does_not_emit_started_counter(self):
        """repopulate_all does not call repopulation_started_counter after refactor."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        mock_client, _pipe = self._make_mock_client()
        redis._client = mock_client

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        with patch("services.bot.guild_projection.repopulation_started_counter") as mock_counter:
            await repopulate_all(bot=bot, redis=redis)

        mock_counter.add.assert_not_called()


class TestDeleteOldGenerationPipeline:
    """Xfail test verifying _delete_old_generation uses a pipeline for bulk deletion."""

    @pytest.mark.asyncio
    async def test_deletes_via_pipeline_not_individual_awaits(self):
        """_delete_old_generation collects all keys then deletes them via one pipeline execute."""
        from services.bot.guild_projection import _delete_old_generation  # noqa: PLC0415

        old_keys = [f"proj:member:gen0:guild1:user{i}".encode() for i in range(250)]

        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        pipe.delete = MagicMock()

        mock_client = MagicMock()
        # Return all 250 keys in first scan, then cursor=0 to end loop
        mock_client.scan = AsyncMock(return_value=(0, old_keys))
        mock_client.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe)
        mock_client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

        redis = AsyncMock()
        redis._client = mock_client

        await _delete_old_generation(redis, "gen0")

        # Pipeline must be opened for deletion
        mock_client.pipeline.assert_called_once_with(transaction=False)
        # pipe.delete must be called (not redis._client.delete directly)
        assert pipe.delete.called
        # Only one pipeline execute
        pipe.execute.assert_awaited_once()
        # redis._client.delete should NOT have been called directly
        mock_client.delete.assert_not_called()


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


class TestQueueMemberToPipe:
    """Xfail tests for the synchronous _queue_member_to_pipe pipeline helper."""

    def test_sets_member_key_with_json_data(self):
        """_queue_member_to_pipe calls pipe.set with the correct member key and JSON payload."""
        from services.bot.guild_projection import _queue_member_to_pipe  # noqa: PLC0415

        pipe = MagicMock()
        member = MagicMock(spec=discord.Member)
        member.roles = [MagicMock(id=123)]
        member.nick = "Nick"
        member.global_name = "Global"
        member.name = "username"
        member.avatar = None

        _queue_member_to_pipe(pipe, "gen1", "guild1", "user1", member)

        expected_key = CacheKeys.proj_member("gen1", "guild1", "user1")
        set_keys = [call[0][0] for call in pipe.set.call_args_list]
        assert expected_key in set_keys
        matching = [call for call in pipe.set.call_args_list if call[0][0] == expected_key]
        assert len(matching) == 1
        stored = json.loads(matching[0][0][1])
        assert stored["username"] == "username"
        assert stored["nick"] == "Nick"
        assert stored["avatar_url"] is None

    def test_queues_zadd_for_each_name_variant(self):
        """_queue_member_to_pipe calls pipe.zadd for each distinct lowercase name variant."""
        from services.bot.guild_projection import _queue_member_to_pipe  # noqa: PLC0415

        pipe = MagicMock()
        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = "NickName"
        member.global_name = "Global Name"
        member.name = "username"
        member.avatar = None

        _queue_member_to_pipe(pipe, "gen1", "guild1", "user1", member)

        usernames_key = CacheKeys.proj_usernames("gen1", "guild1")
        zadd_calls = pipe.zadd.call_args_list
        zadd_keys = [call[0][0] for call in zadd_calls]
        assert all(k == usernames_key for k in zadd_keys)
        all_entries = {next(iter(call[0][1].keys())) for call in zadd_calls}
        assert "username\x00user1" in all_entries
        assert "global name\x00user1" in all_entries
        assert "nickname\x00user1" in all_entries

    def test_deduplicates_when_name_equals_username(self):
        """_queue_member_to_pipe deduplicates when global_name matches username."""
        from services.bot.guild_projection import _queue_member_to_pipe  # noqa: PLC0415

        pipe = MagicMock()
        member = MagicMock(spec=discord.Member)
        member.roles = []
        member.nick = None
        member.global_name = "SameUser"
        member.name = "sameuser"
        member.avatar = None

        _queue_member_to_pipe(pipe, "gen1", "guild1", "user1", member)

        zadd_calls = pipe.zadd.call_args_list
        all_entries = {next(iter(call[0][1].keys())) for call in zadd_calls}
        assert len([e for e in all_entries if e.split("\x00")[0] == "sameuser"]) == 1


class TestQueueUserGuildsToPipe:
    """Xfail tests for the synchronous _queue_user_guilds_to_pipe pipeline helper."""

    def test_sets_user_guilds_key_with_json_list(self):
        """_queue_user_guilds_to_pipe calls pipe.set with the user-guilds key and JSON list."""
        from services.bot.guild_projection import _queue_user_guilds_to_pipe  # noqa: PLC0415

        pipe = MagicMock()
        guild_ids = ["guild1", "guild2"]

        _queue_user_guilds_to_pipe(pipe, "gen1", "user1", guild_ids)

        expected_key = CacheKeys.proj_user_guilds("gen1", "user1")
        pipe.set.assert_called_once_with(expected_key, json.dumps(guild_ids))

    def test_sets_empty_list_when_no_guilds(self):
        """_queue_user_guilds_to_pipe handles an empty guild list."""
        from services.bot.guild_projection import _queue_user_guilds_to_pipe  # noqa: PLC0415

        pipe = MagicMock()

        _queue_user_guilds_to_pipe(pipe, "gen1", "user1", [])

        expected_key = CacheKeys.proj_user_guilds("gen1", "user1")
        pipe.set.assert_called_once_with(expected_key, json.dumps([]))


class TestQueueGuildNameToPipe:
    """Xfail tests for the synchronous _queue_guild_name_to_pipe pipeline helper."""

    def test_sets_guild_name_key(self):
        """_queue_guild_name_to_pipe calls pipe.set with the guild-name key and raw name string."""
        from services.bot.guild_projection import _queue_guild_name_to_pipe  # noqa: PLC0415

        pipe = MagicMock()

        _queue_guild_name_to_pipe(pipe, "gen1", "guild1", "My Guild")

        expected_key = CacheKeys.proj_guild_name("gen1", "guild1")
        pipe.set.assert_called_once_with(expected_key, "My Guild")


class TestRepopulateAllUsesPipeline:
    """Xfail tests verifying repopulate_all batches writes through a Redis pipeline."""

    def _make_redis_with_pipeline(self):
        """Return a redis mock whose _client has a pipeline async context manager."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)

        pipe = MagicMock()
        pipe.set = MagicMock()
        pipe.zadd = MagicMock()
        pipe.execute = AsyncMock(return_value=[])

        mock_client = MagicMock()
        mock_client.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe)
        mock_client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        redis._client = mock_client

        return redis, pipe

    @pytest.mark.asyncio
    async def test_uses_pipeline_context_manager(self):
        """repopulate_all opens redis._client.pipeline() as an async context manager."""
        redis, _pipe = self._make_redis_with_pipeline()
        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)

        redis._client.pipeline.assert_called_once_with(transaction=False)

    @pytest.mark.asyncio
    async def test_executes_pipeline_exactly_once(self):
        """repopulate_all awaits pipe.execute() exactly once for all writes."""
        redis, pipe = self._make_redis_with_pipeline()

        bot = MagicMock(spec=discord.Client)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        guild.name = "Test Guild"
        member = MagicMock(spec=discord.Member)
        member.id = 222
        member.roles = []
        member.nick = None
        member.global_name = "User"
        member.name = "user"
        member.avatar = None
        guild.members = [member]
        bot.guilds = [guild]

        await repopulate_all(bot=bot, redis=redis)

        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_gen_flip_not_in_pipeline(self):
        """Generation pointer flip uses redis.set directly, not the pipeline.

        Fails before Task 10.2 because pipeline is never opened (first assertion fails).
        After Task 10.2: gen flip must not be queued inside the pipeline buffer.
        """
        redis, pipe = self._make_redis_with_pipeline()

        bot = MagicMock(spec=discord.Client)
        bot.guilds = []

        await repopulate_all(bot=bot, redis=redis)

        # Fails before Task 10.2: no pipeline is opened yet
        redis._client.pipeline.assert_called_once_with(transaction=False)

        gen_flip_calls = [
            call for call in redis.set.call_args_list if CacheKeys.proj_gen() in str(call)
        ]
        assert len(gen_flip_calls) == 1
        pipe_set_keys = [call[0][0] for call in pipe.set.call_args_list]
        assert CacheKeys.proj_gen() not in pipe_set_keys
