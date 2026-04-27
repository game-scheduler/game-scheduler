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


"""Unit tests for the participant drop bot handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.handlers.participant_drop import handle_participant_drop_due


def _make_participant(discord_id: str = "123456789", game_title: str = "Test Game") -> MagicMock:
    user = MagicMock()
    user.discord_id = discord_id

    game = MagicMock()
    game.title = game_title
    game.guild_id = "guild_1"

    participant = MagicMock()
    participant.user = user
    participant.game = game
    return participant


def _make_db_session(participant: MagicMock | None) -> MagicMock:
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = participant
    db.execute.return_value = scalar_result
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestHandleParticipantDropDue:
    """Tests for handle_participant_drop_due."""

    @pytest.mark.asyncio
    async def test_uses_get_user_not_fetch_user(self):
        """Must use bot.get_user() (cache) instead of bot.fetch_user() (REST)."""
        participant = _make_participant(discord_id="111222333")
        db = _make_db_session(participant)
        db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": participant}),
            MagicMock(**{"scalar_one_or_none.return_value": None}),
        ]

        mock_user = MagicMock()
        mock_user.send = AsyncMock()

        bot = MagicMock()
        bot.get_user = MagicMock(return_value=mock_user)
        bot.fetch_user = AsyncMock()

        publisher = MagicMock()
        publisher.publish_game_updated = AsyncMock()

        with patch("services.bot.handlers.participant_drop.get_bypass_db_session") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await handle_participant_drop_due(
                {"game_id": "g1", "participant_id": "p1"}, bot, publisher
            )

        bot.get_user.assert_called_once_with(111222333)
        bot.fetch_user.assert_not_awaited()
        mock_user.send.assert_awaited_once()
        assert mock_ctx.call_count == 1
