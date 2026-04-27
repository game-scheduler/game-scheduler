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


"""Unit tests for handle_participant_drop_due.

Verifies the handler correctly removes the participant from the DB,
sends a removal DM, and publishes GAME_UPDATED.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.participant_drop import handle_participant_drop_due
from shared.message_formats import DMFormats
from shared.messaging.events import EventType
from shared.models import GameStatus
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant
from shared.models.user import User

PARTICIPANT_DISCORD_ID = "123456789012345678"


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
    game.title = "Drop Test Game"
    game.guild_id = "guild-db-uuid-999"
    game.guild = MagicMock()
    game.guild.guild_id = "999888777666555444"
    return game


@pytest.fixture
def mock_participant(participant_db_id, mock_game):
    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game_session_id = mock_game.id
    participant.game = mock_game
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = PARTICIPANT_DISCORD_ID
    return participant


@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=discord.Client)
    discord_user = MagicMock()
    discord_user.send = AsyncMock()
    bot.get_user = MagicMock(return_value=discord_user)
    return bot


@pytest.fixture
def mock_publisher():
    publisher = MagicMock(spec=BotEventPublisher)
    publisher.publish_game_updated = AsyncMock()
    return publisher


@pytest.fixture
def drop_event_data(game_id, participant_db_id):
    return {"game_id": game_id, "participant_id": participant_db_id}


def _make_mock_db(mock_participant, notification_schedule: NotificationSchedule | None = None):
    """Build an AsyncMock DB session that returns the given participant.

    notification_schedule: unsent NotificationSchedule to simulate (None = no pending notification).
    """
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    participant_result = MagicMock()
    participant_result.scalar_one_or_none = MagicMock(return_value=mock_participant)

    notif_result = MagicMock()
    notif_result.scalar_one_or_none = MagicMock(return_value=notification_schedule)

    mock_db.execute = AsyncMock(side_effect=[participant_result, notif_result])
    return mock_db


def _patch_db(mock_db):
    """Return context manager that patches get_db_session with mock_db."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("services.bot.handlers.participant_drop.get_bypass_db_session", return_value=ctx)


@pytest.mark.asyncio
async def test_handler_deletes_participant(
    mock_game, mock_participant, mock_bot, mock_publisher, drop_event_data
):
    """Handler must delete the participant record and commit the session."""
    mock_db = _make_mock_db(mock_participant)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_db.delete.assert_called_once_with(mock_participant)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handler_sends_removal_dm(
    mock_game, mock_participant, mock_bot, mock_publisher, drop_event_data
):
    """Handler must send DMFormats.removal to the participant's Discord user."""
    mock_db = _make_mock_db(mock_participant)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_bot.get_user.assert_called_once_with(int(PARTICIPANT_DISCORD_ID))
    discord_user = mock_bot.get_user(int(PARTICIPANT_DISCORD_ID))
    expected_msg = DMFormats.removal(mock_game.title)
    discord_user.send.assert_called_once_with(expected_msg)


@pytest.mark.asyncio
async def test_handler_publishes_game_updated(
    mock_game, mock_participant, mock_bot, mock_publisher, drop_event_data
):
    """Handler must publish GAME_UPDATED after removing the participant."""
    mock_db = _make_mock_db(mock_participant)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_publisher.publish_game_updated.assert_called_once()
    call_kwargs = mock_publisher.publish_game_updated.call_args
    called_game_id = call_kwargs.kwargs.get("game_id") or (
        call_kwargs.args[0] if call_kwargs.args else None
    )
    assert called_game_id == mock_game.id


@pytest.mark.asyncio
async def test_handler_skips_when_participant_not_found(mock_bot, mock_publisher, drop_event_data):
    """Handler must return silently when participant no longer exists."""
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=result)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_db.delete.assert_not_called()
    mock_bot.get_user.assert_not_called()
    mock_publisher.publish_game_updated.assert_not_called()


@pytest.mark.asyncio
async def test_handler_drops_participant_from_cancelled_game(
    mock_bot, mock_publisher, drop_event_data, participant_db_id, game_id
):
    """Handler must remove participant even when the source game is cancelled."""
    cancelled_game = MagicMock(spec=GameSession)
    cancelled_game.id = game_id
    cancelled_game.title = "Cancelled Game"
    cancelled_game.guild_id = "guild-db-uuid-cancelled"
    cancelled_game.status = GameStatus.CANCELLED

    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game = cancelled_game
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = PARTICIPANT_DISCORD_ID

    mock_db = _make_mock_db(participant)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_db.delete.assert_called_once_with(participant)
    mock_db.commit.assert_called_once()
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=ANY, guild_id=ANY, updated_fields=ANY
    )


@pytest.mark.asyncio
async def test_handler_suppresses_removal_dm_when_welcome_not_sent(
    mock_game, mock_participant, mock_bot, mock_publisher, drop_event_data
):
    """No removal DM when an unsent join/clone notification exists for the participant."""
    unsent_schedule = MagicMock(spec=NotificationSchedule)
    unsent_schedule.sent = False
    mock_db = _make_mock_db(mock_participant, notification_schedule=unsent_schedule)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_db.delete.assert_called_once_with(mock_participant)
    mock_bot.get_user.assert_not_called()
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=ANY, guild_id=ANY, updated_fields=ANY
    )


@pytest.mark.asyncio
async def test_handler_sends_removal_dm_when_welcome_already_sent(
    mock_game, mock_participant, mock_bot, mock_publisher, drop_event_data
):
    """Removal DM is sent when the welcome notification has already been delivered (sent=True)."""
    mock_db = _make_mock_db(mock_participant, notification_schedule=None)

    with _patch_db(mock_db):
        await handle_participant_drop_due(drop_event_data, mock_bot, mock_publisher)

    mock_bot.get_user.assert_called_once_with(int(PARTICIPANT_DISCORD_ID))
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=ANY, guild_id=ANY, updated_fields=ANY
    )


def test_participant_drop_due_is_registered_in_event_handlers():
    """EventHandlers must register PARTICIPANT_DROP_DUE or events are silently dropped.

    This test guards against the class of bug where a handler function exists but is
    never wired into start_consuming, which cannot be caught by direct-call handler tests.
    """
    bot = MagicMock(spec=discord.Client)
    handlers = EventHandlers(bot)

    assert EventType.PARTICIPANT_DROP_DUE in handlers._handlers, (
        "PARTICIPANT_DROP_DUE must be in EventHandlers._handlers — "
        "also verify it is passed to consumer.register_handler in start_consuming"
    )
