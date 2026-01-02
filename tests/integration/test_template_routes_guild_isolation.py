# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Integration tests for template routes guild isolation via RLS.

These tests verify that template route handlers properly filter results
to only templates from the user's guilds when guild context is set.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from services.api.routes.templates import get_template, list_templates
from shared.data_access.guild_isolation import set_current_guild_ids
from shared.schemas.auth import CurrentUser

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_current_user_guild_a(user_a):
    """Mock CurrentUser for guild A user."""
    return CurrentUser(
        user=user_a,
        access_token="mock_access_token_guild_a",
        session_token="mock_session_token_guild_a",
    )


@pytest.fixture
def mock_current_user_guild_b(user_b):
    """Mock CurrentUser for guild B user."""
    return CurrentUser(
        user=user_b,
        access_token="mock_access_token_guild_b",
        session_token="mock_session_token_guild_b",
    )


@pytest.fixture
def mock_guilds_guild_a(guild_a_config):
    """Mock user guilds for guild A user (only has access to Guild A)."""
    return [
        {
            "id": guild_a_config.guild_id,
            "name": "Test Guild A",
            "permissions": "8",
        }
    ]


@pytest.fixture
def mock_guilds_guild_b(guild_b_config):
    """Mock user guilds for guild B user (only has access to Guild B)."""
    return [
        {
            "id": guild_b_config.guild_id,
            "name": "Test Guild B",
            "permissions": "8",
        }
    ]


@pytest.mark.asyncio
async def test_list_templates_only_returns_user_guild_templates(
    db,
    redis_client,
    guild_a_id,
    guild_a_config,
    guild_b_id,
    template_a,
    template_b,
    mock_current_user_guild_a,
    mock_guilds_guild_a,
):
    """list_templates only returns templates from user's guilds."""
    from tests.integration.conftest import seed_user_guilds_cache

    await seed_user_guilds_cache(
        redis_client, mock_current_user_guild_a.user.discord_id, [guild_a_id]
    )

    # Set guild context to simulate get_db_with_user_guilds behavior
    set_current_guild_ids([guild_a_id])

    try:
        # Mock Discord client channel name lookup
        with patch("shared.discord.client.fetch_channel_name_safe", return_value="test-channel"):
            # Mock role service to bypass permission checks
            with patch(
                "services.api.routes.templates.roles_module.get_role_service"
            ) as mock_role_service:
                mock_svc = AsyncMock()
                mock_svc.check_bot_manager_permission.return_value = True
                mock_role_service.return_value = mock_svc

                templates = await list_templates(
                    guild_id=guild_a_id,
                    current_user=mock_current_user_guild_a,
                    db=db,
                )

                # Only Guild A template visible (Guild B filtered by RLS)
                # Note: This test will pass with current code (no RLS yet) because
                # list_templates already filters by guild_id in query
                assert len(templates) >= 1
                template_ids = [t.id for t in templates]
                assert template_a.id in template_ids
                assert template_b.id not in template_ids
    finally:
        from shared.data_access.guild_isolation import clear_current_guild_ids

        clear_current_guild_ids()


@pytest.mark.asyncio
@pytest.mark.xfail(reason="RLS not enabled yet - template visible across guilds until Phase 3")
async def test_get_template_returns_404_for_other_guild_template(
    db,
    redis_client,
    guild_a_id,
    guild_b_id,
    template_b,
    mock_current_user_guild_a,
    mock_guilds_guild_a,
):
    """get_template raises 404 for template from different guild (after RLS enabled)."""
    from tests.integration.conftest import seed_user_guilds_cache

    await seed_user_guilds_cache(
        redis_client, mock_current_user_guild_a.user.discord_id, [guild_a_id]
    )

    # Set guild context to simulate get_db_with_user_guilds behavior
    set_current_guild_ids([guild_a_id])

    try:
        # Mock Discord client channel name lookup
        with patch("shared.discord.client.fetch_channel_name_safe", return_value="test-channel"):
            # Mock verify_template_access to pass permission check
            with patch(
                "services.api.dependencies.permissions.verify_template_access",
                return_value=template_b,
            ):
                # Attempting to access Guild B template should raise 404
                # Note: This test is marked xfail because RLS is not enabled yet.
                # Currently get_template can fetch any template by ID.
                # After RLS is enabled in Phase 3, the database query will return None
                # for templates outside the user's guilds, triggering the 404.
                with pytest.raises(HTTPException) as exc_info:
                    await get_template(
                        template_id=template_b.id,
                        current_user=mock_current_user_guild_a,
                        db=db,
                    )

                # RLS filters template, route returns 404
                assert exc_info.value.status_code == 404
    finally:
        from shared.data_access.guild_isolation import clear_current_guild_ids

        clear_current_guild_ids()


@pytest.mark.asyncio
async def test_list_templates_with_no_guild_context_returns_all(
    db,
    template_a,
    template_b,
    guild_a_id,
    mock_current_user_guild_a,
):
    """list_templates without guild context sees all templates (no RLS filtering)."""
    # Do NOT set guild context (simulating service operations without RLS)

    # Mock Discord client channel name lookup
    with patch("shared.discord.client.fetch_channel_name_safe", return_value="test-channel"):
        # Mock role service to return admin permission
        with patch(
            "services.api.routes.templates.roles_module.get_role_service"
        ) as mock_role_service:
            mock_svc = AsyncMock()
            mock_svc.check_bot_manager_permission.return_value = True
            mock_role_service.return_value = mock_svc

            # This should see all templates for guild_a since guild_id is passed
            # (route already filters by guild_id, RLS provides additional safety)
            templates = await list_templates(
                guild_id=guild_a_id,
                current_user=mock_current_user_guild_a,
                db=db,
            )

            # Should only see guild_a templates (route filters by guild_id parameter)
            template_ids = [t.id for t in templates]
            assert template_a.id in template_ids
