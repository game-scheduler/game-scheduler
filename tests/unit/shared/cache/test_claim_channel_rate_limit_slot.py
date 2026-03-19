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


"""Unit tests for RedisClient.claim_channel_rate_limit_slot."""

from unittest.mock import AsyncMock, patch

import pytest

from shared.cache.client import RedisClient


class TestClaimChannelRateLimitSlot:
    """Verify the rate-limit slot claim interface and key semantics."""

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

    async def test_empty_window_returns_0(self, client_and_mock: tuple) -> None:
        """First edit in an idle channel proceeds immediately (wait = 0)."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 0

    async def test_spacing_n1_returns_1000(self, client_and_mock: tuple) -> None:
        """Second edit right after the first carries 1000ms spacing wait."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1000

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 1000

    async def test_spacing_n2_returns_1000(self, client_and_mock: tuple) -> None:
        """Third edit right after second carries 1000ms spacing wait."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1000

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 1000

    async def test_spacing_n3_returns_1500(self, client_and_mock: tuple) -> None:
        """Fourth edit right after third carries 1500ms spacing wait."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1500

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 1500

    async def test_spacing_n4_returns_1500(self, client_and_mock: tuple) -> None:
        """Fifth edit right after fourth carries 1500ms spacing wait."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 1500

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 1500

    async def test_window_full_returns_window_expiry_wait(self, client_and_mock: tuple) -> None:
        """When 5+ edits fill the 5s window, returns ms until oldest edit leaves."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 3000

        result = await client.claim_channel_rate_limit_slot("111222333")

        assert result == 3000

    async def test_key_scoped_to_channel_id(self, client_and_mock: tuple) -> None:
        """Sorted-set key is channel_rate_limit:{channel_id}."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_channel_rate_limit_slot("987654321012345678")

        _script, _numkeys, key_arg = mock_redis.eval.call_args.args[:3]
        assert key_arg == "channel_rate_limit:987654321012345678"

    async def test_lua_script_sets_pexpire_5001(self) -> None:
        """Lua script sets key TTL to 5001ms so idle keys vanish automatically."""
        from shared.cache.client import _CHANNEL_RATE_LIMIT_LUA  # noqa: PLC0415

        assert "5001" in _CHANNEL_RATE_LIMIT_LUA
        assert "pexpire" in _CHANNEL_RATE_LIMIT_LUA.lower()

    async def test_independent_channels_do_not_share_state(self, client_and_mock: tuple) -> None:
        """Two distinct channels use separate sorted-set keys."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = 0

        await client.claim_channel_rate_limit_slot("AAA")
        await client.claim_channel_rate_limit_slot("BBB")

        calls = mock_redis.eval.call_args_list
        key_a = calls[0].args[2]
        key_b = calls[1].args[2]
        assert key_a == "channel_rate_limit:AAA"
        assert key_b == "channel_rate_limit:BBB"
        assert key_a != key_b

    async def test_returns_int(self, client_and_mock: tuple) -> None:
        """Return value is always an int, not a raw Redis byte/string."""
        client, mock_redis = client_and_mock
        mock_redis.eval.return_value = "750"  # redis-py may return bytes or str

        result = await client.claim_channel_rate_limit_slot("123")

        assert isinstance(result, int)
        assert result == 750

    async def test_auto_connects_when_no_client(self, mock_redis: AsyncMock) -> None:
        """Method establishes connection if not yet connected."""
        with (
            patch("shared.cache.client.ConnectionPool") as mock_pool_class,
            patch("shared.cache.client.Redis") as mock_redis_class,
        ):
            mock_pool_class.from_url.return_value = AsyncMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.eval.return_value = 0

            client = RedisClient("redis://localhost:6379/0")
            assert client._client is None

            result = await client.claim_channel_rate_limit_slot("555")

            assert client._client is not None
            assert result == 0

    async def test_eval_error_returns_0(self, client_and_mock: tuple) -> None:
        """On Redis error the method fails open and returns 0 (allow the edit)."""
        client, mock_redis = client_and_mock
        mock_redis.eval.side_effect = Exception("connection lost")

        result = await client.claim_channel_rate_limit_slot("999")

        assert result == 0
