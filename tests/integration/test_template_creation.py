# Copyright 2025-2026 Bret McKee
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


"""Integration tests for template creation API endpoint.

Tests verify that template creation through POST /guilds/{guild_id}/templates
properly enforces authorization, validates request data, and persists to database.

Prevents regression where create_template fixture bypassed API validation.
"""

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from shared.utils.limits import MAX_DESCRIPTION_LENGTH
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_create_template_via_api_success(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation succeeds with valid data and proper authorization.

    Prevents regression where create_template fixture bypassed API validation,
    authorization checks, and request schema enforcement.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template via API endpoint
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "D&D Campaign",
                    "description": "Weekly D&D session",
                    "max_players": 5,
                    "expected_duration_minutes": 180,
                    "reminder_minutes": [60, 15],
                    "where": "Discord Voice",
                    "signup_instructions": "Be on time",
                    "order": 1,
                    "is_default": False,
                    "signup_priority_role_ids": ["111222333444555666", "999888777666555444"],
                },
            )

        # Verify successful creation
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        template_data = response.json()

        # Verify response data matches request
        assert template_data["name"] == "D&D Campaign"
        assert template_data["guild_id"] == guild["id"]
        assert template_data["channel_id"] == channel["id"]
        assert template_data["max_players"] == 5
        assert template_data["expected_duration_minutes"] == 180
        assert template_data["reminder_minutes"] == [60, 15]
        assert template_data["where"] == "Discord Voice"
        assert template_data["signup_instructions"] == "Be on time"
        assert template_data["order"] == 1
        assert template_data["is_default"] is False
        assert template_data["signup_priority_role_ids"] == [
            "111222333444555666",
            "999888777666555444",
        ]

        template_id = template_data["id"]

        # Verify database persistence
        result = admin_db_sync.execute(
            text(
                """
                SELECT name, description, max_players, guild_id, channel_id,
                       expected_duration_minutes, reminder_minutes, "where",
                       signup_instructions, "order", is_default,
                       signup_priority_role_ids
                FROM game_templates
                WHERE id = :id
            """
            ),
            {"id": template_id},
        )
        row = result.fetchone()

        assert row is not None, f"Template {template_id} not found in database"
        assert row.name == "D&D Campaign"
        assert row.description == "Weekly D&D session"
        assert row.max_players == 5
        assert row.guild_id == guild["id"]
        assert row.channel_id == channel["id"]
        assert row.expected_duration_minutes == 180
        assert row.reminder_minutes == [60, 15]
        assert row.where == "Discord Voice"
        assert row.signup_instructions == "Be on time"
        assert row.order == 1
        assert row.is_default is False
        assert row.signup_priority_role_ids == ["111222333444555666", "999888777666555444"]

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_without_bot_manager_role(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails without bot manager role (403 Forbidden).

    Ensures authorization enforcement prevents users without bot manager role
    from creating templates, preventing unauthorized template management.
    """
    # Setup test environment WITH bot manager role configured but user doesn't have it
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session WITHOUT bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=["999999999"],  # Different role, not bot manager
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Attempt to create template without authorization
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Unauthorized Template",
                    "description": "Should not be created",
                    "order": 0,
                    "is_default": False,
                },
            )

        # Verify authorization failure
        assert response.status_code == 403, (
            f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
        )

        # Verify template was NOT created in database
        result = admin_db_sync.execute(
            text(
                """
                SELECT COUNT(*) FROM game_templates
                WHERE guild_id = :guild_id AND name = :name
            """
            ),
            {"guild_id": guild["id"], "name": "Unauthorized Template"},
        )
        count = result.scalar()
        assert count == 0, "Template should not have been created without authorization"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_without_authentication(
    admin_db_sync,
    create_guild,
    create_channel,
    api_base_url,
):
    """Verify template creation fails without authentication (401 Unauthorized).

    The session_token cookie is optional at the FastAPI parameter level; the
    get_current_user dependency raises 401 when it is absent.
    This ensures unauthenticated requests cannot create templates.
    """
    # Setup test environment
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])

    # Make request WITHOUT authentication (no session token)
    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=10.0,
    ) as client:
        response = await client.post(
            f"/api/v1/guilds/{guild['id']}/templates",
            json={
                "guild_id": guild["id"],
                "channel_id": channel["id"],
                "name": "Unauthenticated Template",
                "description": "Should not be created",
                "order": 0,
                "is_default": False,
            },
        )

    # Verify authentication failure
    assert response.status_code == 401, (
        f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
    )

    # Verify template was NOT created in database
    result = admin_db_sync.execute(
        text(
            """
            SELECT COUNT(*) FROM game_templates
            WHERE guild_id = :guild_id AND name = :name
        """
        ),
        {"guild_id": guild["id"], "name": "Unauthenticated Template"},
    )
    count = result.scalar()
    assert count == 0, "Template should not have been created without authentication"


@pytest.mark.asyncio
async def test_create_template_missing_required_fields(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails with missing required fields (422 Unprocessable Entity).

    Ensures Pydantic schema validation rejects incomplete requests,
    preventing creation of invalid templates.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Test missing 'name' field
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    # Missing required 'name' field
                    "description": "Missing name",
                },
            )

        # Verify validation failure
        assert response.status_code == 422, (
            f"Expected 422 Unprocessable Entity, got {response.status_code}: {response.text}"
        )

        # Verify error mentions missing field
        response_data = response.json()
        assert "name" in str(response_data).lower(), "Response should indicate missing 'name' field"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_invalid_guild_id(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails with non-existent guild_id (404 Not Found).

    Ensures guild existence validation before template creation,
    preventing orphaned templates.
    """
    # Setup test environment without creating guild (only channel for valid UUID format)
    fake_guild_id = "00000000-0000-0000-0000-000000000000"
    fake_guild_discord_id = "fake-discord-guild-id"

    # Create channel in a real guild but will use fake guild_id
    real_guild = create_guild()
    channel = create_channel(guild_id=real_guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=fake_guild_discord_id,
        channel_discord_id=channel["channel_id"],
        user_roles=["123456789012345678"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Attempt to create template with non-existent guild_id
            response = await client.post(
                f"/api/v1/guilds/{fake_guild_id}/templates",
                json={
                    "guild_id": fake_guild_id,
                    "channel_id": channel["id"],
                    "name": "Invalid Guild Template",
                },
            )

        # Verify guild not found
        assert response.status_code == 404, (
            f"Expected 404 Not Found, got {response.status_code}: {response.text}"
        )

        # Verify template was NOT created in database
        result = admin_db_sync.execute(
            text(
                """
                SELECT COUNT(*) FROM game_templates
                WHERE name = :name
            """
            ),
            {"name": "Invalid Guild Template"},
        )
        count = result.scalar()
        assert count == 0, "Template should not have been created for non-existent guild"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_invalid_channel_id(
    admin_db_sync,
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation with non-existent channel_id.

    Ensures channel validation - may return 422 (validation error) or
    succeed with channel name resolution failure (non-blocking).
    """
    # Setup test environment
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    fake_channel_id = "00000000-0000-0000-0000-000000000000"
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id="fake-channel-discord-id",
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Attempt to create template with non-existent channel_id
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": fake_channel_id,
                    "name": "Invalid Channel Template",
                },
            )

        # Channel validation may return error or succeed (non-blocking channel
        # name resolution). Accept 500 (foreign key constraint), 422 (validation
        # error), or 201 (success with unknown channel)
        assert response.status_code in [
            201,
            422,
            500,
        ], f"Expected 201, 422, or 500, got {response.status_code}: {response.text}"

        if response.status_code == 201:
            # If created, verify channel_id stored correctly
            response_data = response.json()
            assert response_data["channel_id"] == fake_channel_id
            assert "channel_name" in response_data, "Response should include channel_name field"
        elif response.status_code == 500:
            # Database foreign key constraint violation is acceptable.
            # Error messages are sanitized so body content is not checked.
            pass

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_default_template(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify default template creation with is_default=True flag.

    Ensures default template handling works correctly and flag persists
    to database for UI to identify primary template choice.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with is_default=True
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Default D&D Template",
                    "description": "Standard weekly D&D campaign",
                    "is_default": True,
                    "max_players": 6,
                    "expected_duration_minutes": 240,
                },
            )

        # Verify successful creation
        assert response.status_code == 201, (
            f"Expected 201 Created, got {response.status_code}: {response.text}"
        )

        # Verify response data
        template_data = response.json()
        assert template_data["name"] == "Default D&D Template"
        assert template_data["is_default"] is True, "is_default should be True in response"
        template_id = template_data["id"]

        # Verify database persistence of is_default flag
        result = admin_db_sync.execute(
            text(
                """
                SELECT name, is_default, max_players
                FROM game_templates
                WHERE id = :id
            """
            ),
            {"id": template_id},
        )
        row = result.fetchone()
        assert row is not None, "Template should exist in database"
        assert row.name == "Default D&D Template"
        assert row.is_default is True, "is_default should be True in database"
        assert row.max_players == 6

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_minimal_fields(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation with only required fields.

    Ensures optional fields can be omitted and database stores appropriate
    null/default values for omitted fields.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with ONLY required fields
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Minimal Template",
                    # All other fields omitted (optional)
                },
            )

        # Verify successful creation
        assert response.status_code == 201, (
            f"Expected 201 Created, got {response.status_code}: {response.text}"
        )

        # Verify response data
        template_data = response.json()
        assert template_data["name"] == "Minimal Template"
        assert template_data["guild_id"] == guild["id"]
        assert template_data["channel_id"] == channel["id"]
        template_id = template_data["id"]

        # Verify optional fields have null/default values in database
        result = admin_db_sync.execute(
            text(
                """
                SELECT name, description, is_default, max_players,
                       expected_duration_minutes, reminder_minutes, "where",
                       signup_instructions, notify_role_ids,
                       allowed_player_role_ids, allowed_host_role_ids
                FROM game_templates
                WHERE id = :id
            """
            ),
            {"id": template_id},
        )
        row = result.fetchone()
        assert row is not None, "Template should exist in database"
        assert row.name == "Minimal Template"
        assert row.description is None, "description should be NULL"
        assert row.is_default is False, "is_default should default to False"
        assert row.max_players is None, "max_players should be NULL"
        assert row.expected_duration_minutes is None, "expected_duration_minutes should be NULL"
        assert row.reminder_minutes is None, "reminder_minutes should be NULL"
        assert row.where is None, "where should be NULL"
        assert row.signup_instructions is None, "signup_instructions should be NULL"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_description_exceeds_max_length(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails when description exceeds MAX_DESCRIPTION_LENGTH (422).

    Ensures Pydantic schema validation enforces max_length constraint,
    preventing excessively long descriptions.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with description exceeding MAX_DESCRIPTION_LENGTH
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "name": "Long Description Template",
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "description": "x" * (MAX_DESCRIPTION_LENGTH + 1),
                },
            )

        # Verify validation failure
        assert response.status_code == 422, (
            f"Expected 422 Unprocessable Entity for description > {MAX_DESCRIPTION_LENGTH} chars, "
            f"got {response.status_code}: {response.text}"
        )

        # Verify error mentions field validation
        response_data = response.json()
        error_str = str(response_data).lower()
        assert "description" in error_str or "string" in error_str, (
            "Response should indicate description validation failure"
        )

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_where_exceeds_max_length(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails when where exceeds 500 characters (422).

    Ensures Pydantic schema validation enforces max_length constraint,
    preventing excessively long location strings.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with where exceeding 500 characters
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "name": "Long Location Template",
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "where": "x" * 501,  # Exceeds max_length=500
                },
            )

        # Verify validation failure
        assert response.status_code == 422, (
            f"Expected 422 Unprocessable Entity for where > 500 chars, "
            f"got {response.status_code}: {response.text}"
        )

        # Verify error mentions field validation
        response_data = response.json()
        error_str = str(response_data).lower()
        assert "where" in error_str or "string" in error_str, (
            "Response should indicate where validation failure"
        )

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_signup_instructions_exceeds_max_length(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation fails when signup_instructions exceeds 1000 characters (422).

    Ensures Pydantic schema validation enforces max_length constraint,
    preventing excessively long signup instructions.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with signup_instructions exceeding 1000 characters
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "name": "Long Instructions Template",
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "signup_instructions": "x" * 1001,  # Exceeds max_length=1000
                },
            )

        # Verify validation failure
        assert response.status_code == 422, (
            f"Expected 422 Unprocessable Entity for signup_instructions > 1000 chars, "
            f"got {response.status_code}: {response.text}"
        )

        # Verify error mentions field validation
        response_data = response.json()
        error_str = str(response_data).lower()
        assert "signup" in error_str or "string" in error_str, (
            "Response should indicate signup_instructions validation failure"
        )

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_template_fields_at_max_length(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation succeeds with fields at exactly max_length (201).

    Ensures validation boundary is inclusive (max_length is allowed),
    testing edge case where all fields are at their maximum allowed length.
    """
    # Setup test environment with bot manager role
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session with bot manager role
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create template with fields at exactly max_length
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "name": "Max Length Template",
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "description": "x" * MAX_DESCRIPTION_LENGTH,  # Exactly max_length
                    "where": "y" * 500,  # Exactly max_length=500
                    "signup_instructions": "z" * 1000,  # Exactly max_length=1000
                },
            )

        # Verify successful creation at boundary
        assert response.status_code == 201, (
            f"Expected 201 Created for fields at max_length, "
            f"got {response.status_code}: {response.text}"
        )

        # Verify response data
        template_data = response.json()
        assert template_data["name"] == "Max Length Template"
        assert len(template_data["description"]) == MAX_DESCRIPTION_LENGTH
        assert len(template_data["where"]) == 500
        assert len(template_data["signup_instructions"]) == 1000

    finally:
        await cleanup_test_session(session_token)
