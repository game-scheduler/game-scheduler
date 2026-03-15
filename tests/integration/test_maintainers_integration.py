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


"""Integration tests for maintainer privilege endpoints.

Tests use pre-seeded Redis sessions and discord:app_info cache keys
to exercise the toggle and refresh endpoints without real Discord API calls.
"""

import json

import httpx
import pytest

from shared.cache.keys import CacheKeys
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_MAINTAINER_DISCORD_ID = "111222333444555666"
TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"


async def _seed_app_info(redis_client_async, owner_id: str) -> None:
    """Seed discord:app_info cache to bypass real Discord API calls."""
    app_info = {"id": "999888777", "owner": {"id": owner_id}}
    await redis_client_async.set(
        CacheKeys.app_info(),
        json.dumps(app_info),
        ttl=3600,
    )


# ===========================================================================
# Toggle Endpoint Tests (Task 4.2 — RED phase; xfail against 501 stub)
# ===========================================================================


@pytest.mark.asyncio
async def test_toggle_enables_maintainer_mode(
    create_user,
    redis_client_async,
    api_base_url,
):
    """Toggle endpoint sets is_maintainer=True for a valid can_be_maintainer user."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
        is_maintainer=False,
    )
    await _seed_app_info(redis_client_async, owner_id=TEST_MAINTAINER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/toggle")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        session_data = await redis_client_async.get_json(f"session:{session_token}")
        assert session_data is not None, "Session should still exist"
        assert session_data.get("is_maintainer") is True, (
            "is_maintainer should be True after toggle"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_toggle_returns_403_without_can_be_maintainer(
    create_user,
    api_base_url,
):
    """Toggle endpoint returns 403 when user session lacks can_be_maintainer."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=False,
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/toggle")

        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_toggle_returns_403_if_not_in_discord_team(
    create_user,
    redis_client_async,
    api_base_url,
):
    """Toggle endpoint returns 403 when Discord app info shows user is not in team."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
    )
    await _seed_app_info(redis_client_async, owner_id="different_owner_99999")

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/toggle")

        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_toggle_disables_maintainer_mode(
    create_user,
    redis_client_async,
    api_base_url,
):
    """Toggle endpoint sets is_maintainer=False when maintainer mode is already enabled."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
        is_maintainer=True,
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/toggle")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        session_data = await redis_client_async.get_json(f"session:{session_token}")
        assert session_data is not None, "Session should still exist"
        assert session_data.get("is_maintainer") is False, (
            "is_maintainer should be False after toggling off"
        )
    finally:
        await cleanup_test_session(session_token)


# ===========================================================================
# Refresh Endpoint Tests (Task 4.5 — RED phase; xfail against 501 stub)
# ===========================================================================


@pytest.mark.asyncio
async def test_refresh_returns_403_for_non_maintainer(
    create_user,
    api_base_url,
):
    """Refresh endpoint returns 403 when caller does not have is_maintainer=True."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
        is_maintainer=False,
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/refresh")

        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_refresh_deletes_other_maintainer_sessions(
    create_user,
    redis_client_async,
    api_base_url,
):
    """Refresh deletes other is_maintainer sessions while preserving caller's."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    caller_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
        is_maintainer=True,
    )
    other_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        "other_elevated_user_id",
        can_be_maintainer=True,
        is_maintainer=True,
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": caller_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/refresh")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        caller_data = await redis_client_async.get_json(f"session:{caller_token}")
        assert caller_data is not None, "Caller session should be preserved"

        other_data = await redis_client_async.get_json(f"session:{other_token}")
        assert other_data is None, "Other elevated session should be deleted"
    finally:
        await cleanup_test_session(caller_token)


@pytest.mark.asyncio
async def test_refresh_flushes_app_info_cache(
    create_user,
    redis_client_async,
    api_base_url,
):
    """Refresh deletes the discord:app_info cache key."""
    create_user(discord_user_id=TEST_MAINTAINER_DISCORD_ID)

    session_token, _ = await create_test_session(
        TEST_DISCORD_TOKEN,
        TEST_MAINTAINER_DISCORD_ID,
        can_be_maintainer=True,
        is_maintainer=True,
    )
    await _seed_app_info(redis_client_async, owner_id=TEST_MAINTAINER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post("/api/v1/maintainers/refresh")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        app_info_cached = await redis_client_async.get(CacheKeys.app_info())
        assert app_info_cached is None, "discord:app_info cache should be flushed"
    finally:
        await cleanup_test_session(session_token)
