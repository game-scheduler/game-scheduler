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


"""Tests for game utilities."""

from shared.utils.games import DEFAULT_MAX_PLAYERS, resolve_max_players


class TestResolveMaxPlayers:
    """Tests for resolve_max_players utility function."""

    def test_resolve_max_players_with_value(self):
        """Test that resolve_max_players returns the value when provided."""

        assert resolve_max_players(5) == 5
        assert resolve_max_players(1) == 1
        assert resolve_max_players(100) == 100

    def test_resolve_max_players_with_none(self):
        """Test that resolve_max_players defaults to DEFAULT_MAX_PLAYERS when None."""

        assert resolve_max_players(None) == DEFAULT_MAX_PLAYERS

    def test_resolve_max_players_with_zero(self):
        """Test that resolve_max_players treats 0 as falsy and defaults."""

        # 0 is falsy, so it defaults to DEFAULT_MAX_PLAYERS
        result = resolve_max_players(0)
        assert result == DEFAULT_MAX_PLAYERS

    def test_resolve_max_players_default_value_is_10(self):
        """Test that the default value is 10."""

        assert resolve_max_players(None) == 10
        assert DEFAULT_MAX_PLAYERS == 10
