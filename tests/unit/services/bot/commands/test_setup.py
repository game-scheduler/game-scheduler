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


"""Tests for command setup module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.commands import list_games, my_games
from services.bot.commands.setup import setup_commands


class TestSetupCommands:
    """Tests for setup_commands function."""

    @pytest.mark.asyncio
    async def test_setup_commands_registers_all_commands(self) -> None:
        """Test that setup_commands calls setup on both list_games and my_games."""
        mock_bot = MagicMock()
        mock_list_setup = AsyncMock()
        mock_my_setup = AsyncMock()

        with (
            patch.object(list_games, "setup", mock_list_setup),
            patch.object(my_games, "setup", mock_my_setup),
        ):
            await setup_commands(mock_bot)

        mock_list_setup.assert_awaited_once_with(mock_bot)
        mock_my_setup.assert_awaited_once_with(mock_bot)
