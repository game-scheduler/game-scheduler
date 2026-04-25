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


"""Unit tests for CacheOperation StrEnum and cache_get helper."""

from enum import StrEnum
from unittest.mock import AsyncMock, MagicMock, patch

from shared.cache.operations import CacheOperation, cache_get

_EXPECTED_OPERATIONS = {
    "fetch_guild",
    "fetch_channel",
    "fetch_guild_roles",
    "fetch_guild_channels",
    "get_application_info",
    "user_roles_api",
    "display_name",
    "session_lookup",
    "session_refresh",
    "oauth_state",
    "user_roles_bot",
    "guild_roles_bot",
}


def test_cache_operation_is_str_enum() -> None:
    assert issubclass(CacheOperation, StrEnum)


def test_cache_operation_members() -> None:
    values = {member.value for member in CacheOperation}
    assert values == _EXPECTED_OPERATIONS


def test_cache_operation_fetch_guild_value() -> None:
    assert CacheOperation.FETCH_GUILD == "fetch_guild"


async def test_cache_get_hit_returns_value() -> None:
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value={"id": "123"})
    mock_counter = MagicMock()
    mock_histogram = MagicMock()

    with (
        patch("shared.cache.operations.get_redis_client", return_value=mock_redis),
        patch("shared.cache.operations._hit_counter", mock_counter),
        patch("shared.cache.operations._miss_counter", MagicMock()),
        patch("shared.cache.operations._duration_histogram", mock_histogram),
    ):
        result = await cache_get("some:key", CacheOperation.SESSION_LOOKUP)

    assert result == {"id": "123"}
    mock_counter.add.assert_called_once_with(1, {"operation": CacheOperation.SESSION_LOOKUP})


async def test_cache_get_miss_returns_none() -> None:
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value=None)
    mock_counter = MagicMock()
    mock_histogram = MagicMock()

    with (
        patch("shared.cache.operations.get_redis_client", return_value=mock_redis),
        patch("shared.cache.operations._hit_counter", MagicMock()),
        patch("shared.cache.operations._miss_counter", mock_counter),
        patch("shared.cache.operations._duration_histogram", mock_histogram),
    ):
        result = await cache_get("some:key", CacheOperation.SESSION_LOOKUP)

    assert result is None
    mock_counter.add.assert_called_once_with(1, {"operation": CacheOperation.SESSION_LOOKUP})


async def test_cache_get_records_duration_on_hit() -> None:
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value={"data": "value"})
    mock_histogram = MagicMock()

    with (
        patch("shared.cache.operations.get_redis_client", return_value=mock_redis),
        patch("shared.cache.operations._hit_counter", MagicMock()),
        patch("shared.cache.operations._miss_counter", MagicMock()),
        patch("shared.cache.operations._duration_histogram", mock_histogram),
    ):
        await cache_get("some:key", CacheOperation.OAUTH_STATE)

    call_kwargs = mock_histogram.record.call_args
    assert call_kwargs is not None
    _duration, labels = call_kwargs.args[0], call_kwargs.args[1]
    assert labels["operation"] == CacheOperation.OAUTH_STATE
    assert labels["result"] == "hit"


async def test_cache_get_records_duration_on_miss() -> None:
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value=None)
    mock_histogram = MagicMock()

    with (
        patch("shared.cache.operations.get_redis_client", return_value=mock_redis),
        patch("shared.cache.operations._hit_counter", MagicMock()),
        patch("shared.cache.operations._miss_counter", MagicMock()),
        patch("shared.cache.operations._duration_histogram", mock_histogram),
    ):
        await cache_get("some:key", CacheOperation.OAUTH_STATE)

    call_kwargs = mock_histogram.record.call_args
    assert call_kwargs is not None
    _duration, labels = call_kwargs.args[0], call_kwargs.args[1]
    assert labels["operation"] == CacheOperation.OAUTH_STATE
    assert labels["result"] == "miss"


async def test_cache_get_passes_operation_label_to_all_metrics() -> None:
    mock_redis = AsyncMock()
    mock_redis.get_json = AsyncMock(return_value=None)
    mock_hit = MagicMock()
    mock_miss = MagicMock()
    mock_histogram = MagicMock()

    with (
        patch("shared.cache.operations.get_redis_client", return_value=mock_redis),
        patch("shared.cache.operations._hit_counter", mock_hit),
        patch("shared.cache.operations._miss_counter", mock_miss),
        patch("shared.cache.operations._duration_histogram", mock_histogram),
    ):
        await cache_get("some:key", CacheOperation.GUILD_ROLES_BOT)

    miss_labels = mock_miss.add.call_args.args[1]
    hist_labels = mock_histogram.record.call_args.args[1]
    assert miss_labels["operation"] == CacheOperation.GUILD_ROLES_BOT
    assert hist_labels["operation"] == CacheOperation.GUILD_ROLES_BOT
