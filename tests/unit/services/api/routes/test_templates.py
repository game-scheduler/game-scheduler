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


"""Unit tests for template endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import HTTPException
from starlette import status

from services.api.routes import templates
from shared.discord.client import DiscordAPIError
from shared.models.template import GameTemplate
from shared.schemas import template as template_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


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
    template.allowed_signup_methods = ["SELF_SIGNUP", "HOST_SELECTED"]
    template.default_signup_method = "SELF_SIGNUP"
    template.archive_delay_seconds = None
    template.archive_channel_id = None
    template.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    template.updated_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    template.channel = channel_config
    return template


class TestBuildTemplateResponse:
    """Test build_template_response helper function."""

    @pytest.mark.asyncio
    async def test_build_template_response_with_all_fields(self, mock_template):
        """Test building response with all template fields populated."""
        mock_discord_client = AsyncMock()

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch:
            mock_fetch.return_value = "test-channel"

            result = await templates.build_template_response(mock_template, mock_discord_client)

        assert result.id == mock_template.id
        assert result.guild_id == mock_template.guild_id
        assert result.name == mock_template.name
        assert result.description == mock_template.description
        assert result.order == mock_template.order
        assert result.is_default == mock_template.is_default
        assert result.channel_id == mock_template.channel_id
        assert result.channel_name == "test-channel"
        assert result.notify_role_ids == mock_template.notify_role_ids
        assert result.allowed_player_role_ids == mock_template.allowed_player_role_ids
        assert result.allowed_host_role_ids == mock_template.allowed_host_role_ids
        assert result.max_players == mock_template.max_players
        assert result.expected_duration_minutes == mock_template.expected_duration_minutes
        assert result.reminder_minutes == mock_template.reminder_minutes
        assert result.where == mock_template.where
        assert result.signup_instructions == mock_template.signup_instructions
        assert result.allowed_signup_methods == mock_template.allowed_signup_methods
        assert result.default_signup_method == mock_template.default_signup_method
        assert result.created_at == "2024-01-01T12:00:00+00:00"
        assert result.updated_at == "2024-01-01T12:00:00+00:00"

        mock_fetch.assert_awaited_once_with(mock_template.channel_id, mock_discord_client)

    @pytest.mark.asyncio
    async def test_build_template_response_with_null_optional_fields(self):
        """Test building response with null optional fields."""
        mock_discord_client = AsyncMock()

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch:
            mock_fetch.return_value = "minimal-channel"

            channel_config = MagicMock()
            channel_config.id = str(uuid.uuid4())
            channel_config.channel_id = "111222333"

            template = MagicMock(spec=GameTemplate)
            template.id = str(uuid.uuid4())
            template.guild_id = str(uuid.uuid4())
            template.name = "Minimal Template"
            template.description = None
            template.order = 0
            template.is_default = False
            template.channel_id = str(uuid.uuid4())
            template.notify_role_ids = None
            template.allowed_player_role_ids = None
            template.allowed_host_role_ids = None
            template.max_players = None
            template.expected_duration_minutes = None
            template.reminder_minutes = None
            template.where = None
            template.signup_instructions = None
            template.allowed_signup_methods = None
            template.default_signup_method = None
            template.archive_delay_seconds = None
            template.archive_channel_id = None
            template.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            template.updated_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            template.channel = channel_config

            result = await templates.build_template_response(template, mock_discord_client)

            assert result.id == template.id
            assert result.name == "Minimal Template"
            assert result.description is None
            assert result.notify_role_ids is None
            assert result.max_players is None
            assert result.channel_name == "minimal-channel"
            mock_fetch.assert_awaited_once_with(template.channel_id, mock_discord_client)

    @pytest.mark.asyncio
    async def test_build_template_response_channel_name_resolution(self, mock_template):
        """Test that channel name is properly resolved via Discord client."""
        mock_discord_client = AsyncMock()

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch:
            mock_fetch.return_value = "resolved-channel"

            result = await templates.build_template_response(mock_template, mock_discord_client)

            assert result.channel_name == "resolved-channel"
            mock_fetch.assert_awaited_once_with(mock_template.channel_id, mock_discord_client)

    @pytest.mark.asyncio
    async def test_build_template_response_includes_archive_fields(self, mock_template):
        """Test that archive fields and channel name are included in response."""
        mock_discord_client = AsyncMock()
        mock_template.archive_delay_seconds = 3600
        mock_template.archive_channel_id = "archive-channel-id"

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch:
            mock_fetch.side_effect = ["primary-channel", "archive-channel"]

            result = await templates.build_template_response(mock_template, mock_discord_client)

        assert result.archive_delay_seconds == 3600
        assert result.archive_channel_id == "archive-channel-id"
        assert result.archive_channel_name == "archive-channel"
        mock_fetch.assert_has_awaits([
            call(mock_template.channel_id, mock_discord_client),
            call(mock_template.archive_channel_id, mock_discord_client),
        ])


class TestListTemplates:
    """Test list_templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test listing templates with role filtering."""
        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch(
                "services.api.dependencies.permissions.check_bot_manager_permission",
                new_callable=AsyncMock,
            ) as mock_check_manager,
        ):
            mock_get_guild.return_value = mock_guild_config
            mock_check_manager.return_value = False

            mock_role_service = AsyncMock()
            mock_get_role_service.return_value = mock_role_service

            mock_discord_client = AsyncMock()
            mock_discord_client.get_guild_channels.return_value = [
                {"id": mock_template.channel.channel_id, "name": "test-channel", "type": 0}
            ]

            mock_service = AsyncMock()
            mock_service.get_templates_for_user.return_value = [mock_template]
            mock_template_service.return_value = mock_service

            result = await templates.list_templates(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert len(result) == 1
            assert result[0].name == "Test Template"
            assert result[0].channel_name == "test-channel"
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_check_manager.assert_awaited_once_with(
                mock_guild_config.guild_id, mock_current_user_unit, mock_role_service, mock_db
            )

    @pytest.mark.asyncio
    async def test_list_templates_includes_archive_fields(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test listing templates includes archive fields."""
        mock_template.archive_delay_seconds = 900
        mock_template.archive_channel_id = "archive-channel-id"

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch(
                "services.api.dependencies.permissions.check_bot_manager_permission"
            ) as mock_check_permission,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_get_role_service.return_value = mock_role_service
            mock_check_permission.return_value = True

            mock_discord_client = AsyncMock()
            mock_discord_client.get_guild_channels.return_value = [
                {"id": mock_template.channel.channel_id, "name": "primary-channel", "type": 0},
                {"id": "archive-channel-id", "name": "archive-channel", "type": 0},
            ]

            mock_service = AsyncMock()
            mock_service.get_templates_for_user.return_value = [mock_template]
            mock_template_service.return_value = mock_service

            result = await templates.list_templates(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert result[0].archive_delay_seconds == 900
            assert result[0].archive_channel_id == "archive-channel-id"
            assert result[0].archive_channel_name == "archive-channel"
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_check_permission.assert_awaited_once_with(
                mock_guild_config.guild_id, mock_current_user_unit, mock_role_service, mock_db
            )

    @pytest.mark.asyncio
    async def test_list_templates_maintainer_sees_all(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Maintainer bypasses role filtering and sees all templates."""
        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch(
                "services.api.dependencies.permissions.check_bot_manager_permission",
                new_callable=AsyncMock,
            ) as mock_check_manager,
        ):
            mock_get_guild.return_value = mock_guild_config
            mock_check_manager.return_value = True

            mock_role_service = AsyncMock()
            mock_get_role_service.return_value = mock_role_service

            mock_discord_client = AsyncMock()

            mock_service = AsyncMock()
            mock_service.get_templates_for_user.return_value = [mock_template]
            mock_template_service.return_value = mock_service

            result = await templates.list_templates(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert len(result) == 1
            mock_service.get_templates_for_user.assert_awaited_once()
            _, kwargs = mock_service.get_templates_for_user.call_args
            assert kwargs.get("is_manager") is True
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_check_manager.assert_awaited_once_with(
                mock_guild_config.guild_id, mock_current_user_unit, mock_role_service, mock_db
            )

    @pytest.mark.asyncio
    async def test_list_templates_discord_api_error_falls_back_to_unknown(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test that a Discord API error falls back to 'Unknown Channel' names."""

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch(
                "services.api.dependencies.permissions.check_bot_manager_permission",
                new_callable=AsyncMock,
            ) as mock_check_manager,
        ):
            mock_get_guild.return_value = mock_guild_config
            mock_check_manager.return_value = False
            mock_get_role_service.return_value = AsyncMock()

            mock_discord_client = AsyncMock()
            mock_discord_client.get_guild_channels.side_effect = DiscordAPIError(
                403, "Missing Access"
            )

            mock_service = AsyncMock()
            mock_service.get_templates_for_user.return_value = [mock_template]
            mock_template_service.return_value = mock_service

            result = await templates.list_templates(
                guild_id=mock_guild_config.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert len(result) == 1
            assert result[0].channel_name == "Unknown Channel"
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_check_manager.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_templates_guild_not_found(self, mock_db, mock_current_user_unit):
        """Test listing templates when guild not found."""
        with patch("services.api.database.queries.require_guild_by_id") as mock_get_guild:
            mock_get_guild.side_effect = HTTPException(
                status_code=404, detail="Guild configuration not found"
            )

            mock_discord_client = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await templates.list_templates(
                    guild_id="nonexistent",
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=mock_discord_client,
                )

            assert exc_info.value.status_code == 404
            mock_get_guild.assert_awaited_once_with(
                mock_db, "nonexistent", mock_current_user_unit.user.discord_id
            )


class TestGetTemplate:
    """Test get_template endpoint."""

    @pytest.mark.asyncio
    async def test_get_template_success(
        self, mock_db, mock_current_user_unit, mock_template, mock_channel_config
    ):
        """Test getting template by ID."""
        with (
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch,
            patch(
                "services.api.dependencies.permissions.verify_template_access"
            ) as mock_verify_access,
        ):
            mock_service = AsyncMock()
            mock_service.get_template_by_id.return_value = mock_template
            mock_template_service.return_value = mock_service

            mock_discord_client = AsyncMock()
            mock_fetch.return_value = "test-channel"
            mock_verify_access.return_value = mock_template

            result = await templates.get_template(
                template_id=mock_template.id,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert result.id == mock_template.id
            assert result.name == "Test Template"
            assert result.channel_name == "test-channel"
            mock_template_service.assert_called_once_with(mock_db)
            mock_verify_access.assert_awaited_once_with(
                mock_template, mock_current_user_unit.user.discord_id, mock_db
            )
            mock_fetch.assert_awaited_once_with(mock_template.channel_id, mock_discord_client)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, mock_db, mock_current_user_unit):
        """Test getting nonexistent template."""
        with patch(
            "services.api.services.template_service.TemplateService"
        ) as mock_template_service:
            mock_service = AsyncMock()
            mock_service.get_template_by_id.return_value = None
            mock_template_service.return_value = mock_service

            mock_discord_client = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await templates.get_template(
                    template_id="nonexistent",
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=mock_discord_client,
                )

            assert exc_info.value.status_code == 404
            mock_template_service.assert_called_once_with(mock_db)


class TestCreateTemplate:
    """Test create_template endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_success(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
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
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch,
            patch(
                "services.api.dependencies.permissions.require_bot_manager"
            ) as mock_require_manager,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = True
            mock_get_role_service.return_value = mock_role_service
            mock_require_manager.return_value = mock_current_user_unit

            mock_service = AsyncMock()
            mock_service.create_template.return_value = mock_template
            mock_template_service.return_value = mock_service

            mock_discord_client = AsyncMock()
            mock_fetch.return_value = "test-channel"

            result = await templates.create_template(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=mock_discord_client,
            )

            assert result.name == "Test Template"
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_require_manager.assert_awaited_once_with(
                mock_guild_config.id, mock_current_user_unit, mock_role_service, mock_db
            )
            mock_fetch.assert_awaited_once_with(mock_template.channel_id, mock_discord_client)

    @pytest.mark.asyncio
    async def test_create_template_passes_archive_fields(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test create_template passes archive fields to the service layer."""
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
            archive_delay_seconds=300,
            archive_channel_id="archive-channel-id",
        )

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch,
            patch(
                "services.api.dependencies.permissions.require_bot_manager"
            ) as mock_require_manager,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = True
            mock_get_role_service.return_value = mock_role_service
            mock_require_manager.return_value = mock_current_user_unit

            mock_service = AsyncMock()
            mock_service.create_template.return_value = mock_template
            mock_template_service.return_value = mock_service

            mock_fetch.return_value = "test-channel"

            await templates.create_template(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=AsyncMock(),
            )

            mock_service.create_template.assert_awaited_once_with(
                guild_id=mock_guild_config.id,
                channel_id=mock_template.channel_id,
                name="New Template",
                description="New description",
                order=1,
                is_default=False,
                notify_role_ids=["role1"],
                allowed_player_role_ids=None,
                allowed_host_role_ids=None,
                max_players=10,
                expected_duration_minutes=180,
                reminder_minutes=[60, 15],
                where="Online",
                signup_instructions="Join us",
                archive_delay_seconds=300,
                archive_channel_id="archive-channel-id",
                allowed_signup_methods=None,
                default_signup_method=None,
                signup_priority_role_ids=None,
            )
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_require_manager.assert_awaited_once_with(
                mock_guild_config.id, mock_current_user_unit, mock_role_service, mock_db
            )
            mock_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_template_passes_signup_priority_fields(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test create_template forwards signup_priority_role_ids and signup method fields."""
        request = template_schemas.TemplateCreateRequest(
            guild_id=mock_guild_config.id,
            name="Priority Template",
            channel_id=mock_template.channel_id,
            signup_priority_role_ids=["111", "222"],
            allowed_signup_methods=["SELF_SIGNUP"],
            default_signup_method="SELF_SIGNUP",
        )

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("shared.discord.client.fetch_channel_name_safe", return_value="test-channel"),
            patch("services.api.dependencies.permissions.require_bot_manager"),
        ):
            mock_get_guild.return_value = mock_guild_config
            mock_role_service = AsyncMock()
            mock_get_role_service.return_value = mock_role_service
            mock_service = AsyncMock()
            mock_service.create_template.return_value = mock_template
            mock_template_service.return_value = mock_service

            await templates.create_template(
                guild_id=mock_guild_config.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=AsyncMock(),
            )

            call_kwargs = mock_service.create_template.call_args.kwargs
            assert call_kwargs["signup_priority_role_ids"] == ["111", "222"]
            assert call_kwargs["allowed_signup_methods"] == ["SELF_SIGNUP"]
            assert call_kwargs["default_signup_method"] == "SELF_SIGNUP"
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    async def test_create_template_unauthorized(
        self, mock_db, mock_current_user_unit, mock_guild_config
    ):
        """Test creating template without bot manager role."""
        request = template_schemas.TemplateCreateRequest(
            guild_id=mock_guild_config.id,
            name="New Template",
            channel_id=str(uuid.uuid4()),
        )

        with (
            patch("services.api.database.queries.require_guild_by_id") as mock_get_guild,
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.dependencies.permissions.require_bot_manager"
            ) as mock_require_manager,
        ):
            mock_get_guild.return_value = mock_guild_config

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = False
            mock_get_role_service.return_value = mock_role_service
            mock_require_manager.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )

            mock_discord_client = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await templates.create_template(
                    guild_id=mock_guild_config.id,
                    request=request,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                    discord_client=mock_discord_client,
                )

            assert exc_info.value.status_code == 403
            mock_get_guild.assert_awaited_once_with(
                mock_db, mock_guild_config.id, mock_current_user_unit.user.discord_id
            )
            mock_get_role_service.assert_called_once_with()
            mock_require_manager.assert_awaited_once_with(
                mock_guild_config.id, mock_current_user_unit, mock_role_service, mock_db
            )


class TestUpdateTemplate:
    """Test update_template endpoint."""

    @pytest.mark.asyncio
    async def test_update_template_passes_archive_fields(
        self, mock_db, mock_current_user_unit, mock_template
    ):
        """Test update_template forwards archive fields to service layer."""
        request = template_schemas.TemplateUpdateRequest(
            archive_delay_seconds=0,
            archive_channel_id=None,
        )

        with (
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch,
            patch(
                "services.api.dependencies.permissions.require_bot_manager"
            ) as mock_require_manager,
        ):
            mock_role_service = AsyncMock()
            mock_get_role_service.return_value = mock_role_service
            mock_require_manager.return_value = mock_current_user_unit

            updated_template = MagicMock(spec=GameTemplate)
            updated_template.id = mock_template.id
            updated_template.guild_id = mock_template.guild_id
            updated_template.name = mock_template.name
            updated_template.description = mock_template.description
            updated_template.order = mock_template.order
            updated_template.is_default = mock_template.is_default
            updated_template.channel_id = mock_template.channel_id
            updated_template.notify_role_ids = mock_template.notify_role_ids
            updated_template.allowed_player_role_ids = mock_template.allowed_player_role_ids
            updated_template.allowed_host_role_ids = mock_template.allowed_host_role_ids
            updated_template.max_players = mock_template.max_players
            updated_template.expected_duration_minutes = mock_template.expected_duration_minutes
            updated_template.reminder_minutes = mock_template.reminder_minutes
            updated_template.where = mock_template.where
            updated_template.signup_instructions = mock_template.signup_instructions
            updated_template.allowed_signup_methods = mock_template.allowed_signup_methods
            updated_template.default_signup_method = mock_template.default_signup_method
            updated_template.archive_delay_seconds = 0
            updated_template.archive_channel_id = None
            updated_template.created_at = mock_template.created_at
            updated_template.updated_at = mock_template.updated_at

            mock_service = AsyncMock()
            mock_service.get_template_by_id.return_value = mock_template
            mock_service.update_template.return_value = updated_template
            mock_template_service.return_value = mock_service

            mock_fetch.return_value = "test-channel"

            await templates.update_template(
                template_id=mock_template.id,
                request=request,
                current_user=mock_current_user_unit,
                db=mock_db,
                discord_client=AsyncMock(),
            )

            mock_service.update_template.assert_awaited_once_with(
                mock_template,
                archive_delay_seconds=0,
                archive_channel_id=None,
            )
            mock_get_role_service.assert_called_once_with()
            mock_template_service.assert_called_once_with(mock_db)
            mock_require_manager.assert_awaited_once_with(
                mock_template.guild_id, mock_current_user_unit, mock_role_service, mock_db
            )
            mock_fetch.assert_awaited_once()


class TestDeleteTemplate:
    """Test delete_template endpoint."""

    @pytest.mark.asyncio
    async def test_delete_default_template_fails(
        self, mock_db, mock_current_user_unit, mock_guild_config, mock_template
    ):
        """Test that deleting default template is prevented."""
        mock_template.is_default = True

        with (
            patch(
                "services.api.services.template_service.TemplateService"
            ) as mock_template_service,
            patch("services.api.database.queries.require_guild_by_id"),
            patch("services.api.auth.roles.get_role_service") as mock_get_role_service,
            patch(
                "services.api.dependencies.permissions.require_bot_manager"
            ) as mock_require_manager,
        ):
            mock_template_svc = AsyncMock()
            mock_template_svc.get_template_by_id.return_value = mock_template
            mock_template_service.return_value = mock_template_svc

            mock_role_service = AsyncMock()
            mock_role_service.check_bot_manager_permission.return_value = True
            mock_get_role_service.return_value = mock_role_service
            mock_require_manager.return_value = mock_current_user_unit

            with pytest.raises(HTTPException) as exc_info:
                await templates.delete_template(
                    template_id=mock_template.id,
                    current_user=mock_current_user_unit,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "default" in str(exc_info.value.detail).lower()
            mock_template_service.assert_called_once_with(mock_db)
            mock_get_role_service.assert_called_once_with()
            mock_require_manager.assert_awaited_once_with(
                mock_template.guild_id, mock_current_user_unit, mock_role_service, mock_db
            )
