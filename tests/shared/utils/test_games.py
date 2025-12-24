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


"""Tests for game utilities."""


class TestResolveMaxPlayers:
    """Tests for resolve_max_players utility function."""

    def test_resolve_max_players_with_value(self):
        """Test that resolve_max_players returns the value when provided."""
        from shared.utils.games import resolve_max_players

        assert resolve_max_players(5) == 5
        assert resolve_max_players(1) == 1
        assert resolve_max_players(100) == 100

    def test_resolve_max_players_with_none(self):
        """Test that resolve_max_players defaults to DEFAULT_MAX_PLAYERS when None."""
        from shared.utils.games import DEFAULT_MAX_PLAYERS, resolve_max_players

        assert resolve_max_players(None) == DEFAULT_MAX_PLAYERS

    def test_resolve_max_players_with_zero(self):
        """Test that resolve_max_players treats 0 as falsy and defaults."""
        from shared.utils.games import DEFAULT_MAX_PLAYERS, resolve_max_players

        # 0 is falsy, so it defaults to DEFAULT_MAX_PLAYERS
        result = resolve_max_players(0)
        assert result == DEFAULT_MAX_PLAYERS

    def test_resolve_max_players_default_value_is_10(self):
        """Test that the default value is 10."""
        from shared.utils.games import DEFAULT_MAX_PLAYERS, resolve_max_players

        assert resolve_max_players(None) == 10
        assert DEFAULT_MAX_PLAYERS == 10
