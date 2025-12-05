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


"""Unit tests for permission check dependencies."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from services.api.auth import roles as roles_module
from services.api.dependencies import permissions
from shared.schemas import auth as auth_schemas


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    return auth_schemas.CurrentUser(
        user=mock_user, access_token="test_token", session_token="test-session-token"
    )


@pytest.fixture
def mock_role_service():
    """Create mock role verification service."""
    service = AsyncMock()
    service.has_permissions = AsyncMock()
    service.check_game_host_permission = AsyncMock()
    return service


@pytest.fixture
def mock_tokens():
    """Mock token functions."""
    return {
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_at": 9999999999,
    }


@pytest.mark.asyncio
async def test_get_role_service():
    """Test getting role service."""
    service = await permissions.get_role_service()
    assert isinstance(service, roles_module.RoleVerificationService)


@pytest.mark.asyncio
async def test_require_manage_guild_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_manage_guild with permission."""
    mock_role_service.has_permissions.return_value = True
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        # Use a Discord snowflake format ID to skip UUID resolution
        result = await permissions.require_manage_guild(
            "123456789012345678",  # Discord snowflake format
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.has_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_require_manage_guild_no_session(mock_current_user, mock_role_service):
    """Test require_manage_guild with no session."""
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_guild(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_manage_guild_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_manage_guild without permission."""
    mock_role_service.has_permissions.return_value = False
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_guild(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "MANAGE_GUILD" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_manage_channels_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_manage_channels with permission."""
    mock_role_service.has_permissions.return_value = True
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        # Use a Discord snowflake format ID to skip UUID resolution
        result = await permissions.require_manage_channels(
            "123456789012345678",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.has_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_require_manage_channels_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_manage_channels without permission."""
    mock_role_service.has_permissions.return_value = False
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_channels(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "MANAGE_CHANNELS" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_game_host_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host with permission."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_game_host(
            "guild456",
            "channel789",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.check_game_host_permission.assert_called_once_with(
        "user123",
        "guild456",
        mock_db,
        channel_id="channel789",
        access_token="test_token",
    )


@pytest.mark.asyncio
async def test_require_game_host_no_permission(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host without permission."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_game_host(
                "guild456",
                "channel789",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "host games" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_game_host_no_channel(mock_current_user, mock_role_service, mock_tokens):
    """Test require_game_host without channel ID."""
    mock_db = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_game_host(
            "guild456",
            None,
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.check_game_host_permission.assert_called_once_with(
        "user123",
        "guild456",
        mock_db,
        channel_id=None,
        access_token="test_token",
    )


@pytest.mark.asyncio
async def test_require_administrator_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_administrator with permission."""
    mock_role_service.has_permissions.return_value = True

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_administrator(
            "guild456",
            mock_current_user,
            mock_role_service,
        )

    assert result == mock_current_user
    mock_role_service.has_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_require_administrator_no_permission(
    mock_current_user, mock_role_service, mock_tokens
):
    """Test require_administrator without permission."""
    mock_role_service.has_permissions.return_value = False

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_administrator(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 403
    assert "ADMINISTRATOR" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_bot_manager_success(mock_current_user, mock_role_service, mock_tokens):
    """Test require_bot_manager with permission."""
    mock_role_service.check_bot_manager_permission.return_value = True
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        result = await permissions.require_bot_manager(
            "123456789012345678",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result == mock_current_user
    mock_role_service.check_bot_manager_permission.assert_called_once()


@pytest.mark.asyncio
async def test_require_bot_manager_no_permission(mock_current_user, mock_role_service, mock_tokens):
    """Test require_bot_manager without permission."""
    mock_role_service.check_bot_manager_permission.return_value = False
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_bot_manager(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 403
    assert "Bot manager role required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_guild_membership_success():
    """Test verify_guild_membership with member returns guilds."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_user.session_token = "session123"

    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_db = AsyncMock()
    user_guilds = [{"id": "guild123"}, {"id": "guild456"}]

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value={"access_token": "token"}),
        patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds),
    ):
        result = await permissions.verify_guild_membership("guild123", mock_current_user, mock_db)

    assert result == user_guilds


@pytest.mark.asyncio
async def test_verify_guild_membership_not_member():
    """Test verify_guild_membership with non-member raises 404."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_user.session_token = "session123"

    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_db = AsyncMock()
    user_guilds = [{"id": "guild456"}, {"id": "guild789"}]

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value={"access_token": "token"}),
        patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds),
        pytest.raises(HTTPException) as exc_info,
    ):
        await permissions.verify_guild_membership("guild123", mock_current_user, mock_db)

    assert exc_info.value.status_code == 404
    assert "Guild not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_guild_membership_no_session():
    """Test verify_guild_membership with no session raises 401."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_user.session_token = "session123"

    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_db = AsyncMock()

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value=None),
        pytest.raises(HTTPException) as exc_info,
    ):
        await permissions.verify_guild_membership("guild123", mock_current_user, mock_db)

    assert exc_info.value.status_code == 401
    assert "No session found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_template_access_success():
    """Test verify_template_access with authorized user."""
    from unittest.mock import MagicMock

    mock_template = MagicMock()
    mock_template.id = "template123"
    mock_template.guild_id = "db-guild-uuid"

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=True),
    ):
        result = await permissions.verify_template_access(
            mock_template, "user123", "test_token", mock_db
        )

    assert result == mock_template


@pytest.mark.asyncio
async def test_verify_template_access_not_member():
    """Test verify_template_access returns 404 for non-member."""
    from unittest.mock import MagicMock

    mock_template = MagicMock()
    mock_template.id = "template123"
    mock_template.guild_id = "db-guild-uuid"

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=False),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

    assert exc_info.value.status_code == 404
    assert "Template not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_template_access_guild_not_found():
    """Test verify_template_access with missing guild."""
    from unittest.mock import MagicMock

    mock_template = MagicMock()
    mock_template.id = "template123"
    mock_template.guild_id = "db-guild-uuid"

    mock_db = AsyncMock()

    with patch("services.api.database.queries.get_guild_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

    assert exc_info.value.status_code == 404
    assert "Template not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_game_access_success():
    """Test verify_game_access with authorized user."""
    from unittest.mock import MagicMock

    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.guild_id = "db-guild-uuid"
    mock_game.allowed_player_role_ids = None

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()
    mock_role_service = AsyncMock()

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=True),
    ):
        result = await permissions.verify_game_access(
            mock_game, "user123", "test_token", mock_db, mock_role_service
        )

    assert result == mock_game


@pytest.mark.asyncio
async def test_verify_game_access_not_member():
    """Test verify_game_access returns 404 for non-member."""
    from unittest.mock import MagicMock

    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.guild_id = "db-guild-uuid"

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()
    mock_role_service = AsyncMock()

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=False),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

    assert exc_info.value.status_code == 404
    assert "Game not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_game_access_role_check_success():
    """Test verify_game_access with player role restrictions passes."""
    from unittest.mock import MagicMock

    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.guild_id = "db-guild-uuid"
    mock_game.allowed_player_role_ids = ["role1", "role2"]

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()
    mock_role_service = AsyncMock()
    mock_role_service.has_any_role.return_value = True

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=True),
    ):
        result = await permissions.verify_game_access(
            mock_game, "user123", "test_token", mock_db, mock_role_service
        )

    assert result == mock_game
    mock_role_service.has_any_role.assert_called_once_with(
        "user123", "guild123", "test_token", ["role1", "role2"]
    )


@pytest.mark.asyncio
async def test_verify_game_access_role_check_fails():
    """Test verify_game_access returns 403 when user lacks player roles."""
    from unittest.mock import MagicMock

    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.guild_id = "db-guild-uuid"
    mock_game.allowed_player_role_ids = ["role1", "role2"]

    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "guild123"

    mock_db = AsyncMock()
    mock_role_service = AsyncMock()
    mock_role_service.has_any_role.return_value = False

    with (
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config),
        patch("services.api.dependencies.permissions._check_guild_membership", return_value=True),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

    assert exc_info.value.status_code == 403
    assert "required role" in exc_info.value.detail
