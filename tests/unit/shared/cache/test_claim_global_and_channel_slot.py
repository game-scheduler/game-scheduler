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


"""Unit tests for RedisClient.claim_global_and_channel_slot."""

from unittest.mock import ANY, AsyncMock, patch

import pytest
import redis

from shared.cache.client import (
    _REDIS_ERROR_BACKOFF_BASE_MS,
    _REDIS_ERROR_BACKOFF_JITTER_MS,
    RedisClient,
)


class TestClaimGlobalAndChannelSlot:
    """Verify combined global + per-channel rate-limit slot claim."""

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        mock = AsyncMock()
        mock.ping = AsyncMock()
        mock.eval = AsyncMock(return_value=0)
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    async def client_and_mock(self, mock_redis: AsyncMock):
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch("shared.cache.client.Redis") as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = AsyncMock()
            mock_redis_class.return_value = mock_redis
            client = RedisClient("redis://localhost:6379/0")
            await client.connect()
            yield client, mock_redis
            await client.disconnect()

    async def test_both_available_returns_0(self, client_and_mock: tuple) -> None:
        """When both budgets have capacity, returns 0 and claims both slots."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        result = await client.claim_global_and_channel_slot("111222333")

        assert result == 0

    async def test_global_full_returns_wait(self, client_and_mock: tuple) -> None:
        """When global budget is exhausted, returns positive wait and claims nothing."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 50

        result = await client.claim_global_and_channel_slot("111222333")

        assert result == 50

    async def test_channel_full_returns_wait(self, client_and_mock: tuple) -> None:
        """When channel budget is exhausted, returns positive wait and claims nothing."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1000

        result = await client.claim_global_and_channel_slot("111222333")

        assert result == 1000

    async def test_both_full_returns_max_wait(self, client_and_mock: tuple) -> None:
        """When both limits are exhausted, returns the larger wait value."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1200

        result = await client.claim_global_and_channel_slot("111222333")

        assert result == 1200

    async def test_global_key_is_discord_global_rate_limit(self, client_and_mock: tuple) -> None:
        """Global sorted-set key is discord:global_rate_limit."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_and_channel_slot("987654321")

        _script, _numkeys, global_key_arg = mock_redis.eval.call_args.args[:3]
        assert global_key_arg == "discord:global_rate_limit"

    async def test_channel_key_scoped_to_channel_id(self, client_and_mock: tuple) -> None:
        """Per-channel sorted-set key is channel_rate_limit:{channel_id}."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_and_channel_slot("987654321")

        _script, _numkeys, _global_key, channel_key_arg = mock_redis.eval.call_args.args[:4]
        assert channel_key_arg == "channel_rate_limit:987654321"

    async def test_returns_int(self, client_and_mock: tuple) -> None:
        """Return value is always an int."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = "40"

        result = await client.claim_global_and_channel_slot("123")

        assert isinstance(result, int)
        assert result == 40

    async def test_eval_error_returns_jittered_backoff(self, client_and_mock: tuple) -> None:
        """On Redis error the method fails closed with a jittered 1000-1250ms backoff."""
        client, mock_redis = client_and_mock
        mock_redis.eval.side_effect = Exception("connection lost")

        result = await client.claim_global_and_channel_slot("999")

        assert (
            _REDIS_ERROR_BACKOFF_BASE_MS
            <= result
            <= _REDIS_ERROR_BACKOFF_BASE_MS + _REDIS_ERROR_BACKOFF_JITTER_MS
        )

    async def test_lua_script_constant_exists(self) -> None:
        """_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA constant is importable."""
        from shared.cache.client import _GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA  # noqa: PLC0415

        assert isinstance(_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA, str)
        assert len(_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA) > 0

    async def test_auto_connects_when_no_client(self, mock_redis: AsyncMock) -> None:
        """claim_global_and_channel_slot establishes connection if not yet connected."""
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch("shared.cache.client.Redis") as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = AsyncMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.eval.return_value = 0

            client = RedisClient("redis://localhost:6379/0")
            assert client._client is None

            result = await client.claim_global_and_channel_slot("555")

            assert client._client is not None
            assert result == 0
            mock_pool_class.from_url.assert_called_once_with(
                "redis://localhost:6379/0", max_connections=ANY, decode_responses=True
            )
            mock_redis_class.assert_called_once_with(
                connection_pool=mock_pool_class.from_url.return_value
            )

    async def test_global_max_override_passed_as_argv3(self, client_and_mock: tuple) -> None:
        """When global_max=45 is supplied, ARGV[3] of the Lua eval receives '45'."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_and_channel_slot("111", global_max=45)

        call_args = mock_redis.eval.call_args.args
        global_max_arg = call_args[6]  # ARGV[3] = global_max
        assert global_max_arg == "45"

    async def test_default_global_max_is_25(self, client_and_mock: tuple) -> None:
        """Default global_max (no argument) sends '25' as ARGV[3]."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_and_channel_slot("222")

        call_args = mock_redis.eval.call_args.args
        global_max_arg = call_args[6]  # ARGV[3] = global_max
        assert global_max_arg == "25"

    async def test_no_permission_error_is_reraised(self, client_and_mock: tuple) -> None:
        """NoPermissionError propagates instead of returning a backoff.

        ACL misconfigurations must surface immediately so callers get a clear
        error rather than looping forever on a jittered backoff.
        """
        client, mock_redis = client_and_mock
        mock_redis.eval.side_effect = redis.exceptions.NoPermissionError("NOPERM")

        with pytest.raises(redis.exceptions.NoPermissionError):
            await client.claim_global_and_channel_slot("999")


class TestClaimGlobalSlot:
    """Verify global-only rate-limit slot claim (no per-channel constraint)."""

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        mock = AsyncMock()
        mock.ping = AsyncMock()
        mock.eval = AsyncMock(return_value=0)
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    async def client_and_mock(self, mock_redis: AsyncMock):
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch("shared.cache.client.Redis") as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = AsyncMock()
            mock_redis_class.return_value = mock_redis
            client = RedisClient("redis://localhost:6379/0")
            await client.connect()
            yield client, mock_redis
            await client.disconnect()

    async def test_both_available_returns_0(self, client_and_mock: tuple) -> None:
        """When global budget has capacity, returns 0."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        result = await client.claim_global_slot()

        assert result == 0

    async def test_global_full_returns_wait(self, client_and_mock: tuple) -> None:
        """When global budget is exhausted, returns positive wait."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 40

        result = await client.claim_global_slot()

        assert result == 40

    async def test_uses_global_rate_limit_key(self, client_and_mock: tuple) -> None:
        """Global key is discord:global_rate_limit."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot()

        _script, _numkeys, global_key_arg = mock_redis.eval.call_args.args[:3]
        assert global_key_arg == "discord:global_rate_limit"

    async def test_no_sentinel_channel_key(self, client_and_mock: tuple) -> None:
        """No sentinel channel key — eval receives exactly 3 positional args after the script."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot()

        _script, numkeys, _global_key, _now_ms, _global_max = mock_redis.eval.call_args.args
        assert numkeys == 1

    async def test_returns_int(self, client_and_mock: tuple) -> None:
        """Return value is always an int."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = "30"

        result = await client.claim_global_slot()

        assert isinstance(result, int)
        assert result == 30

    async def test_eval_error_returns_jittered_backoff(self, client_and_mock: tuple) -> None:
        """On Redis error the method fails closed with a jittered 1000-1250ms backoff."""
        client, mock_redis = client_and_mock
        mock_redis.eval.side_effect = Exception("timeout")

        result = await client.claim_global_slot()

        assert (
            _REDIS_ERROR_BACKOFF_BASE_MS
            <= result
            <= _REDIS_ERROR_BACKOFF_BASE_MS + _REDIS_ERROR_BACKOFF_JITTER_MS
        )

    async def test_auto_connects_when_no_client(self, mock_redis: AsyncMock) -> None:
        """claim_global_slot establishes connection if not yet connected."""
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch("shared.cache.client.Redis") as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = AsyncMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.eval.return_value = 0

            client = RedisClient("redis://localhost:6379/0")
            assert client._client is None

            result = await client.claim_global_slot()

            assert client._client is not None
            assert result == 0
            mock_pool_class.from_url.assert_called_once_with(
                "redis://localhost:6379/0", max_connections=ANY, decode_responses=True
            )
            mock_redis_class.assert_called_once_with(
                connection_pool=mock_pool_class.from_url.return_value
            )

    async def test_global_max_override_passed_as_argv2(self, client_and_mock: tuple) -> None:
        """When global_max=45 is supplied, ARGV[2] of the Lua eval receives '45'."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot(global_max=45)

        call_args = mock_redis.eval.call_args.args
        global_max_arg = call_args[4]  # ARGV[2] = global_max
        assert global_max_arg == "45"

    async def test_default_global_max_is_25(self, client_and_mock: tuple) -> None:
        """Default global_max (no argument) sends '25' as ARGV[2]."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot()

        call_args = mock_redis.eval.call_args.args
        global_max_arg = call_args[4]  # ARGV[2] = global_max
        assert global_max_arg == "25"

    async def test_uses_one_key_not_two(self, client_and_mock: tuple) -> None:
        """claim_global_slot must pass numkeys=1, not 2.

        The sentinel channel key (discord:_no_channel) accumulates entries from
        every claim_global_slot call and triggers the 1000-1500ms inter-edit
        spacing check, serializing concurrent API requests with ~1.5s gaps.
        """
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot()

        _script, numkeys = mock_redis.eval.call_args.args[:2]
        assert numkeys == 1, "must use only 1 Redis key (global only, no sentinel channel key)"

    async def test_global_max_is_argv2(self, client_and_mock: tuple) -> None:
        """global_max must be ARGV[2] (index 4) once the sentinel key is removed."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_global_slot(global_max=45)

        call_args = mock_redis.eval.call_args.args
        global_max_arg = call_args[4]  # ARGV[2] = global_max after sentinel removal
        assert global_max_arg == "45"

    async def test_no_permission_error_is_reraised(self, client_and_mock: tuple) -> None:
        """NoPermissionError propagates instead of returning a backoff.

        ACL misconfigurations must surface immediately so callers get a clear
        error rather than looping forever on a jittered backoff.
        """
        client, mock_redis = client_and_mock
        mock_redis.eval.side_effect = redis.exceptions.NoPermissionError("NOPERM")

        with pytest.raises(redis.exceptions.NoPermissionError):
            await client.claim_global_slot()
