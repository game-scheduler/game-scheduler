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


"""Unit tests for EventHandlers._handle_game_updated."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models.message_refresh_queue import MessageRefreshQueue


@pytest.mark.asyncio
async def test_handle_game_updated_inserts_queue_row(
    event_handlers, mock_bot, sample_game, sample_user
):
    """Test game.updated event upserts a row into message_refresh_queue."""
    sample_game.host = sample_user
    sample_game.participants = []

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db_session,
        patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ),
    ):
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await event_handlers._handle_game_updated({"game_id": sample_game.id})

    # Write path uses execute() with an upsert statement (not session.add)
    mock_db.execute.assert_awaited_once()
    queue_rows_via_add = [
        call.args[0]
        for call in mock_db.add.call_args_list
        if isinstance(call.args[0], MessageRefreshQueue)
    ]
    assert len(queue_rows_via_add) == 0
