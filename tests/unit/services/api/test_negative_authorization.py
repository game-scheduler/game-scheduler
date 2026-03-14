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


"""
Negative authorization tests.

Tests verify that users cannot access resources they shouldn't be able to access,
ensuring proper 404 vs 403 responses to prevent information disclosure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.api.dependencies import permissions
from shared.schemas import auth as auth_schemas


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    mock_user = MagicMock()
    mock_user.discord_id = "user123"
    mock_user.id = "user-uuid-123"
    return auth_schemas.CurrentUser(
        user=mock_user, access_token="test_token", session_token="test-session-token"
    )


@pytest.fixture
def mock_other_user():
    """Create mock user for another guild."""
    mock_user = MagicMock()
    mock_user.discord_id = "other_user456"
    mock_user.id = "user-uuid-456"
    return auth_schemas.CurrentUser(
        user=mock_user, access_token="other_token", session_token="other-session-token"
    )


@pytest.fixture
def mock_tokens():
    """Mock token data."""
    return {
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_at": 9999999999,
    }


@pytest.fixture
def mock_guild_config():
    """Create mock guild configuration."""
    guild = MagicMock()
    guild.id = "guild-uuid-123"
    guild.guild_id = "123456789012345678"  # Discord snowflake
    return guild


@pytest.fixture
def mock_template():
    """Create mock template."""
    template = MagicMock()
    template.id = "template-uuid-123"
    template.guild_id = "guild-uuid-123"
    template.name = "Test Template"
    return template


@pytest.fixture
def mock_game():
    """Create mock game."""
    game = MagicMock()
    game.id = "game-uuid-123"
    game.guild_id = "guild-uuid-123"
    game.host_id = "host-uuid-123"
    game.allowed_player_role_ids = ["role123", "role456"]
    return game


class TestGuildMembershipAuthorization:
    """Test guild membership verification returns 404 for non-members."""

    @pytest.mark.asyncio
    async def test_verify_guild_membership_returns_404_not_member(
        self, mock_current_user, mock_tokens
    ):
        """Non-member receives 404 to prevent information disclosure."""
        guild_id = "123456789012345678"
        mock_db = AsyncMock()

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch(
                "services.api.auth.oauth2.get_user_guilds",
                return_value=[{"id": "different_guild"}],
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await permissions.verify_guild_membership(guild_id, mock_current_user, mock_db)

        assert exc_info.value.status_code == 404
        assert "Guild not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_guild_membership_returns_guilds_if_member(
        self, mock_current_user, mock_tokens
    ):
        """Member receives guild list."""
        guild_id = "123456789012345678"
        mock_db = AsyncMock()
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.verify_guild_membership(
                    guild_id, mock_current_user, mock_db
                )

        assert result == user_guilds

    @pytest.mark.asyncio
    async def test_verify_guild_membership_returns_401_no_session(self, mock_current_user):
        """No session returns 401."""
        guild_id = "123456789012345678"
        mock_db = AsyncMock()

        with patch("services.api.auth.tokens.get_user_tokens", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_guild_membership(guild_id, mock_current_user, mock_db)

        assert exc_info.value.status_code == 401
        assert "No session found" in exc_info.value.detail


class TestTemplateAccessAuthorization:
    """Test template access returns 404 for non-members."""

    @pytest.mark.asyncio
    async def test_template_access_returns_404_not_member(self, mock_template, mock_guild_config):
        """Non-member cannot access template - receives 404."""
        mock_db = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=False,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Template not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_template_access_returns_template_if_member(
        self, mock_template, mock_guild_config
    ):
        """Member can access template."""
        mock_db = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=True,
            ),
        ):
            result = await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

        assert result == mock_template

    @pytest.mark.asyncio
    async def test_template_access_returns_404_guild_not_found(self, mock_template):
        """Template with non-existent guild returns 404."""
        mock_db = AsyncMock()

        # require_guild_by_id now raises HTTPException instead of returning None
        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                side_effect=HTTPException(status_code=404, detail="Template not found"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Template not found" in exc_info.value.detail


class TestGameAccessAuthorization:
    """Test game access returns 404 for non-members, 403 for unauthorized members."""

    @pytest.mark.asyncio
    async def test_game_access_returns_404_not_member(self, mock_game, mock_guild_config):
        """Non-member cannot access game - receives 404."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=False,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert exc_info.value.status_code == 404
        assert "Game not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_game_access_returns_403_member_lacks_roles(self, mock_game, mock_guild_config):
        """Member without required roles receives 403 (not 404)."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.has_any_role = AsyncMock(return_value=False)

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=True,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert exc_info.value.status_code == 403
        assert "required role" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_game_access_returns_game_if_authorized(self, mock_game, mock_guild_config):
        """Authorized member can access game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.has_any_role = AsyncMock(return_value=True)

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=True,
            ),
        ):
            result = await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert result == mock_game

    @pytest.mark.asyncio
    async def test_game_access_allows_member_without_role_restrictions(
        self, mock_game, mock_guild_config
    ):
        """Member can access game with no role restrictions."""
        mock_game.allowed_player_role_ids = None
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=True,
            ),
        ):
            result = await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert result == mock_game
        mock_role_service.has_any_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_game_access_returns_404_guild_not_found(self, mock_game):
        """Game with non-existent guild returns 404."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()

        # require_guild_by_id now raises HTTPException instead of returning None
        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                side_effect=HTTPException(status_code=404, detail="Game not found"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert exc_info.value.status_code == 404
        assert "Game not found" in exc_info.value.detail


class TestGameManagementAuthorization:
    """Test can_manage_game returns 404 for non-members."""

    @pytest.mark.asyncio
    async def test_can_manage_game_returns_404_not_member(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Non-member attempting to manage game receives 404."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        guild_id = "123456789012345678"

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch(
                "services.api.auth.oauth2.get_user_guilds",
                return_value=[{"id": "different_guild"}],
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await permissions.can_manage_game(
                        "host123",
                        guild_id,
                        mock_current_user,
                        mock_role_service,
                        mock_db,
                    )

        assert exc_info.value.status_code == 404
        assert "Guild not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_can_manage_game_returns_true_for_host(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Host can manage their own game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_manage_game(
                    mock_current_user.user.discord_id,  # Host is current user
                    guild_id,
                    mock_current_user,
                    mock_role_service,
                    mock_db,
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_manage_game_returns_true_for_bot_manager(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Bot manager can manage any game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_manage_game(
                    "different_host",  # Not current user
                    guild_id,
                    mock_current_user,
                    mock_role_service,
                    mock_db,
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_manage_game_returns_false_for_unauthorized_member(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Guild member without bot manager role cannot manage other's game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_manage_game(
                    "different_host",  # Not current user
                    guild_id,
                    mock_current_user,
                    mock_role_service,
                    mock_db,
                )

        assert result is False


class TestGameExportAuthorization:
    """Test can_export_game returns 404 for non-members."""

    @pytest.mark.asyncio
    async def test_can_export_game_returns_404_not_member(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Non-member attempting to export game receives 404."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        guild_id = "123456789012345678"

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch(
                "services.api.auth.oauth2.get_user_guilds",
                return_value=[{"id": "different_guild"}],
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await permissions.can_export_game(
                        "host_uuid",
                        [],
                        guild_id,
                        mock_current_user.user.id,
                        mock_current_user.user.discord_id,
                        mock_role_service,
                        mock_db,
                        mock_tokens["access_token"],
                        mock_current_user,
                    )

        assert exc_info.value.status_code == 404
        assert "Guild not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_can_export_game_returns_true_for_host(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Host can export their own game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_export_game(
                    mock_current_user.user.id,  # Host is current user
                    [],
                    guild_id,
                    mock_current_user.user.id,
                    mock_current_user.user.discord_id,
                    mock_role_service,
                    mock_db,
                    mock_tokens["access_token"],
                    mock_current_user,
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_export_game_returns_true_for_participant(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Participant can export game they're in."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        # Create mock participant
        mock_participant = MagicMock()
        mock_participant.user_id = mock_current_user.user.discord_id
        mock_participant.user = MagicMock()

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_export_game(
                    "different_host",
                    [mock_participant],
                    guild_id,
                    mock_current_user.user.id,
                    mock_current_user.user.discord_id,
                    mock_role_service,
                    mock_db,
                    mock_tokens["access_token"],
                    mock_current_user,
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_export_game_returns_true_for_bot_manager(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Bot manager can export any game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_export_game(
                    "different_host",
                    [],
                    guild_id,
                    mock_current_user.user.id,
                    mock_current_user.user.discord_id,
                    mock_role_service,
                    mock_db,
                    mock_tokens["access_token"],
                    mock_current_user,
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_export_game_returns_false_for_unauthorized(
        self, mock_current_user, mock_tokens, mock_guild_config
    ):
        """Unauthorized member cannot export game."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)
        guild_id = "123456789012345678"
        user_guilds = [{"id": guild_id, "name": "Test Guild"}]

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch("services.api.auth.oauth2.get_user_guilds", return_value=user_guilds):
                result = await permissions.can_export_game(
                    "different_host",
                    [],
                    guild_id,
                    mock_current_user.user.id,
                    mock_current_user.user.discord_id,
                    mock_role_service,
                    mock_db,
                    mock_tokens["access_token"],
                    mock_current_user,
                )

        assert result is False


class TestInformationDisclosurePrevention:
    """
    Test that authorization failures don't leak information about guild existence.

    Per OWASP, return 404 for resources in guilds user doesn't belong to,
    not 403, to prevent enumeration attacks.
    """

    @pytest.mark.asyncio
    async def test_guild_membership_check_prevents_enumeration(
        self, mock_current_user, mock_tokens
    ):
        """
        Verify 404 returned for non-existent guilds same as unauthorized guilds.

        This prevents attackers from discovering which guild IDs exist.
        """
        mock_db = AsyncMock()

        with patch("services.api.auth.tokens.get_user_tokens", return_value=mock_tokens):
            with patch(
                "services.api.auth.oauth2.get_user_guilds",
                return_value=[{"id": "user_guild"}],
            ):
                # Test both non-existent and unauthorized guild
                for guild_id in ["123456789012345678", "999999999999999999"]:
                    with pytest.raises(HTTPException) as exc_info:
                        await permissions.verify_guild_membership(
                            guild_id, mock_current_user, mock_db
                        )

                    # Both should return same 404 error
                    assert exc_info.value.status_code == 404
                    assert "Guild not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_template_access_prevents_guild_enumeration(
        self, mock_template, mock_guild_config
    ):
        """Template access returns 404 regardless of whether guild exists."""
        mock_db = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=False,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_template_access(
                mock_template, "user123", "test_token", mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Template not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_game_access_prevents_guild_enumeration(self, mock_game, mock_guild_config):
        """Game access returns 404 for non-members regardless of guild existence."""
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=False,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        assert exc_info.value.status_code == 404
        assert "Game not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_member_without_role_gets_403_not_404(self, mock_game, mock_guild_config):
        """
        Guild member lacking required role gets 403 (not 404).

        This is appropriate because the user IS a guild member,
        so revealing the resource exists is not an information leak.
        """
        mock_db = AsyncMock()
        mock_role_service = AsyncMock()
        mock_role_service.has_any_role = AsyncMock(return_value=False)

        with (
            patch(
                "services.api.database.queries.require_guild_by_id",
                return_value=mock_guild_config,
            ),
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                return_value=True,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await permissions.verify_game_access(
                mock_game, "user123", "test_token", mock_db, mock_role_service
            )

        # Guild member without role gets 403, not 404
        assert exc_info.value.status_code == 403
        assert "required role" in exc_info.value.detail.lower()
