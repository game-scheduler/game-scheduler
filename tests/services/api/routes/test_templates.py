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


"""Unit tests for template endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.api.routes import templates
from shared.models.template import GameTemplate
from shared.schemas import auth as auth_schemas
from shared.schemas import template as template_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    mock_user = MagicMock()
    mock_user.discord_id = "123456789"
    return auth_schemas.CurrentUser(
        user=mock_user,
        user_id="user-uuid",
        access_token="test_access_token",
        session_token="test-session-token",
    )


@pytest.fixture
def mock_guild_config():
    """Create mock guild configuration."""
    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.guild_id = "987654321"
    config.bot_manager_role_ids = ["role1", "role2"]
    return config


@pytest.fixture
def mock_channel_config():
    """Create mock channel configuration."""
    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.channel_id = "111222333"
    return config


@pytest.fixture
def mock_template():
    """Create mock template."""
    channel_config = MagicMock()
    channel_config.id = str(uuid.uuid4())
    channel_config.channel_id = "111222333"

    template = MagicMock(spec=GameTemplate)
    template.id = str(uuid.uuid4())
    template.guild_id = str(uuid.uuid4())
    template.name = "Test Template"
    template.description = "Test description"
    template.order = 0
    template.is_default = False
    template.channel_id = str(uuid.uuid4())
    template.notify_role_ids = ["role1"]
    template.allowed_player_role_ids = None
    template.allowed_host_role_ids = None
    template.max_players = 10
    template.expected_duration_minutes = 180
    template.reminder_minutes = [60, 15]
    template.where = "Online"
    template.signup_instructions = "Just join!"
    template.created_at = datetime(2024, 1, 1, 12, 0, 0)
    template.updated_at = datetime(2024, 1, 1, 12, 0, 0)
    template.channel = channel_config
    return template


class TestListTemplates:
    """Test list_templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_success(
        self, mock_db, mock_current_user, mock_guild_config, mock_template
    ):
        """Test listing templates with role filtering."""
        with (
            patch("services.api.database.queries.get_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch("services.api.auth.discord_client.get_discord_client") as mock_get_discord_client,
            patch("services.api.auth.discord_client.fetch_channel_name_safe") as mock_fetch_name,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.has_permissions.return_value = True
            mock_get_role_service.return_value = mock_role_service

            mock_discord_client = AsyncMock()
            mock_discord_client.get_guild_member.return_value = {"roles": ["role1", "role2"]}
            mock_get_discord_client.return_value = mock_discord_client

            mock_fetch_name.return_value = "test-channel"

            mock_service = AsyncMock()
            mock_service.get_templates_for_user.return_value = [mock_template]
            mock_template_service.return_value = mock_service

            result = await templates.list_templates(
                guild_id=mock_guild_config.id, current_user=mock_current_user, db=mock_db
            )

            assert len(result) == 1
            assert result[0].name == "Test Template"
            assert result[0].channel_name == "test-channel"

    @pytest.mark.asyncio
    async def test_list_templates_guild_not_found(self, mock_db, mock_current_user):
        """Test listing templates when guild not found."""
        with patch("services.api.database.queries.get_guild_by_id") as mock_get_guild:
            mock_get_guild.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await templates.list_templates(
                    guild_id="nonexistent", current_user=mock_current_user, db=mock_db
                )

            assert exc_info.value.status_code == 404


class TestGetTemplate:
    """Test get_template endpoint."""

    @pytest.mark.asyncio
    async def test_get_template_success(
        self, mock_db, mock_current_user, mock_template, mock_channel_config
    ):
        """Test getting template by ID."""
        with (
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("services.api.auth.discord_client.fetch_channel_name_safe") as mock_fetch_name,
        ):
            mock_service = AsyncMock()
            mock_service.get_template_by_id.return_value = mock_template
            mock_template_service.return_value = mock_service

            mock_fetch_name.return_value = "test-channel"

            result = await templates.get_template(
                template_id=mock_template.id, current_user=mock_current_user, db=mock_db
            )

            assert result.id == mock_template.id
            assert result.name == "Test Template"
            assert result.channel_name == "test-channel"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, mock_db, mock_current_user):
        """Test getting nonexistent template."""
        with patch(
            "services.api.services.template_service.TemplateService"
        ) as mock_template_service:
            mock_service = AsyncMock()
            mock_service.get_template_by_id.return_value = None
            mock_template_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await templates.get_template(
                    template_id="nonexistent", current_user=mock_current_user, db=mock_db
                )

            assert exc_info.value.status_code == 404


class TestCreateTemplate:
    """Test create_template endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_success(
        self, mock_db, mock_current_user, mock_guild_config, mock_template
    ):
        """Test creating template with bot manager role."""
        request = template_schemas.TemplateCreateRequest(
            guild_id=mock_guild_config.id,
            name="New Template",
            description="New description",
            order=1,
            is_default=False,
            channel_id=mock_template.channel_id,
            notify_role_ids=["role1"],
            allowed_player_role_ids=None,
            allowed_host_role_ids=None,
            max_players=10,
            expected_duration_minutes=180,
            reminder_minutes=[60, 15],
            where="Online",
            signup_instructions="Join us",
        )

        with (
            patch("services.api.database.queries.get_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("services.api.auth.discord_client.fetch_channel_name_safe") as mock_fetch_name,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = True
            mock_get_role_service.return_value = mock_role_service

            mock_service = AsyncMock()
            mock_service.create_template.return_value = mock_template
            mock_template_service.return_value = mock_service

            mock_fetch_name.return_value = "test-channel"

            result = await templates.create_template(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user,
                db=mock_db,
            )

            assert result.name == "Test Template"

    @pytest.mark.asyncio
    async def test_create_template_unauthorized(
        self, mock_db, mock_current_user, mock_guild_config
    ):
        """Test creating template without bot manager role."""
        request = template_schemas.TemplateCreateRequest(
            guild_id=mock_guild_config.id,
            name="New Template",
            channel_id=str(uuid.uuid4()),
        )

        with (
            patch("services.api.database.queries.get_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = False
            mock_get_role_service.return_value = mock_role_service

            with pytest.raises(HTTPException) as exc_info:
                await templates.create_template(
                    guild_id=mock_guild_config.id,
                    request=request,
                    current_user=mock_current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403


class TestDeleteTemplate:
    """Test delete_template endpoint."""

    @pytest.mark.asyncio
    async def test_delete_default_template_fails(
        self, mock_db, mock_current_user, mock_guild_config, mock_template
    ):
        """Test that deleting default template is prevented."""
        mock_template.is_default = True

        with (
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("services.api.database.queries.get_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
        ):
            mock_template_svc = AsyncMock()
            mock_template_svc.get_template.return_value = mock_template
            mock_template_service.return_value = mock_template_svc

            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = True
            mock_get_role_service.return_value = mock_role_service

            with pytest.raises(HTTPException) as exc_info:
                await templates.delete_template(
                    template_id=mock_template.id, current_user=mock_current_user, db=mock_db
                )

            assert exc_info.value.status_code == 400
            assert "default" in str(exc_info.value.detail).lower()
