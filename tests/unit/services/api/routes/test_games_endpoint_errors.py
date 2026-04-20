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


"""Unit tests for game endpoint error paths."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status as http_status

from services.api.routes import games as games_routes
from services.api.schemas.clone_game import CarryoverOption, CloneGameRequest
from services.api.services import participant_resolver as resolver_module


@pytest.fixture
def mock_game_service():
    svc = AsyncMock()
    svc.db = AsyncMock()
    return svc


@pytest.fixture
def clone_data():
    return CloneGameRequest(
        scheduled_at=datetime(2026, 7, 1, 20, 0, tzinfo=UTC),
        player_carryover=CarryoverOption.NO,
        waitlist_carryover=CarryoverOption.NO,
    )


class TestCreateGame:
    @pytest.mark.asyncio
    async def test_create_game_validation_error(self, mock_current_user_unit, mock_game_service):
        mock_game_service.create_game.side_effect = resolver_module.ValidationError(
            invalid_mentions=["@ghost"], valid_participants=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="2026-06-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc_info.value.detail["error"] == "invalid_mentions"

    @pytest.mark.asyncio
    async def test_create_game_value_error_not_found(
        self, mock_current_user_unit, mock_game_service
    ):
        mock_game_service.create_game.side_effect = ValueError("Template not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="2026-06-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND


class TestListGames:
    @pytest.mark.asyncio
    async def test_list_games_filters_unauthorized_games(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game = MagicMock()
        mock_game_service.list_games.return_value = ([mock_game], 1)

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            side_effect=HTTPException(status_code=http_status.HTTP_403_FORBIDDEN),
        ):
            result = await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
                display_name_resolver=MagicMock(),
            )

        assert result.games == []
        assert result.total == 0


class TestGetGame:
    @pytest.mark.asyncio
    async def test_get_game_can_manage_exception_defaults_false(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game = MagicMock()
        mock_game.guild = MagicMock()
        mock_game.guild.guild_id = "discord-guild-123"
        mock_game.host = MagicMock()
        mock_game.host.discord_id = "host-discord-123"
        mock_game_service.get_game.return_value = mock_game

        with (
            patch(
                "services.api.dependencies.permissions.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.dependencies.permissions.can_manage_game",
                side_effect=HTTPException(status_code=http_status.HTTP_403_FORBIDDEN),
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ) as mock_build,
        ):
            await games_routes.get_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        mock_build.assert_called_once_with(
            mock_game,
            can_manage=False,
        )


class TestUpdateGame:
    @pytest.mark.asyncio
    async def test_update_game_validation_error(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.update_game.side_effect = resolver_module.ValidationError(
            invalid_mentions=["@ghost"], valid_participants=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.update_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_game_value_error_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.update_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.update_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND


class TestDeleteGame:
    @pytest.mark.asyncio
    async def test_delete_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.delete_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.delete_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_game_forbidden(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.delete_game.side_effect = ValueError("You are not the host")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.delete_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN


class TestCloneGame:
    @pytest.mark.asyncio
    async def test_clone_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service, clone_data
    ):
        mock_game_service.clone_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                clone_data=clone_data,
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clone_game_forbidden(
        self, mock_current_user_unit, mock_game_service, mock_role_service, clone_data
    ):
        mock_game_service.clone_game.side_effect = ValueError("Not the host")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                clone_data=clone_data,
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN


class TestJoinGame:
    @pytest.fixture
    def mock_game(self):
        game = MagicMock()
        game.guild_id = "guild-uuid-1"
        game.guild = MagicMock()
        game.guild.guild_id = "discord-guild-123"
        return game

    @pytest.mark.asyncio
    async def test_join_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service, mock_game
    ):
        mock_game_service.get_game.return_value = mock_game
        mock_game_service.join_game.side_effect = ValueError("Game not found")

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await games_routes.join_game(
                    game_id="game-1",
                    current_user=mock_current_user_unit,
                    game_service=mock_game_service,
                    role_service=mock_role_service,
                    display_name_resolver=MagicMock(),
                )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_join_game_bad_request(
        self, mock_current_user_unit, mock_game_service, mock_role_service, mock_game
    ):
        mock_game_service.get_game.return_value = mock_game
        mock_game_service.join_game.side_effect = ValueError("Game is full")

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await games_routes.join_game(
                    game_id="game-1",
                    current_user=mock_current_user_unit,
                    game_service=mock_game_service,
                    role_service=mock_role_service,
                    display_name_resolver=MagicMock(),
                )

        assert exc_info.value.status_code == http_status.HTTP_400_BAD_REQUEST


class TestLeaveGame:
    @pytest.mark.asyncio
    async def test_leave_game_not_found(self, mock_current_user_unit, mock_game_service):
        mock_game_service.leave_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.leave_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_leave_game_bad_request(self, mock_current_user_unit, mock_game_service):
        mock_game_service.leave_game.side_effect = ValueError("Not a participant")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.leave_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_400_BAD_REQUEST
