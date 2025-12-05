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


@pytest.mark.asyncio
async def test_check_guild_membership_exception_handling(caplog):
    """Test _check_guild_membership returns False on exception."""
    import logging

    caplog.set_level(logging.ERROR)

    with patch(
        "services.api.auth.oauth2.get_user_guilds", side_effect=Exception("Discord API error")
    ):
        result = await permissions._check_guild_membership("user123", "guild123", "test_token")

    assert result is False
    assert "Failed to check guild membership" in caplog.text
    assert "user123" in caplog.text


@pytest.mark.asyncio
async def test_get_guild_name_success(mock_current_user, mock_tokens):
    """Test get_guild_name returns guild name."""
    mock_db = AsyncMock()
    user_guilds = [
        {"id": "guild123", "name": "Test Guild"},
        {"id": "guild456", "name": "Other Guild"},
    ]

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens),
        patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds),
    ):
        result = await permissions.get_guild_name("guild123", mock_current_user, mock_db)

    assert result == "Test Guild"


@pytest.mark.asyncio
async def test_get_guild_name_not_found(mock_current_user, mock_tokens):
    """Test get_guild_name returns Unknown Guild for missing guild."""
    mock_db = AsyncMock()
    user_guilds = [{"id": "guild456", "name": "Other Guild"}]

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens),
        patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds),
    ):
        result = await permissions.get_guild_name("guild123", mock_current_user, mock_db)

    assert result == "Unknown Guild"


@pytest.mark.asyncio
async def test_get_guild_name_no_session(mock_current_user):
    """Test get_guild_name raises 401 when no session."""
    mock_db = AsyncMock()

    with (
        patch("services.api.auth.tokens.get_user_tokens", return_value=None),
        pytest.raises(HTTPException) as exc_info,
    ):
        await permissions.get_guild_name("guild123", mock_current_user, mock_db)

    assert exc_info.value.status_code == 401
    assert "No session found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_manage_channels_no_session(mock_current_user, mock_role_service):
    """Test require_manage_channels with no session."""
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_manage_channels(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_bot_manager_no_session(mock_current_user, mock_role_service):
    """Test require_bot_manager with no session."""
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_bot_manager(
                "123456789012345678",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_game_host_no_session(mock_current_user, mock_role_service):
    """Test require_game_host with no session."""
    mock_db = AsyncMock()

    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_game_host(
                "guild456",
                "channel789",
                mock_current_user,
                mock_role_service,
                mock_db,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_administrator_no_session(mock_current_user, mock_role_service):
    """Test require_administrator with no session."""
    with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.require_administrator(
                "guild456",
                mock_current_user,
                mock_role_service,
            )

    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_game_access_guild_not_found():
    """Test verify_game_access with missing guild."""
    from unittest.mock import MagicMock

    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.guild_id = "db-guild-uuid"

    mock_db = AsyncMock()
    mock_role_service = AsyncMock()

    with patch("services.api.database.queries.get_guild_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

    assert exc_info.value.status_code == 404
    assert "Game not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_resolve_guild_id_guild_not_found():
    """Test _resolve_guild_id raises 404 when guild not in database."""
    mock_db = AsyncMock()

    with patch("services.api.database.queries.get_guild_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await permissions._resolve_guild_id("some-uuid-format", mock_db)

    assert exc_info.value.status_code == 404
    assert "Guild not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_resolve_guild_id_uuid_success():
    """Test _resolve_guild_id successfully resolves UUID to Discord guild ID."""
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    mock_guild_config = MagicMock()
    mock_guild_config.guild_id = "123456789012345678"

    with patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild_config):
        result = await permissions._resolve_guild_id("db-guild-uuid-format", mock_db)

    assert result == "123456789012345678"


@pytest.mark.asyncio
async def test_can_manage_game_user_is_host():
    """Test can_manage_game returns True when user is host."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_db = AsyncMock()

    with (
        patch(
            "services.api.dependencies.permissions.verify_guild_membership",
            return_value=[{"id": "guild123"}],
        ),
    ):
        result = await permissions.can_manage_game(
            "user123",  # game_host_id matches user
            "guild123",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result is True


@pytest.mark.asyncio
async def test_can_manage_game_user_is_bot_manager():
    """Test can_manage_game returns True when user is bot manager."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = True
    mock_db = AsyncMock()

    with (
        patch(
            "services.api.dependencies.permissions.verify_guild_membership",
            return_value=[{"id": "guild123"}],
        ),
        patch(
            "services.api.auth.tokens.get_user_tokens", return_value={"access_token": "test_token"}
        ),
    ):
        result = await permissions.can_manage_game(
            "other_user",  # Not the host
            "guild123",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result is True


@pytest.mark.asyncio
async def test_can_manage_game_user_unauthorized():
    """Test can_manage_game returns False when user is neither host nor bot manager."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = False
    mock_db = AsyncMock()

    with (
        patch(
            "services.api.dependencies.permissions.verify_guild_membership",
            return_value=[{"id": "guild123"}],
        ),
        patch(
            "services.api.auth.tokens.get_user_tokens", return_value={"access_token": "test_token"}
        ),
    ):
        result = await permissions.can_manage_game(
            "other_user",  # Not the host
            "guild123",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result is False


@pytest.mark.asyncio
async def test_can_manage_game_no_token():
    """Test can_manage_game handles None token gracefully."""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_current_user = MagicMock()
    mock_current_user.user = mock_user
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = False
    mock_db = AsyncMock()

    with (
        patch(
            "services.api.dependencies.permissions.verify_guild_membership",
            return_value=[{"id": "guild123"}],
        ),
        patch("services.api.auth.tokens.get_user_tokens", return_value=None),
    ):
        result = await permissions.can_manage_game(
            "other_user",
            "guild123",
            mock_current_user,
            mock_role_service,
            mock_db,
        )

    assert result is False
    mock_role_service.check_bot_manager_permission.assert_called_once_with(
        "user123", "guild123", mock_db, None
    )


@pytest.mark.asyncio
async def test_can_export_game_user_is_host():
    """Test can_export_game returns True when user is host."""
    from unittest.mock import MagicMock

    mock_current_user = MagicMock()
    mock_current_user.user = MagicMock()
    mock_current_user.user.discord_id = "user123"
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_db = AsyncMock()

    with patch(
        "services.api.dependencies.permissions.verify_guild_membership",
        return_value=[{"id": "guild123"}],
    ):
        result = await permissions.can_export_game(
            "user-db-uuid",  # game_host_id matches user_id
            [],
            "guild123",
            "user-db-uuid",  # user_id
            "user123",
            mock_role_service,
            mock_db,
            "test_token",
            mock_current_user,
        )

    assert result is True


@pytest.mark.asyncio
async def test_can_export_game_user_is_participant():
    """Test can_export_game returns True when user is participant."""
    from unittest.mock import MagicMock

    mock_current_user = MagicMock()
    mock_current_user.user = MagicMock()
    mock_current_user.user.discord_id = "user123"
    mock_current_user.session_token = "session123"

    mock_participant = MagicMock()
    mock_participant.user_id = "user123"
    mock_participant.user = MagicMock()  # Not None

    mock_role_service = AsyncMock()
    mock_db = AsyncMock()

    with patch(
        "services.api.dependencies.permissions.verify_guild_membership",
        return_value=[{"id": "guild123"}],
    ):
        result = await permissions.can_export_game(
            "other-host",
            [mock_participant],
            "guild123",
            "user-db-uuid",
            "user123",  # discord_id matches participant
            mock_role_service,
            mock_db,
            "test_token",
            mock_current_user,
        )

    assert result is True


@pytest.mark.asyncio
async def test_can_export_game_user_is_bot_manager():
    """Test can_export_game returns True when user is bot manager."""
    from unittest.mock import MagicMock

    mock_current_user = MagicMock()
    mock_current_user.user = MagicMock()
    mock_current_user.user.discord_id = "user123"
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = True
    mock_db = AsyncMock()

    with patch(
        "services.api.dependencies.permissions.verify_guild_membership",
        return_value=[{"id": "guild123"}],
    ):
        result = await permissions.can_export_game(
            "other-host",
            [],
            "guild123",
            "user-db-uuid",
            "user123",
            mock_role_service,
            mock_db,
            "test_token",
            mock_current_user,
        )

    assert result is True


@pytest.mark.asyncio
async def test_can_export_game_user_unauthorized():
    """Test can_export_game returns False when user lacks all permissions."""
    from unittest.mock import MagicMock

    mock_current_user = MagicMock()
    mock_current_user.user = MagicMock()
    mock_current_user.user.discord_id = "user123"
    mock_current_user.session_token = "session123"

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = False
    mock_db = AsyncMock()

    with patch(
        "services.api.dependencies.permissions.verify_guild_membership",
        return_value=[{"id": "guild123"}],
    ):
        result = await permissions.can_export_game(
            "other-host",
            [],
            "guild123",
            "other-user-db-uuid",
            "user123",
            mock_role_service,
            mock_db,
            "test_token",
            mock_current_user,
        )

    assert result is False


@pytest.mark.asyncio
async def test_can_export_game_participant_user_is_none():
    """Test can_export_game handles participant with None user."""
    from unittest.mock import MagicMock

    mock_current_user = MagicMock()
    mock_current_user.user = MagicMock()
    mock_current_user.user.discord_id = "user123"
    mock_current_user.session_token = "session123"

    mock_participant = MagicMock()
    mock_participant.user_id = "user123"
    mock_participant.user = None  # User is None

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = False
    mock_db = AsyncMock()

    with patch(
        "services.api.dependencies.permissions.verify_guild_membership",
        return_value=[{"id": "guild123"}],
    ):
        result = await permissions.can_export_game(
            "other-host",
            [mock_participant],
            "guild123",
            "other-user-db-uuid",
            "user123",
            mock_role_service,
            mock_db,
            "test_token",
            mock_current_user,
        )

    # Should not count as participant because user is None
    assert result is False


@pytest.mark.asyncio
async def test_can_export_game_no_current_user():
    """Test can_export_game skips guild membership check when current_user is None."""

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission.return_value = True
    mock_db = AsyncMock()

    # Should not call verify_guild_membership when current_user is None
    result = await permissions.can_export_game(
        "other-host",
        [],
        "guild123",
        "user-db-uuid",
        "user123",
        mock_role_service,
        mock_db,
        "test_token",
        None,  # current_user is None
    )

    assert result is True
