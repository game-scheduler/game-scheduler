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


"""Integration tests for games CRUD route coverage.

Covers list_games, get_game, update_game, delete_game, join_game, and leave_game
endpoints in services/api/routes/games.py.  Specifically targets the error paths
and optional form-field handling that are missing from existing tests.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "123456789012345678"


async def _setup_game_context(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
) -> dict:
    """Create guild/channel/user/template and seed Redis for game tests."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    return {
        "guild_id": guild["id"],
        "guild_discord_id": guild["guild_id"],
        "channel_id": channel["id"],
        "channel_discord_id": channel["channel_id"],
        "user_id": user["id"],
        "template_id": template["id"],
    }


async def _create_game_via_api(
    client: httpx.AsyncClient,
    ctx: dict,
    title: str = "Test Game",
) -> dict:
    """Create a game through the API and return the response JSON."""
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    response = await client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": title,
            "scheduled_at": scheduled_at,
        },
    )
    assert response.status_code == 201, f"Game creation failed: {response.text}"
    return response.json()


# ============================================================================
# create_game image handling (lines 75-88, 326-352, 366-369)
# ============================================================================


@pytest.mark.asyncio
async def test_create_game_thumbnail_too_large_returns_400(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a thumbnail exceeding 5 MB returns 400 (line 88)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=30.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            big_file = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 1)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Big Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("big.png", big_file, "image/png")},
            )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_with_banner_image(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a banner image stores it (lines 343-352)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Banner Game",
                    "scheduled_at": scheduled_at,
                },
                files={"image": ("banner.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_with_thumbnail(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a valid PNG thumbnail stores the image (lines 326-335)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("icon.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_invalid_thumbnail_type_returns_400(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a non-image thumbnail returns 400 (lines 75-80)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Bad Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("bad.txt", b"not an image", "text/plain")},
            )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_nonexistent_template_returns_404(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a nonexistent template_id returns 404 (lines 368-369)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": str(uuid.uuid4()),
                    "title": "Bad Template Game",
                    "scheduled_at": scheduled_at,
                },
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# list_games (lines 392-422)
# ============================================================================


@pytest.mark.asyncio
async def test_list_games_returns_authorized_games(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games returns games the user is authorized to see (lines 392-422)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Listed Game")
            response = await client.get(
                "/api/v1/games",
                params={"guild_id": ctx["guild_id"]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "games" in data
        assert any(g["id"] == game["id"] for g in data["games"])
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# get_game (lines 435-462)
# ============================================================================


@pytest.mark.asyncio
async def test_get_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns game details for an authorized user (lines 435-462)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Get Game Test")
            response = await client.get(f"/api/v1/games/{game['id']}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["id"] == game["id"]
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_get_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns 404 for nonexistent game (lines 435-440)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/games/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# update_game (lines 153, 157, 161, 165, 169, 199-200, 552-555)
# ============================================================================


@pytest.mark.asyncio
async def test_update_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} updates game title and returns updated game (lines 552-555)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Original Title")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={"title": "Updated Title"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert response.json()["title"] == "Updated Title"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_with_all_optional_form_fields(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with all optional parsed fields covers lines 153,157,161,165,169."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Optional Fields Game")
            scheduled_at = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "scheduled_at": scheduled_at,
                    "reminder_minutes": json.dumps([30, 60]),
                    "notify_role_ids": json.dumps([]),
                    "participants": json.dumps([]),
                    "removed_participant_ids": json.dumps([]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_remove_thumbnail(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with remove_thumbnail=true covers lines 199-200."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Remove Thumbnail Game")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={"remove_thumbnail": "true"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_nonexistent_returns_404(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with nonexistent game returns 404 (lines 554-555, 247-249)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/games/{uuid.uuid4()}",
                data={"title": "Should Not Matter"},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_with_image_file(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with a banner image processes the upload (lines 203-214)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Image Update Game")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                files={"image": ("banner.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# delete_game (lines 577-586)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """DELETE /api/v1/games/{id} returns 404 for a nonexistent game (lines 577-585)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.delete(f"/api/v1/games/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# clone_game (lines 612-616)
# ============================================================================


@pytest.mark.asyncio
async def test_clone_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/clone with nonexistent game returns 404 (lines 612-614)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                f"/api/v1/games/{uuid.uuid4()}/clone",
                json={"title": "Cloned Game", "scheduled_at": scheduled_at},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# join_game (lines 635-684)
# ============================================================================


@pytest.mark.asyncio
async def test_join_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join with nonexistent game returns 404 (lines 635-637)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{uuid.uuid4()}/join")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_join_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join adds user as participant (lines 638-684)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    host_user = create_user()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host_user["id"],
        template_id=template["id"],
        status="SCHEDULED",
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{game['id']}/join")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["discord_id"] == TEST_BOT_DISCORD_ID
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# leave_game (lines 698-713)
# ============================================================================


@pytest.mark.asyncio
async def test_leave_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/leave with nonexistent game returns 404 (lines 698-712)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{uuid.uuid4()}/leave")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)
