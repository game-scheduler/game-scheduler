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


"""Unit tests for the leave game bot handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.handlers import leave_game as leave_game_module


def _make_leave_interaction(nick=None, global_name=None, name="username", avatar_url=None):
    interaction = MagicMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 55555
    interaction.user.nick = nick
    interaction.user.global_name = global_name
    interaction.user.name = name
    if avatar_url:
        mock_avatar = MagicMock()
        mock_avatar.url = avatar_url
        interaction.user.display_avatar = mock_avatar
    else:
        interaction.user.display_avatar = None
    interaction.user.guild = MagicMock()
    interaction.user.guild.id = 88888
    return interaction


class TestLeaveGameUpsertDisplayName:
    """Tests verifying UserDisplayNameService.upsert_one is called on leave."""

    @pytest.mark.asyncio
    async def test_upsert_called_after_successful_leave(self):
        """handle_leave_game calls upsert_one with interaction.user data on success."""
        interaction = _make_leave_interaction(global_name="GlobalBob", avatar_url=None)
        publisher = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(**{"scalar_one_or_none.return_value": None})
        )
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        game = MagicMock()
        game.guild_id = "88888"
        game.title = "Test Game"

        mock_participant = MagicMock()
        mock_participant.id = "pid2"

        validate_result = {
            "can_leave": True,
            "game": game,
            "participant_count": 2,
            "participant": mock_participant,
            "error": None,
        }

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_db
        async_cm.__aexit__.return_value = None

        with (
            patch("services.bot.handlers.leave_game.get_db_session", return_value=async_cm),
            patch(
                "services.bot.handlers.leave_game._validate_leave_game",
                new=AsyncMock(return_value=validate_result),
            ),
            patch("services.bot.handlers.leave_game.send_success_message", new=AsyncMock()),
            patch("services.bot.handlers.utils.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc.upsert_one = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await leave_game_module.handle_leave_game(
                interaction, "00000000-0000-0000-0000-000000000002", publisher
            )

        mock_svc.upsert_one.assert_awaited_once_with(
            str(interaction.user.id),
            str(interaction.user.guild.id),
            "GlobalBob",
            None,
        )
