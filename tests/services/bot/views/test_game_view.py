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

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.bot.views.game_view import GameView


class TestGameView:
    """Tests for GameView class."""

    @pytest.mark.asyncio
    async def test_initializes_with_default_values(self):
        """Test GameView initialization with default values."""
        view = GameView(game_id="test-game-id")
        assert view.game_id == "test-game-id"
        assert view.is_full is False
        assert view.is_started is False
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_initializes_with_full_game(self):
        """Test GameView when game is full.

        Note: With waitlist support, join button remains enabled even when full.
        """
        view = GameView(game_id="test-game-id", is_full=True)
        assert view.is_full is True
        assert view.join_button.disabled is False  # Waitlist allows joining when full
        assert view.leave_button.disabled is False

    @pytest.mark.asyncio
    async def test_initializes_with_started_game(self):
        """Test GameView when game has started."""
        view = GameView(game_id="test-game-id", is_started=True)
        assert view.is_started is True
        assert view.join_button.disabled is True
        assert view.leave_button.disabled is True

    @pytest.mark.asyncio
    async def test_buttons_have_correct_custom_ids(self):
        """Test that buttons have correct custom IDs."""
        game_id = "12345678-1234-1234-1234-123456789abc"
        view = GameView(game_id=game_id)
        assert view.join_button.custom_id == f"join_game_{game_id}"
        assert view.leave_button.custom_id == f"leave_game_{game_id}"

    @pytest.mark.asyncio
    async def test_join_button_has_correct_style(self):
        """Test join button styling."""
        view = GameView(game_id="test-id")
        # discord.ButtonStyle.success is value 3
        assert view.join_button.style.value == 3
        assert view.join_button.label == "Join Game"

    @pytest.mark.asyncio
    async def test_leave_button_has_correct_style(self):
        """Test leave button styling."""
        view = GameView(game_id="test-id")
        # discord.ButtonStyle.danger is value 4
        assert view.leave_button.style.value == 4
        assert view.leave_button.label == "Leave Game"

    @pytest.mark.asyncio
    async def test_view_has_no_timeout(self):
        """Test that view persists with no timeout."""
        view = GameView(game_id="test-id")
        assert view.timeout is None

    @pytest.mark.asyncio
    async def test_update_button_states_enables_join_when_not_full(self):
        """Test updating button states when game has space."""
        view = GameView(game_id="test-id", is_full=True)
        view.update_button_states(is_full=False, is_started=False)
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_update_button_states_disables_join_when_full(self):
        """Test updating button states when game is full.

        Note: With waitlist support, join button remains enabled even when full.
        """
        view = GameView(game_id="test-id")
        view.update_button_states(is_full=True, is_started=False)
        assert not view.join_button.disabled  # Waitlist allows joining when full
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_update_button_states_disables_both_when_started(self):
        """Test updating button states when game has started."""
        view = GameView(game_id="test-id")
        view.update_button_states(is_full=False, is_started=True)
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_open_game(self):
        """Test creating view from game data for open game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=3, max_players=5, status="SCHEDULED"
        )
        assert not view.is_full
        assert not view.is_started
        assert not view.join_button.disabled
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_full_game(self):
        """Test creating view from game data for full game.

        Note: With waitlist support, join button remains enabled even when full.
        """
        view = GameView.from_game_data(
            game_id="test-id", current_players=5, max_players=5, status="SCHEDULED"
        )
        assert view.is_full
        assert not view.is_started
        assert not view.join_button.disabled  # Waitlist allows joining when full
        assert not view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_in_progress_game(self):
        """Test creating view from game data for in-progress game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=3, max_players=5, status="IN_PROGRESS"
        )
        assert not view.is_full
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_completed_game(self):
        """Test creating view from game data for completed game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=5, max_players=5, status="COMPLETED"
        )
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_creates_view_for_cancelled_game(self):
        """Test creating view from game data for cancelled game."""
        view = GameView.from_game_data(
            game_id="test-id", current_players=2, max_players=5, status="CANCELLED"
        )
        assert view.is_started
        assert view.join_button.disabled
        assert view.leave_button.disabled

    @pytest.mark.asyncio
    async def test_join_button_callback_defers_response(self):
        """Test that join button callback defers interaction."""
        view = GameView(game_id="test-id")
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()

        await view._join_button_callback(interaction)
        interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_button_callback_defers_response(self):
        """Test that leave button callback defers interaction."""
        view = GameView(game_id="test-id")
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()

        await view._leave_button_callback(interaction)
        interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_initializes_with_self_signup_method(self):
        """Test GameView with SELF_SIGNUP method enables join button."""
        from shared.models.signup_method import SignupMethod

        view = GameView(game_id="test-game-id", signup_method=SignupMethod.SELF_SIGNUP.value)
        assert view.signup_method == SignupMethod.SELF_SIGNUP.value
        assert not view.join_button.disabled

    @pytest.mark.asyncio
    async def test_initializes_with_host_selected_method(self):
        """Test GameView with HOST_SELECTED method disables join button."""
        from shared.models.signup_method import SignupMethod

        view = GameView(game_id="test-game-id", signup_method=SignupMethod.HOST_SELECTED.value)
        assert view.signup_method == SignupMethod.HOST_SELECTED.value
        assert view.join_button.disabled

    @pytest.mark.asyncio
    async def test_host_selected_overrides_other_states(self):
        """Test HOST_SELECTED disables join button even when game has space."""
        from shared.models.signup_method import SignupMethod

        view = GameView(
            game_id="test-game-id",
            is_full=False,
            is_started=False,
            signup_method=SignupMethod.HOST_SELECTED.value,
        )
        assert not view.is_full
        assert not view.is_started
        assert view.join_button.disabled  # Still disabled due to signup method

    @pytest.mark.asyncio
    async def test_from_game_data_with_self_signup(self):
        """Test creating view from game data with SELF_SIGNUP method."""
        from shared.models.signup_method import SignupMethod

        view = GameView.from_game_data(
            game_id="test-id",
            current_players=3,
            max_players=5,
            status="SCHEDULED",
            signup_method=SignupMethod.SELF_SIGNUP.value,
        )
        assert not view.join_button.disabled

    @pytest.mark.asyncio
    async def test_from_game_data_with_host_selected(self):
        """Test creating view from game data with HOST_SELECTED method."""
        from shared.models.signup_method import SignupMethod

        view = GameView.from_game_data(
            game_id="test-id",
            current_players=3,
            max_players=5,
            status="SCHEDULED",
            signup_method=SignupMethod.HOST_SELECTED.value,
        )
        assert view.join_button.disabled
        assert not view.leave_button.disabled  # Leave always enabled when not started

    @pytest.mark.asyncio
    async def test_host_selected_leave_button_always_enabled_when_not_started(self):
        """Test HOST_SELECTED games allow players to leave via button."""
        from shared.models.signup_method import SignupMethod

        view = GameView(
            game_id="test-game-id",
            is_full=True,
            is_started=False,
            signup_method=SignupMethod.HOST_SELECTED.value,
        )
        assert view.join_button.disabled  # Can't self-join
        assert not view.leave_button.disabled  # Can self-leave

    @pytest.mark.asyncio
    async def test_update_button_states_with_host_selected_method(self):
        """Test updating button states with HOST_SELECTED method."""
        from shared.models.signup_method import SignupMethod

        view = GameView(game_id="test-id", signup_method=SignupMethod.SELF_SIGNUP.value)
        assert not view.join_button.disabled

        view.update_button_states(
            is_full=False,
            is_started=False,
            signup_method=SignupMethod.HOST_SELECTED.value,
        )
        assert view.join_button.disabled
        assert not view.leave_button.disabled
