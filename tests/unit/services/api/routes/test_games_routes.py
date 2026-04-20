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


"""Unit tests for game routes error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status as http_status

from services.api.routes import games as games_routes
from services.api.services import participant_resolver as resolver_module
from services.api.services.display_names import DisplayNameResolver
from shared.schemas import game as game_schemas


@pytest.fixture
def sample_game_data():
    """Sample game data for error responses."""
    return game_schemas.GameCreateRequest(
        template_id="template-123",
        title="Test Game",
        scheduled_at=datetime(2026, 2, 1, 14, 0, 0, tzinfo=UTC),
        description="Test description",
        max_players=4,
    )


@pytest.fixture
def sample_update_data():
    """Sample game update data for error responses."""
    return game_schemas.GameUpdateRequest(
        title="Updated Game",
        description="Updated description",
    )


def test_handle_game_operation_errors_validation_error(sample_game_data):
    """Test handling ValidationError returns 422 with invalid mentions."""
    validation_error = resolver_module.ValidationError(
        invalid_mentions=["@unknown"],
        valid_participants=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(validation_error, sample_game_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail["error"] == "invalid_mentions"
    assert exc_info.value.detail["message"] == "Some @mentions could not be resolved"
    assert exc_info.value.detail["invalid_mentions"] == ["@unknown"]
    assert exc_info.value.detail["valid_participants"] == []
    assert "form_data" in exc_info.value.detail


def test_handle_game_operation_errors_value_error_not_found(sample_update_data):
    """Test handling ValueError with 'not found' returns 404."""
    value_error = ValueError("Game not found")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Game not found"


def test_handle_game_operation_errors_value_error_min_players(sample_update_data):
    """Test handling ValueError with minimum players error returns 422."""
    value_error = ValueError("Minimum players cannot be greater than maximum players")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail == "Minimum players cannot be greater than maximum players"


def test_handle_game_operation_errors_value_error_forbidden(sample_game_data):
    """Test handling generic ValueError returns 403."""
    value_error = ValueError("You do not have permission to perform this action")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_game_data)

    assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You do not have permission to perform this action"


def test_handle_game_operation_errors_with_update_data(sample_update_data):
    """Test error handling with GameUpdateBase data."""
    validation_error = resolver_module.ValidationError(
        invalid_mentions=["@invalid"],
        valid_participants=["123"],
    )

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(validation_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    form_data = exc_info.value.detail["form_data"]
    assert form_data["title"] == "Updated Game"


def test_handle_game_operation_errors_unexpected_type(sample_game_data):
    """Test that an unexpected exception type produces a 500 with the type name."""
    unexpected_error = RuntimeError("Database crashed")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(unexpected_error, sample_game_data)

    assert exc_info.value.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "RuntimeError" in exc_info.value.detail


class TestGetGameCanManage:
    """Tests for can_manage logic in get_game route handler."""

    def _make_game(self) -> MagicMock:
        game = MagicMock()
        game.host = MagicMock()
        game.host.discord_id = "host_discord_id"
        game.guild = MagicMock()
        game.guild.guild_id = "guild_discord_id"
        return game

    def _make_current_user(self) -> MagicMock:
        user = MagicMock()
        user.user.discord_id = "user_discord_id"
        user.access_token = "token"
        return user

    @pytest.mark.asyncio
    async def test_get_game_passes_can_manage_true_when_authorized(self):
        """get_game passes can_manage=True to _build_game_response when user can manage."""
        game = self._make_game()
        current_user = self._make_current_user()
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)
        game_service.db = MagicMock()
        role_service = MagicMock()
        expected_response = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_build,
        ):
            result = await games_routes.get_game(
                game_id="game-123",
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
            )

        mock_build.assert_called_once_with(
            game,
            can_manage=True,
        )
        assert result is expected_response

    @pytest.mark.asyncio
    async def test_get_game_passes_can_manage_false_when_not_authorized(self):
        """get_game passes can_manage=False to _build_game_response when user cannot manage."""
        game = self._make_game()
        current_user = self._make_current_user()
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)
        game_service.db = MagicMock()
        role_service = MagicMock()
        expected_response = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_build,
        ):
            result = await games_routes.get_game(
                game_id="game-123",
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
            )

        mock_build.assert_called_once_with(
            game,
            can_manage=False,
        )
        assert result is expected_response

    @pytest.mark.asyncio
    async def test_get_game_passes_can_manage_false_on_http_exception(self):
        """get_game passes can_manage=False when can_manage_game raises HTTPException."""
        game = self._make_game()
        current_user = self._make_current_user()
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)
        game_service.db = MagicMock()
        role_service = MagicMock()
        expected_response = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                side_effect=HTTPException(status_code=http_status.HTTP_404_NOT_FOUND),
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_build,
        ):
            result = await games_routes.get_game(
                game_id="game-123",
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
            )

        mock_build.assert_called_once_with(
            game,
            can_manage=False,
        )
        assert result is expected_response


class TestListGamesResolvesParticipants:
    """Tests for resolve_participants=False in list_games route."""

    @pytest.mark.asyncio
    async def test_list_games_calls_build_with_resolve_participants_false(self):
        """list_games calls _build_game_response with resolve_participants=False."""
        game = MagicMock()
        current_user = MagicMock()
        current_user.user.discord_id = "user123"
        current_user.access_token = "token"
        game_service = MagicMock()
        game_service.list_games = AsyncMock(return_value=([game], 1))
        game_service.db = MagicMock()
        role_service = MagicMock()
        expected_response = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_build,
            patch(
                "services.api.routes.games.game_schemas.GameListResponse",
                return_value=MagicMock(),
            ),
        ):
            mock_display_svc = MagicMock()
            mock_display_svc.resolve_display_names_and_avatars = AsyncMock(return_value={})

            await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
                display_name_resolver=mock_display_svc,
            )

        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args.kwargs
        assert call_kwargs.get("resolve_participants") is False


class TestListGamesPrefetchedDisplayData:
    """Tests for prefetched host display data batch fetch in list_games."""

    def _make_game(self, host_discord_id: str, guild_discord_id: str) -> MagicMock:
        game = MagicMock()
        game.host = MagicMock()
        game.host.discord_id = host_discord_id
        game.guild = MagicMock()
        game.guild.guild_id = guild_discord_id
        game.guild_id = "guild-db-id"
        return game

    @pytest.mark.asyncio
    async def test_list_games_passes_prefetched_display_data_to_build(self):
        """list_games passes prefetched_display_data into each _build_game_response call."""
        game = self._make_game("host1", "guild_discord_1")
        current_user = MagicMock()
        current_user.user.discord_id = "user123"
        current_user.access_token = "token"
        game_service = MagicMock()
        game_service.list_games = AsyncMock(return_value=([game], 1))
        game_service.db = MagicMock()
        role_service = MagicMock()

        prefetched = {"host1": {"display_name": "Host One", "avatar_url": None}}

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ) as mock_build,
            patch(
                "services.api.routes.games.game_schemas.GameListResponse",
                return_value=MagicMock(),
            ),
        ):
            mock_display_svc = MagicMock()
            mock_display_svc.resolve_display_names_and_avatars = AsyncMock(return_value=prefetched)

            await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
                display_name_resolver=mock_display_svc,
            )

        call_kwargs = mock_build.call_args.kwargs
        assert call_kwargs.get("prefetched_display_data") == prefetched

    @pytest.mark.asyncio
    async def test_list_games_fetches_host_once_across_multiple_games(self):
        """A host appearing in multiple games triggers exactly one Discord member fetch."""
        game1 = self._make_game("host1", "guild_discord_1")
        game2 = self._make_game("host1", "guild_discord_1")
        current_user = MagicMock()
        current_user.user.discord_id = "user123"
        current_user.access_token = "token"
        game_service = MagicMock()
        game_service.list_games = AsyncMock(return_value=([game1, game2], 2))
        game_service.db = MagicMock()
        role_service = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "services.api.routes.games.game_schemas.GameListResponse",
                return_value=MagicMock(),
            ),
        ):
            mock_display_svc = MagicMock()
            mock_display_svc.resolve_display_names_and_avatars = AsyncMock(return_value={})

            await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
                display_name_resolver=mock_display_svc,
            )

        assert mock_display_svc.resolve_display_names_and_avatars.call_count == 1
        call_args = mock_display_svc.resolve_display_names_and_avatars.call_args
        resolved_ids = call_args.args[1] if call_args.args else call_args.kwargs.get("user_ids", [])
        assert resolved_ids.count("host1") == 1

    @pytest.mark.asyncio
    async def test_list_games_one_fetch_per_guild(self):
        """list_games issues one resolve_display_names_and_avatars call per guild, not per game."""
        game_g1 = self._make_game("host_a", "guild_1")
        game_g2 = self._make_game("host_b", "guild_2")
        current_user = MagicMock()
        current_user.user.discord_id = "user123"
        current_user.access_token = "token"
        game_service = MagicMock()
        game_service.list_games = AsyncMock(return_value=([game_g1, game_g2], 2))
        game_service.db = MagicMock()
        role_service = MagicMock()

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "services.api.routes.games.game_schemas.GameListResponse",
                return_value=MagicMock(),
            ),
        ):
            mock_display_svc = MagicMock()
            mock_display_svc.resolve_display_names_and_avatars = AsyncMock(return_value={})

            await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
                display_name_resolver=mock_display_svc,
            )

        assert mock_display_svc.resolve_display_names_and_avatars.call_count == 2


class TestListGamesUsesDisplayNameResolver:
    """list_games should call resolve_display_names_and_avatars on the resolver directly."""

    def _make_game(self, host_discord_id: str, guild_discord_id: str) -> MagicMock:
        game = MagicMock()
        game.host = MagicMock()
        game.host.discord_id = host_discord_id
        game.guild = MagicMock()
        game.guild.guild_id = guild_discord_id
        game.guild_id = "guild-db-id"
        return game

    @pytest.mark.asyncio
    async def test_list_games_calls_resolver_resolve_display_names_and_avatars(self):
        """list_games calls resolver.resolve_display_names_and_avatars for host display names."""
        game = self._make_game("host1", "guild_discord_1")
        current_user = MagicMock()
        current_user.user.discord_id = "user123"
        current_user.access_token = "token"
        game_service = MagicMock()
        game_service.list_games = AsyncMock(return_value=([game], 1))
        game_service.db = MagicMock()
        role_service = MagicMock()

        mock_display_resolver = MagicMock(spec=DisplayNameResolver)
        mock_display_resolver.resolve_display_names_and_avatars = AsyncMock(
            return_value={"host1": {"display_name": "Host", "avatar_url": None}}
        )

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "services.api.routes.games.game_schemas.GameListResponse", return_value=MagicMock()
            ),
        ):
            await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                limit=50,
                offset=0,
                current_user=current_user,
                game_service=game_service,
                role_service=role_service,
                display_name_resolver=mock_display_resolver,
            )

        mock_display_resolver.resolve_display_names_and_avatars.assert_awaited_once_with(
            "guild_discord_1", ["host1"]
        )
