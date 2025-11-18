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


"""Tests for GameView button component."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.bot.views.game_view import GameView


@pytest.fixture
def event_loop():
    """Create an event loop for tests that need it."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestGameView:
    """Tests for GameView class."""

    @pytest.mark.asyncio
    async def test_initializes_with_default_values(self, event_loop):
        """Test GameView initialization with default values."""
        view = GameView(game_id="test-game-id")
        assert view.game_id == "test-game-id"
        assert view.is_full is False
        assert view.is_started is False
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_initializes_with_full_game(self, event_loop):
        """Test GameView when game is full."""
        view = GameView(game_id="test-game-id", is_full=True)
        assert view.is_full is True
        assert view.join_button.disabled is True
        assert view.leave_button.disabled is False

    @pytest.mark.asyncio
    async def test_initializes_with_started_game(self, event_loop):
        """Test GameView when game has started."""
        view = GameView(game_id="test-game-id", is_started=True)
        assert view.is_started is True
        assert view.join_button.disabled is True
        assert view.leave_button.disabled is True

    @pytest.mark.asyncio
    async def test_buttons_have_correct_custom_ids(self, event_loop):
        """Test that buttons have correct custom IDs."""
        game_id = "12345678-1234-1234-1234-123456789abc"
        view = GameView(game_id=game_id)
        assert view.join_button.custom_id == f"join_game_{game_id}"
        assert view.leave_button.custom_id == f"leave_game_{game_id}"

    @pytest.mark.asyncio
    async def test_join_button_has_correct_style(self, event_loop):
        """Test join button styling."""
        view = GameView(game_id="test-id")
        # discord.ButtonStyle.success is value 3
        assert view.join_button.style.value == 3
        assert view.join_button.label == "Join Game"
        assert view.join_button.emoji.name == "✅"

    @pytest.mark.asyncio
    async def test_leave_button_has_correct_style(self, event_loop):
        """Test leave button styling."""
        view = GameView(game_id="test-id")
        # discord.ButtonStyle.danger is value 4
        assert view.leave_button.style.value == 4
        assert view.leave_button.label == "Leave Game"
        assert view.leave_button.emoji.name == "❌"

    @pytest.mark.asyncio
    async def test_view_has_no_timeout(self, event_loop):
        """Test that view persists with no timeout."""
        view = GameView(game_id="test-id")
        assert view.timeout is None

    @pytest.mark.asyncio
    async def test_update_button_states_enables_join_when_not_full(self, event_loop):
        """Test updating button states when game has space."""
        view = GameView(game_id="test-id", is_full=True)
        view.update_button_states(is_full=False, is_started=False)
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_update_button_states_disables_join_when_full(self, event_loop):
        """Test updating button states when game is full."""
        view = GameView(game_id="test-id")
        view.update_button_states(is_full=True, is_started=False)
        assert view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_update_button_states_disables_both_when_started(self, event_loop):
        """Test updating button states when game has started."""
        view = GameView(game_id="test-id")
        view.update_button_states(is_full=False, is_started=True)
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_open_game(self, event_loop):
        """Test creating view from game data for open game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=3, max_players=5, status="SCHEDULED"
        )
        assert not view.is_full
        assert not view.is_started
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_full_game(self, event_loop):
        """Test creating view from game data for full game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=5, max_players=5, status="SCHEDULED"
        )
        assert view.is_full
        assert not view.is_started
        assert view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_in_progress_game(self, event_loop):
        """Test creating view from game data for in-progress game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=3, max_players=5, status="IN_PROGRESS"
        )
        assert not view.is_full
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_completed_game(self, event_loop):
        """Test creating view from game data for completed game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=5, max_players=5, status="COMPLETED"
        )
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_cancelled_game(self, event_loop):
        """Test creating view from game data for cancelled game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=2, max_players=5, status="CANCELLED"
        )
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_join_button_callback_defers_response(self, event_loop):
        """Test that join button callback defers interaction."""
        view = GameView(game_id="test-id")
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()

        await view._join_button_callback(interaction)
        interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_button_callback_defers_response(self, event_loop):
        """Test that leave button callback defers interaction."""
        view = GameView(game_id="test-id")
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()

        await view._leave_button_callback(interaction)
        interaction.response.defer.assert_called_once()
