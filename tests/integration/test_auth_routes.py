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


"""Integration tests for auth routes via the fake Discord HTTP service.

All 5 auth endpoints are exercised through real HTTP calls against the API
container, which is wired to the fake-discord service via DISCORD_API_BASE_URL.
No patch() calls are used — all interactions go through the real request path.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from services.api.auth.tokens import encrypt_token
from tests.shared.auth_helpers import create_test_session

pytestmark = pytest.mark.integration

# Matches the fake-discord default user response in fake_discord_app.py
_FAKE_DISCORD_USER_ID = "123456789012345678"
_FAKE_DISCORD_USERNAME = "testuser"

# ============================================================================
# Success path tests
# ============================================================================


@pytest.mark.asyncio
async def test_login_returns_authorization_url_and_state(async_client, redis_client_async):
    """GET /auth/login returns 200 JSON with authorization_url and state; state stored in Redis."""
    redirect_uri = "http://localhost:3000/callback"

    response = await async_client.get("/api/v1/auth/login", params={"redirect_uri": redirect_uri})

    assert response.status_code == 200
    body = response.json()
    assert "authorization_url" in body
    assert "state" in body

    stored = await redis_client_async.get(f"oauth_state:{body['state']}")
    assert stored == redirect_uri


@pytest.mark.asyncio
async def test_callback_creates_session_on_success(redis_client_async, api_base_url):
    """Valid code + matching state → 200 JSON; session cookie set in the response."""
    state = uuid.uuid4().hex
    redirect_uri = "http://localhost:3000/callback"
    await redis_client_async.set(f"oauth_state:{state}", redirect_uri, ttl=600)

    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get(
            "/api/v1/auth/callback",
            params={"code": "fake_code", "state": state},
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    assert "session_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(create_user, api_base_url):
    """Valid session → POST /auth/refresh returns new access_token and expires_in."""
    create_user(discord_user_id=_FAKE_DISCORD_USER_ID)
    session_token, _ = await create_test_session("fake_access_token", _FAKE_DISCORD_USER_ID)

    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=10.0,
        cookies={"session_token": session_token},
    ) as client:
        response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "expires_in" in body


@pytest.mark.asyncio
async def test_logout_clears_session(create_user, api_base_url):
    """Valid session → POST /auth/logout returns 200 with a message."""
    create_user(discord_user_id=_FAKE_DISCORD_USER_ID)
    session_token, _ = await create_test_session("fake_access_token", _FAKE_DISCORD_USER_ID)

    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=10.0,
        cookies={"session_token": session_token},
    ) as client:
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    body = response.json()
    assert "message" in body


@pytest.mark.asyncio
async def test_user_info_returns_username(create_user, api_base_url):
    """Valid session → GET /auth/user returns 200 with username from fake Discord."""
    create_user(discord_user_id=_FAKE_DISCORD_USER_ID)
    session_token, _ = await create_test_session("fake.access_token", _FAKE_DISCORD_USER_ID)

    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=10.0,
        cookies={"session_token": session_token},
    ) as client:
        response = await client.get("/api/v1/auth/user")

    assert response.status_code == 200
    body = response.json()
    assert body.get("username") == _FAKE_DISCORD_USERNAME


# ============================================================================
# Error path tests (Task 4.4)
# ============================================================================


@pytest.mark.asyncio
async def test_callback_state_mismatch_returns_400(async_client):
    """GET /auth/callback with a state not in Redis → 400 Bad Request."""
    response = await async_client.get(
        "/api/v1/auth/callback",
        params={"code": "some_code", "state": "not_a_real_state"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_callback_missing_code_returns_422(async_client):
    """GET /auth/callback without a code query param → 422 Unprocessable Entity."""
    response = await async_client.get(
        "/api/v1/auth/callback",
        params={"state": "some_state"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_callback_discord_error_returns_500(redis_client_async, api_base_url):
    """Fake Discord returns 500 on code exchange → API returns 500."""
    state = uuid.uuid4().hex
    redirect_uri = "http://localhost:3000/callback"
    await redis_client_async.set(f"oauth_state:{state}", redirect_uri, ttl=600)

    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get(
            "/api/v1/auth/callback",
            params={"code": "error_trigger", "state": state},
        )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_refresh_no_session_returns_401(async_client):
    """POST /auth/refresh without a session cookie → 401 Unauthorized."""
    response = await async_client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_discord_error_returns_401(create_user, redis_client_async, api_base_url):
    """Fake Discord returns 401 on token refresh → API returns 401."""
    create_user(discord_user_id=_FAKE_DISCORD_USER_ID)

    session_token = str(uuid.uuid4())
    expiry = (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)).isoformat()
    session_data = {
        "user_id": _FAKE_DISCORD_USER_ID,
        "access_token": encrypt_token("fake_access_token"),
        "refresh_token": encrypt_token("error_refresh"),
        "expires_at": expiry,
        "can_be_maintainer": False,
        "is_maintainer": False,
    }
    await redis_client_async.set_json(f"session:{session_token}", session_data, ttl=604800)

    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=10.0,
        cookies={"session_token": session_token},
    ) as client:
        response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_info_no_session_returns_401(async_client):
    """GET /auth/user without a session cookie → 401 Unauthorized."""
    response = await async_client.get("/api/v1/auth/user")

    assert response.status_code == 401
