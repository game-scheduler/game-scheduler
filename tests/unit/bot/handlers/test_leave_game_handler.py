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

"""Unit tests for handle_leave_game.

Verifies leave DM suppression when the join notification has not been sent yet.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.leave_game import handle_leave_game
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant
from shared.models.user import User

USER_DISCORD_ID = "111222333444555666"


@pytest.fixture
def game_id():
    return str(uuid4())


@pytest.fixture
def participant_db_id():
    return str(uuid4())


@pytest.fixture
def mock_game(game_id):
    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.title = "Leave Test Game"
    game.guild_id = "guild-db-uuid-42"
    game.status = "SCHEDULED"
    return game


@pytest.fixture
def mock_participant(participant_db_id, mock_game):
    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game_session_id = mock_game.id
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = USER_DISCORD_ID
    return participant


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = int(USER_DISCORD_ID)
    interaction.user.send = AsyncMock()
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_publisher():
    publisher = MagicMock(spec=BotEventPublisher)
    publisher.publish_game_updated = AsyncMock()
    return publisher


def _make_mock_db(mock_participant, mock_game, unsent_notification=None):
    """Build a mock DB session for leave_game handler tests.

    _validate_leave_game runs 3 queries (game, user, participant + count).
    The leave handler then runs 1 notification query.
    """
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    game_result = MagicMock()
    game_result.scalar_one_or_none = MagicMock(return_value=mock_game)

    user = MagicMock(spec=User)
    user.id = str(uuid4())
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    participant_result = MagicMock()
    participant_result.scalar_one_or_none = MagicMock(return_value=mock_participant)

    count_result = MagicMock()
    count_result.scalar_one_or_none = MagicMock(return_value=1)

    notif_result = MagicMock()
    notif_result.scalar_one_or_none = MagicMock(return_value=unsent_notification)

    upsert_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            user_result,
            participant_result,
            count_result,
            notif_result,
            upsert_result,
        ]
    )
    return mock_db


def _patch_db(mock_db):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("services.bot.handlers.leave_game.get_db_session", return_value=ctx)


@pytest.mark.asyncio
async def test_leave_sends_dm_when_join_was_already_sent(
    mock_game, mock_participant, mock_interaction, mock_publisher, game_id
):
    """Leave DM is sent when no unsent join notification exists (join DM was delivered)."""
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=None)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id, mock_publisher)

    mock_interaction.user.send.assert_called_once()
    sent_content = (
        mock_interaction.user.send.call_args.kwargs.get("content")
        or mock_interaction.user.send.call_args.args[0]
    )
    assert mock_game.title in sent_content


@pytest.mark.asyncio
async def test_leave_suppresses_dm_when_join_not_yet_sent(
    mock_game, mock_participant, mock_interaction, mock_publisher, game_id
):
    """No leave DM is sent when an unsent join notification still exists."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id, mock_publisher)

    mock_interaction.user.send.assert_not_called()


@pytest.mark.asyncio
async def test_leave_deletes_participant_regardless_of_notification(
    mock_game, mock_participant, mock_interaction, mock_publisher, game_id
):
    """Participant is always deleted even when the leave DM is suppressed."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id, mock_publisher)

    mock_db.delete.assert_called_once_with(mock_participant)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_leave_publishes_game_updated_regardless_of_notification(
    mock_game, mock_participant, mock_interaction, mock_publisher, game_id
):
    """GAME_UPDATED is always published even when the leave DM is suppressed."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id, mock_publisher)

    mock_publisher.publish_game_updated.assert_called_once()
