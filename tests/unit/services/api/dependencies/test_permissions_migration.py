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
Unit tests for permissions.py migration to require_guild_by_id helper.

Tests verify no behavior changes after migration from get_guild_by_id
to require_guild_by_id helper function.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from services.api.dependencies import permissions
from shared.data_access.guild_isolation import set_current_guild_ids
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.template import GameTemplate


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def guild_config():
    """Sample guild configuration."""
    return GuildConfiguration(
        id=str(uuid4()),
        guild_id="123456789012345678",
        bot_manager_role_ids=["987654321098765432"],
    )


@pytest.fixture
def game_template(guild_config):
    """Sample game template."""
    return GameTemplate(
        id=str(uuid4()),
        guild_id=guild_config.id,
        name="Test Template",
        description="Test description",
    )


@pytest.fixture
def game_session(guild_config):
    """Sample game session."""
    return GameSession(
        id=str(uuid4()),
        guild_id=guild_config.id,
        title="Test Game",
        description="Test game description",
        allowed_player_role_ids=["111222333444555666"],
    )


class TestVerifyTemplateAccess:
    """Tests for verify_template_access function after migration."""

    @pytest.mark.asyncio
    async def test_verify_template_access_success(self, mock_db, game_template, guild_config):
        """Test successful template access verification."""
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = True

            result = await permissions.verify_template_access(
                game_template, "user123", "token123", mock_db
            )

            assert result == game_template
            mock_require.assert_called_once_with(
                mock_db,
                game_template.guild_id,
                "token123",
                "user123",
                not_found_detail="Template not found",
            )
            mock_check.assert_called_once_with("user123", guild_config.guild_id, "token123")

    @pytest.mark.asyncio
    async def test_verify_template_access_guild_not_found(self, mock_db, game_template):
        """Test template access when guild not found."""
        with patch(
            "services.api.dependencies.permissions.queries.require_guild_by_id",
            new_callable=AsyncMock,
        ) as mock_require:
            mock_require.side_effect = HTTPException(status_code=404, detail="Template not found")

            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_template_access(
                    game_template, "user123", "token123", mock_db
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Template not found"

    @pytest.mark.asyncio
    async def test_verify_template_access_user_not_member(
        self, mock_db, game_template, guild_config
    ):
        """Test template access when user not guild member."""
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_template_access(
                    game_template, "user123", "token123", mock_db
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Template not found"


class TestVerifyGameAccess:
    """Tests for verify_game_access function after migration."""

    @pytest.mark.asyncio
    async def test_verify_game_access_success(
        self, mock_db, game_session, guild_config, mock_role_service
    ):
        """Test successful game access verification."""
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = True
            mock_role_service.has_any_role.return_value = True

            result = await permissions.verify_game_access(
                game_session, "user123", "token123", mock_db, mock_role_service
            )

            assert result == game_session
            mock_require.assert_called_once_with(
                mock_db,
                game_session.guild_id,
                "token123",
                "user123",
                not_found_detail="Game not found",
            )
            mock_check.assert_called_once_with("user123", guild_config.guild_id, "token123")
            mock_role_service.has_any_role.assert_called_once_with(
                "user123", guild_config.guild_id, game_session.allowed_player_role_ids
            )

    @pytest.mark.asyncio
    async def test_verify_game_access_guild_not_found(
        self, mock_db, game_session, mock_role_service
    ):
        """Test game access when guild not found."""
        with patch(
            "services.api.dependencies.permissions.queries.require_guild_by_id",
            new_callable=AsyncMock,
        ) as mock_require:
            mock_require.side_effect = HTTPException(status_code=404, detail="Game not found")

            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_game_access(
                    game_session, "user123", "token123", mock_db, mock_role_service
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Game not found"

    @pytest.mark.asyncio
    async def test_verify_game_access_user_not_member(
        self, mock_db, game_session, guild_config, mock_role_service
    ):
        """Test game access when user not guild member."""
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_game_access(
                    game_session, "user123", "token123", mock_db, mock_role_service
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Game not found"

    @pytest.mark.asyncio
    async def test_verify_game_access_user_lacks_player_role(
        self, mock_db, game_session, guild_config, mock_role_service
    ):
        """Test game access when user lacks required player role."""
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = True
            mock_role_service.has_any_role.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await permissions.verify_game_access(
                    game_session, "user123", "token123", mock_db, mock_role_service
                )

            assert exc_info.value.status_code == 403
            assert "required role" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_game_access_no_player_role_restriction(
        self, mock_db, guild_config, mock_role_service
    ):
        """Test game access when no player role restriction configured."""
        game_no_roles = GameSession(
            id=str(uuid4()),
            guild_id=guild_config.id,
            title="Test Game",
            description="Test game description",
            allowed_player_role_ids=None,
        )
        set_current_guild_ids([guild_config.guild_id])

        with (
            patch(
                "services.api.dependencies.permissions.queries.require_guild_by_id",
                new_callable=AsyncMock,
            ) as mock_require,
            patch(
                "services.api.dependencies.permissions._check_guild_membership",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_require.return_value = guild_config
            mock_check.return_value = True

            result = await permissions.verify_game_access(
                game_no_roles, "user123", "token123", mock_db, mock_role_service
            )

            assert result == game_no_roles
            mock_role_service.has_any_role.assert_not_called()


class TestResolveGuildDiscordId:
    """Tests for _resolve_guild_id function after migration."""

    @pytest.mark.asyncio
    async def test_resolve_guild_id_already_snowflake(self, mock_db):
        """Test resolution when guild_id is already a Discord snowflake."""
        snowflake_id = "123456789012345678"
        result = await permissions._resolve_guild_id(snowflake_id, mock_db, "token123", "user123")
        assert result == snowflake_id

    @pytest.mark.asyncio
    async def test_resolve_guild_id_from_uuid_success(self, mock_db, guild_config):
        """Test successful resolution of UUID to Discord snowflake."""
        set_current_guild_ids([guild_config.guild_id])

        with patch(
            "services.api.dependencies.permissions.queries.require_guild_by_id",
            new_callable=AsyncMock,
        ) as mock_require:
            mock_require.return_value = guild_config
            result = await permissions._resolve_guild_id(
                guild_config.id, mock_db, "token123", "user123"
            )
            assert result == guild_config.guild_id
            mock_require.assert_called_once_with(mock_db, guild_config.id, "token123", "user123")

    @pytest.mark.asyncio
    async def test_resolve_guild_id_guild_not_found(self, mock_db):
        """Test resolution when guild not found."""
        with patch(
            "services.api.dependencies.permissions.queries.require_guild_by_id",
            new_callable=AsyncMock,
        ) as mock_require:
            mock_require.side_effect = HTTPException(status_code=404, detail="Guild not found")
            uuid_id = str(uuid4())

            with pytest.raises(HTTPException) as exc_info:
                await permissions._resolve_guild_id(uuid_id, mock_db, "token123", "user123")

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Guild not found"
