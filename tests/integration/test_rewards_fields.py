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


"""Integration tests for rewards fields and Save and Archive flow."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "334455667788990011"


async def _setup_context(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
) -> dict:
    """Create guild/channel/user/template and seed Redis for rewards tests."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    return {
        "guild_id": guild["id"],
        "channel_id": channel["id"],
        "template_id": template["id"],
    }


async def _create_game(client: httpx.AsyncClient, template_id: str, **extra) -> dict:
    """Create a game via API and return the response body."""
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    payload = {
        "template_id": template_id,
        "title": "INT_TEST Rewards Game",
        "scheduled_at": scheduled_at,
        **extra,
    }
    response = await client.post("/api/v1/games", data=payload)
    assert response.status_code == 201, f"Game creation failed: {response.text}"
    return response.json()


# ============================================================================
# rewards field persistence
# ============================================================================


@pytest.mark.asyncio
async def test_rewards_field_persists_through_game_update(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a game with rewards returns the new value in the response."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            assert game.get("rewards") is None

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"rewards": "a bag of gold coins"},
            )
            assert response.status_code == 200, response.text
            assert response.json()["rewards"] == "a bag of gold coins"

            fetch_response = await client.get(f"/api/v1/games/{game_id}")
            assert fetch_response.status_code == 200, fetch_response.text
            assert fetch_response.json()["rewards"] == "a bag of gold coins"
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# remind_host_rewards propagates from template to game
# ============================================================================


@pytest.mark.asyncio
async def test_remind_host_rewards_propagates_from_template_to_game(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Creating a game from a template copies remind_host_rewards to the game."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    admin_db_sync.execute(
        text("UPDATE game_templates SET remind_host_rewards = true WHERE id = :template_id"),
        {"template_id": template["id"]},
    )
    admin_db_sync.commit()

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, template["id"])

        row = admin_db_sync.execute(
            text("SELECT remind_host_rewards FROM game_sessions WHERE id = :id"),
            {"id": game["id"]},
        ).fetchone()
        assert row is not None
        assert row[0] is True, "remind_host_rewards should be True on new game from template"
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# clone behavior
# ============================================================================


@pytest.mark.asyncio
async def test_clone_game_does_not_copy_rewards(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Cloning a game with rewards set results in a clone with rewards = NULL."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text("UPDATE game_sessions SET rewards = 'gold coins' WHERE id = :id"),
                {"id": game_id},
            )
            admin_db_sync.commit()

            clone_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
            clone_response = await client.post(
                f"/api/v1/games/{game_id}/clone",
                json={
                    "scheduled_at": clone_at,
                    "player_carryover": "NO",
                    "waitlist_carryover": "NO",
                },
            )
            assert clone_response.status_code == 201, clone_response.text
            clone_id = clone_response.json()["id"]

        row = admin_db_sync.execute(
            text("SELECT rewards FROM game_sessions WHERE id = :id"),
            {"id": clone_id},
        ).fetchone()
        assert row is not None
        assert row[0] is None, "Cloned game should have rewards = NULL"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_clone_game_copies_remind_host_rewards(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Cloning a game preserves remind_host_rewards on the new game."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text("UPDATE game_sessions SET remind_host_rewards = true WHERE id = :id"),
                {"id": game_id},
            )
            admin_db_sync.commit()

            clone_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
            clone_response = await client.post(
                f"/api/v1/games/{game_id}/clone",
                json={
                    "scheduled_at": clone_at,
                    "player_carryover": "NO",
                    "waitlist_carryover": "NO",
                },
            )
            assert clone_response.status_code == 201, clone_response.text
            clone_id = clone_response.json()["id"]

        row = admin_db_sync.execute(
            text("SELECT remind_host_rewards FROM game_sessions WHERE id = :id"),
            {"id": clone_id},
        ).fetchone()
        assert row is not None
        assert row[0] is True, "Cloned game should inherit remind_host_rewards = True"
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# Save and Archive — status schedule creation/update
# ============================================================================


@pytest.mark.asyncio
async def test_save_and_archive_creates_archived_schedule(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a COMPLETED game with archive_delay_seconds=1 creates an ARCHIVED schedule."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            before = datetime.now(UTC).replace(tzinfo=None)

            admin_db_sync.execute(
                text(
                    "UPDATE game_sessions "
                    "SET status = 'COMPLETED', archive_channel_id = :channel_id "
                    "WHERE id = :id"
                ),
                {"id": game_id, "channel_id": ctx["channel_id"]},
            )
            admin_db_sync.commit()

            existing = admin_db_sync.execute(
                text(
                    "SELECT id FROM game_status_schedule "
                    "WHERE game_id = :game_id AND target_status = 'ARCHIVED'"
                ),
                {"game_id": game_id},
            ).fetchone()
            assert existing is None, "No ARCHIVED schedule should exist before update"

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"archive_delay_seconds": "1"},
            )
            assert response.status_code == 200, response.text

        after = datetime.now(UTC).replace(tzinfo=None)

        row = admin_db_sync.execute(
            text(
                "SELECT transition_time FROM game_status_schedule "
                "WHERE game_id = :game_id AND target_status = 'ARCHIVED'"
            ),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "ARCHIVED schedule should be created after update"

        transition_time = row[0]
        if hasattr(transition_time, "tzinfo") and transition_time.tzinfo is not None:
            transition_time = transition_time.replace(tzinfo=None)
        assert before <= transition_time <= after + timedelta(seconds=5), (
            f"Transition time {transition_time} should be ~now+1s"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_save_and_archive_updates_existing_archived_schedule(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a COMPLETED game with archive_delay_seconds=1 replaces a far-future schedule."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text(
                    "UPDATE game_sessions "
                    "SET status = 'COMPLETED', archive_delay_seconds = 86400, "
                    "archive_channel_id = :channel_id "
                    "WHERE id = :id"
                ),
                {"id": game_id, "channel_id": ctx["channel_id"]},
            )
            admin_db_sync.commit()

            far_future = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24)
            old_schedule_id = str(uuid.uuid4())
            admin_db_sync.execute(
                text(
                    "INSERT INTO game_status_schedule "
                    "(id, game_id, target_status, transition_time, executed) "
                    "VALUES (:id, :game_id, 'ARCHIVED', :transition_time, false)"
                ),
                {
                    "id": old_schedule_id,
                    "game_id": game_id,
                    "transition_time": far_future,
                },
            )
            admin_db_sync.commit()

            before = datetime.now(UTC).replace(tzinfo=None)

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"archive_delay_seconds": "1"},
            )
            assert response.status_code == 200, response.text

        after = datetime.now(UTC).replace(tzinfo=None)

        row = admin_db_sync.execute(
            text(
                "SELECT transition_time FROM game_status_schedule "
                "WHERE game_id = :game_id AND target_status = 'ARCHIVED' AND executed = false"
            ),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "ARCHIVED schedule should still exist after update"

        transition_time = row[0]
        if hasattr(transition_time, "tzinfo") and transition_time.tzinfo is not None:
            transition_time = transition_time.replace(tzinfo=None)
        assert transition_time <= after + timedelta(seconds=5), (
            f"Schedule should have been updated to ~now+1s, got {transition_time}"
        )
        assert transition_time >= before - timedelta(seconds=1), (
            f"Schedule should not be in the past: {transition_time}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_archive_delay_seconds_not_in_game_update_for_non_archive_case(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a COMPLETED game without archive_delay_seconds preserves any existing schedule."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text("UPDATE game_sessions SET status = 'COMPLETED' WHERE id = :id"),
                {"id": game_id},
            )
            admin_db_sync.commit()

            original_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
            schedule_id = str(uuid.uuid4())
            admin_db_sync.execute(
                text(
                    "INSERT INTO game_status_schedule "
                    "(id, game_id, target_status, transition_time, executed) "
                    "VALUES (:id, :game_id, 'ARCHIVED', :transition_time, false)"
                ),
                {
                    "id": schedule_id,
                    "game_id": game_id,
                    "transition_time": original_time,
                },
            )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"rewards": "some loot"},
            )
            assert response.status_code == 200, response.text

        row = admin_db_sync.execute(
            text(
                "SELECT transition_time FROM game_status_schedule "
                "WHERE game_id = :game_id AND target_status = 'ARCHIVED'"
            ),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "Existing ARCHIVED schedule should be preserved"

        transition_time = row[0]
        if hasattr(transition_time, "tzinfo") and transition_time.tzinfo is not None:
            transition_time = transition_time.replace(tzinfo=None)
        assert abs((transition_time - original_time).total_seconds()) < 1, (
            "Existing ARCHIVED schedule should not be modified"
        )
    finally:
        await cleanup_test_session(session_token)
