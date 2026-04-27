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


"""Unit tests for CloneConfirmationView button interactions."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.publisher import BotEventPublisher
from services.bot.views.clone_confirmation_view import CloneConfirmationView
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.models.participant_action_schedule import ParticipantActionSchedule
from shared.models.user import User


@pytest.fixture
def schedule_id():
    return str(uuid4())


@pytest.fixture
def game_id():
    return str(uuid4())


@pytest.fixture
def participant_id():
    return str(uuid4())


@pytest.fixture
def mock_publisher():
    publisher = MagicMock(spec=BotEventPublisher)
    publisher.publish_game_updated = AsyncMock()
    return publisher


@pytest.fixture
async def view(schedule_id, game_id, participant_id, mock_publisher):
    return CloneConfirmationView(
        schedule_id=schedule_id,
        game_id=game_id,
        participant_id=participant_id,
        publisher=mock_publisher,
    )


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.client = MagicMock(spec=discord.Client)
    return interaction


def _make_mock_db(mock_schedule):
    """Build an AsyncMock DB session returning the given schedule record."""
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=mock_schedule)
    mock_db.execute = AsyncMock(return_value=result)
    return mock_db


def _patch_db(mock_db, module_path):
    """Return a context manager that patches get_db_session with mock_db."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch(module_path, return_value=ctx)


@pytest.mark.asyncio
async def test_confirm_button_deletes_participant_action_schedule(
    view, mock_interaction, schedule_id
):
    """Confirm callback must delete the ParticipantActionSchedule record and commit."""
    mock_schedule = MagicMock(spec=ParticipantActionSchedule)
    mock_schedule.id = schedule_id
    mock_db = _make_mock_db(mock_schedule)

    with _patch_db(mock_db, "services.bot.views.clone_confirmation_view.get_db_session"):
        await view._confirm_callback(mock_interaction)

    mock_db.delete.assert_called_once_with(mock_schedule)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_button_sends_pg_notify(view, mock_interaction, schedule_id):
    """Confirm callback must send NOTIFY participant_action_schedule_changed after deleting."""
    mock_schedule = MagicMock(spec=ParticipantActionSchedule)
    mock_schedule.id = schedule_id

    # Use a separate execute mock to capture both the SELECT and the NOTIFY calls
    notify_executed = []

    async def fake_execute(stmt, *args, **kwargs):
        compiled = str(stmt)
        if "participant_action_schedule_changed" in compiled:
            notify_executed.append(compiled)
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_schedule)
        return result

    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.execute = fake_execute
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("services.bot.views.clone_confirmation_view.get_db_session", return_value=ctx):
        await view._confirm_callback(mock_interaction)

    assert notify_executed, "pg_notify for participant_action_schedule_changed was not called"


@pytest.mark.asyncio
async def test_decline_button_calls_drop_handler(
    view, mock_interaction, game_id, participant_id, mock_publisher
):
    """Decline callback must invoke handle_participant_drop_due with correct data."""
    with patch(
        "services.bot.views.clone_confirmation_view.handle_participant_drop_due",
        new_callable=AsyncMock,
    ) as mock_drop:
        await view._decline_callback(mock_interaction)

    mock_drop.assert_called_once()
    call_args = mock_drop.call_args
    event_data = call_args.args[0] if call_args.args else call_args.kwargs.get("data")
    assert event_data["game_id"] == game_id
    assert event_data["participant_id"] == participant_id


@pytest.mark.asyncio
async def test_decline_path_removes_participant_and_publishes_game_updated(
    view, mock_interaction, game_id, participant_id, mock_publisher
):
    """Full decline path: decline → drop handler → participant deleted → GAME_UPDATED published."""
    mock_game = MagicMock(spec=GameSession)
    mock_game.id = game_id
    mock_game.title = "Drop Test Game"
    mock_game.guild_id = "guild-db-uuid-test"

    mock_participant = MagicMock(spec=GameParticipant)
    mock_participant.id = participant_id
    mock_participant.game = mock_game
    mock_participant.user = MagicMock(spec=User)
    mock_participant.user.discord_id = "123456789012345678"

    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none = MagicMock(return_value=mock_participant)
    mock_db.execute = AsyncMock(return_value=db_result)

    drop_db_ctx = MagicMock()
    drop_db_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    drop_db_ctx.__aexit__ = AsyncMock(return_value=False)

    discord_user = AsyncMock()
    discord_user.send = AsyncMock()
    mock_interaction.client.fetch_user = AsyncMock(return_value=discord_user)

    with patch(
        "services.bot.handlers.participant_drop.get_bypass_db_session",
        return_value=drop_db_ctx,
    ):
        await view._decline_callback(mock_interaction)

    mock_db.delete.assert_called_once_with(mock_participant)
    mock_db.commit.assert_called_once()
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=game_id, guild_id="guild-db-uuid-test", updated_fields={"participants": True}
    )
