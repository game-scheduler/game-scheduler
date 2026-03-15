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


"""Unit tests for maintainer privilege endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.routes.maintainers import refresh_maintainers, toggle_maintainer_mode
from shared.schemas.auth import CurrentUser


def _make_current_user(session_token: str = "test-session-token") -> CurrentUser:  # noqa: S107
    return CurrentUser(
        user=MagicMock(),
        access_token="fake-access-token",
        session_token=session_token,
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client with an async _client for scan_iter support."""
    mock = AsyncMock()
    mock._client = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def patch_get_redis(mock_redis):
    """Patch cache_client.get_redis_client for all tests in this module."""
    with patch(
        "services.api.routes.maintainers.cache_client.get_redis_client",
        AsyncMock(return_value=mock_redis),
    ):
        yield


# ===========================================================================
# toggle_maintainer_mode
# ===========================================================================


@pytest.mark.asyncio
async def test_toggle_sets_is_maintainer_true(mock_redis):
    """Toggle sets is_maintainer=True and persists session when all checks pass."""
    user = _make_current_user("session-abc")
    mock_redis.get_json.return_value = {
        "user_id": "111222333",
        "can_be_maintainer": True,
        "is_maintainer": False,
    }

    with patch(
        "services.api.routes.maintainers.oauth2.is_app_maintainer",
        AsyncMock(return_value=True),
    ):
        result = await toggle_maintainer_mode(user)

    assert result == {"is_maintainer": True}
    saved_data = mock_redis.set_json.call_args[0][1]
    assert saved_data["is_maintainer"] is True


@pytest.mark.asyncio
async def test_toggle_returns_403_when_no_session(mock_redis):
    """Toggle returns 403 when session data is absent."""
    mock_redis.get_json.return_value = None

    with pytest.raises(Exception) as exc_info:
        await toggle_maintainer_mode(_make_current_user())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_toggle_returns_403_without_can_be_maintainer(mock_redis):
    """Toggle returns 403 when session lacks can_be_maintainer."""
    mock_redis.get_json.return_value = {"user_id": "111", "can_be_maintainer": False}

    with pytest.raises(Exception) as exc_info:
        await toggle_maintainer_mode(_make_current_user())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_toggle_returns_403_when_not_in_discord_team(mock_redis):
    """Toggle returns 403 when Discord app info excludes the user."""
    mock_redis.get_json.return_value = {"user_id": "111", "can_be_maintainer": True}

    with patch(
        "services.api.routes.maintainers.oauth2.is_app_maintainer",
        AsyncMock(return_value=False),
    ):
        with pytest.raises(Exception) as exc_info:
            await toggle_maintainer_mode(_make_current_user())

    assert exc_info.value.status_code == 403


# ===========================================================================
# refresh_maintainers
# ===========================================================================


@pytest.mark.asyncio
async def test_refresh_returns_403_when_no_session(mock_redis):
    """Refresh returns 403 when session data is absent."""
    mock_redis.get_json.return_value = None

    with pytest.raises(Exception) as exc_info:
        await refresh_maintainers(_make_current_user())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_refresh_returns_403_when_not_maintainer(mock_redis):
    """Refresh returns 403 when caller has is_maintainer=False."""
    mock_redis.get_json.return_value = {
        "user_id": "111",
        "can_be_maintainer": True,
        "is_maintainer": False,
    }

    with pytest.raises(Exception) as exc_info:
        await refresh_maintainers(_make_current_user())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_refresh_deletes_other_maintainer_sessions(mock_redis):
    """Refresh deletes other sessions with is_maintainer=True."""
    caller_token = "caller-token"
    user = _make_current_user(caller_token)
    caller_key = f"session:{caller_token}"
    other_key = "session:other-elevated"

    async def get_json_side(key):
        if key == caller_key:
            return {"user_id": "111", "is_maintainer": True}
        return {"user_id": "999", "is_maintainer": True}

    mock_redis.get_json.side_effect = get_json_side

    async def scan_iter(_pattern):
        yield caller_key
        yield other_key

    mock_redis._client.scan_iter = scan_iter

    result = await refresh_maintainers(user)

    assert result == {"status": "ok"}
    deleted = [call[0][0] for call in mock_redis.delete.call_args_list]
    assert other_key in deleted
    assert caller_key not in deleted


@pytest.mark.asyncio
async def test_refresh_preserves_non_maintainer_sessions(mock_redis):
    """Refresh does not delete sessions where is_maintainer is False."""
    caller_token = "caller-token"
    user = _make_current_user(caller_token)
    caller_key = f"session:{caller_token}"
    normal_key = "session:normal-user"

    async def get_json_side(key):
        if key == caller_key:
            return {"user_id": "111", "is_maintainer": True}
        return {"user_id": "888", "is_maintainer": False}

    mock_redis.get_json.side_effect = get_json_side

    async def scan_iter(_pattern):
        yield caller_key
        yield normal_key

    mock_redis._client.scan_iter = scan_iter

    await refresh_maintainers(user)

    deleted = [call[0][0] for call in mock_redis.delete.call_args_list]
    assert normal_key not in deleted


@pytest.mark.asyncio
async def test_refresh_flushes_app_info_cache(mock_redis):
    """Refresh deletes the discord:app_info cache key."""
    caller_token = "caller-token"
    user = _make_current_user(caller_token)
    caller_key = f"session:{caller_token}"
    mock_redis.get_json.return_value = {"user_id": "111", "is_maintainer": True}

    async def scan_iter(_pattern):
        yield caller_key

    mock_redis._client.scan_iter = scan_iter

    await refresh_maintainers(user)

    deleted = [call[0][0] for call in mock_redis.delete.call_args_list]
    assert "discord:app_info" in deleted
