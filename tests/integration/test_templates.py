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


"""Integration tests for template mutation API endpoints.

Covers update_template, delete_template, set_default_template, and
reorder_templates in services/api/routes/templates.py (lines 123-128,
254, 282, 297, 311-354) that were previously uncovered.
"""

import uuid

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "123456789012345678"


@pytest.mark.asyncio
async def test_update_template_success(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/templates/{id} updates a template field."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"], name="Old Name")

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/templates/{template['id']}",
                json={"name": "Updated Name"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["name"] == "Updated Name"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_delete_template_non_default_success(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """DELETE /api/v1/templates/{id} removes a non-default template and returns 204."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.delete(f"/api/v1/templates/{template['id']}")

        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_delete_default_template_blocked(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """DELETE /api/v1/templates/{id} returns 400 when template is the default."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    admin_db_sync.execute(
        text("UPDATE game_templates SET is_default = true WHERE id = :id"),
        {"id": template["id"]},
    )
    admin_db_sync.commit()

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.delete(f"/api/v1/templates/{template['id']}")

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_set_default_template(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/templates/{id}/set-default marks the template as default."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/templates/{template['id']}/set-default")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["is_default"] is True
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_reorder_templates(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/templates/reorder reorders templates by assigning new order values."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template1 = create_template(guild_id=guild["id"], channel_id=channel["id"], name="Template A")
    template2 = create_template(guild_id=guild["id"], channel_id=channel["id"], name="Template B")

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/templates/reorder",
                json={
                    "template_orders": [
                        {template2["id"]: 1},
                        {template1["id"]: 2},
                    ]
                },
            )

        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# list_templates (lines 103-172)
# ============================================================================


@pytest.mark.asyncio
async def test_list_templates_success(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/guilds/{guild_id}/templates returns template list (lines 103-172)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    create_template(guild_id=guild["id"], channel_id=channel["id"], name="Listed Template")

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/guilds/{guild['id']}/templates")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert isinstance(data, list)
        assert any(t["name"] == "Listed Template" for t in data)
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_list_templates_manager_no_templates_returns_404(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Bot manager with no templates in guild gets 404 (lines 122-127)."""
    guild = create_guild(
        discord_guild_id="123456789012345678", bot_manager_roles=[BOT_MANAGER_ROLE_ID]
    )
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/guilds/{guild['id']}/templates")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# get_template (lines 183-194)
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_success(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/templates/{id} returns template details (lines 183-194)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/templates/{template['id']}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert response.json()["id"] == template["id"]
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_get_template_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/templates/{id} returns 404 for nonexistent template (lines 186-187)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/templates/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# update_template not-found (lines 253-254)
# ============================================================================


@pytest.mark.asyncio
async def test_update_template_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/templates/{id} returns 404 when template does not exist (lines 253-254)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/templates/{uuid.uuid4()}",
                json={"name": "Irrelevant"},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# delete_template not-found (lines 281-282)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_template_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """DELETE /api/v1/templates/{id} returns 404 when template does not exist (lines 281-282)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.delete(f"/api/v1/templates/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# set_default_template not-found (lines 314-315)
# ============================================================================


@pytest.mark.asyncio
async def test_set_default_template_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/templates/{id}/set-default returns 404 when not found (lines 314-315)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/templates/{uuid.uuid4()}/set-default")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# reorder_templates early-return and not-found (lines 336, 345-346)
# ============================================================================


@pytest.mark.asyncio
async def test_reorder_templates_empty_list_returns_204(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/templates/reorder with empty list returns 204 immediately (line 336)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/templates/reorder",
                json={"template_orders": []},
            )

        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_reorder_templates_template_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/templates/reorder with nonexistent template_id returns 404 (lines 345-346)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/templates/reorder",
                json={"template_orders": [{str(uuid.uuid4()): 1}]},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)
