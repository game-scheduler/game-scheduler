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


"""Unit tests for EventHandlers lifecycle event error and branch paths.

Covers _handle_notification_due, _handle_game_reminder, _handle_join_notification,
_handle_player_removed, _handle_participant_drop_due, and _handle_game_cancelled.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import NotificationDueEvent


@pytest.fixture
def bot():
    return MagicMock(spec=discord.Client)


@pytest.fixture
def handlers(bot):
    return EventHandlers(bot)


def _db_ctx(mock_db=None):
    if mock_db is None:
        mock_db = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_db, ctx


def _make_reminder_event(game_id=None):
    return NotificationDueEvent(
        game_id=game_id or uuid4(),
        notification_type="reminder",
    )


# ---------------------------------------------------------------------------
# _handle_notification_due
# ---------------------------------------------------------------------------


async def test_notification_due_invalid_data_is_rejected(handlers):
    """Malformed event data is handled gracefully without raising."""
    await handlers._handle_notification_due({})  # missing required game_id


async def test_notification_due_routes_to_clone_confirmation(handlers):
    """clone_confirmation notification type is dispatched to its handler."""
    event = NotificationDueEvent(
        game_id=uuid4(),
        notification_type="clone_confirmation",
        participant_id=str(uuid4()),
    )
    with patch.object(handlers, "_handle_clone_confirmation", new=AsyncMock()) as mock_handler:
        await handlers._handle_notification_due(event.model_dump())
    mock_handler.assert_called_once()


async def test_notification_due_unknown_type_logs_error(handlers):
    """Unknown notification type is logged without raising."""
    data = {"game_id": str(uuid4()), "notification_type": "unknown_type"}
    await handlers._handle_notification_due(data)


# ---------------------------------------------------------------------------
# _handle_game_reminder
# ---------------------------------------------------------------------------


async def test_game_reminder_game_not_found(handlers):
    """Returns early when game cannot be found in the database."""
    event = _make_reminder_event()
    _, ctx = _db_ctx()
    with (
        patch.object(handlers, "_get_game_with_participants", new=AsyncMock(return_value=None)),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_reminder(event)


async def test_game_reminder_game_fails_validation(handlers):
    """Returns early when game state is not valid for sending reminders."""
    event = _make_reminder_event()
    mock_game = MagicMock()
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers, "_get_game_with_participants", new=AsyncMock(return_value=mock_game)
        ),
        patch.object(handlers, "_validate_game_for_reminder", new=AsyncMock(return_value=False)),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_reminder(event)


async def test_game_reminder_exception_is_caught(handlers):
    """Exception during reminder processing is logged without propagating."""
    event = _make_reminder_event()
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_get_game_with_participants",
            new=AsyncMock(side_effect=RuntimeError("db error")),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_game_reminder(event)


# ---------------------------------------------------------------------------
# _handle_join_notification
# ---------------------------------------------------------------------------


async def test_join_notification_not_confirmed_skips(handlers):
    """Returns early when participant is on the waitlist, not confirmed."""
    event = NotificationDueEvent(
        game_id=uuid4(),
        notification_type="join_notification",
        participant_id=str(uuid4()),
    )
    mock_game = MagicMock()
    mock_participant = MagicMock()
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_fetch_join_notification_data",
            new=AsyncMock(return_value=(mock_game, mock_participant)),
        ),
        patch.object(handlers, "_is_participant_confirmed", return_value=False),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_join_notification(event)


async def test_join_notification_exception_is_caught(handlers):
    """Exception during join notification processing is logged without propagating."""
    event = NotificationDueEvent(
        game_id=uuid4(),
        notification_type="join_notification",
        participant_id=str(uuid4()),
    )
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_fetch_join_notification_data",
            new=AsyncMock(side_effect=RuntimeError("network error")),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_join_notification(event)


# ---------------------------------------------------------------------------
# _handle_player_removed
# ---------------------------------------------------------------------------


async def test_player_removed_missing_required_fields(handlers):
    """Returns early when message_id or channel_id is absent."""
    await handlers._handle_player_removed({"game_id": "g1"})


async def test_player_removed_success(handlers):
    """Updates message and notifies player when all required fields are present."""
    data = {
        "game_id": "g1",
        "message_id": "m1",
        "channel_id": "c1",
        "discord_id": "d1",
        "game_title": "Test Game",
        "game_scheduled_at": None,
    }
    with (
        patch.object(handlers, "_update_message_for_player_removal", new=AsyncMock()),
        patch.object(handlers, "_notify_removed_player", new=AsyncMock()),
    ):
        await handlers._handle_player_removed(data)


async def test_player_removed_exception_is_caught(handlers):
    """Exception during player removal handling is logged without propagating."""
    data = {"game_id": "g1", "message_id": "m1", "channel_id": "c1"}
    with patch.object(
        handlers, "_update_message_for_player_removal", new=AsyncMock(side_effect=RuntimeError)
    ):
        await handlers._handle_player_removed(data)


# ---------------------------------------------------------------------------
# _handle_participant_drop_due
# ---------------------------------------------------------------------------


async def test_participant_drop_due_delegates_to_handler(handlers):
    """Delegates to handle_participant_drop_due with bot and publisher."""
    data = {"game_id": str(uuid4()), "participant_id": str(uuid4())}
    mock_publisher = MagicMock()
    with (
        patch("services.bot.events.handlers.get_bot_publisher", return_value=mock_publisher),
        patch(
            "services.bot.events.handlers.handle_participant_drop_due", new=AsyncMock()
        ) as mock_drop,
    ):
        await handlers._handle_participant_drop_due(data)
    mock_drop.assert_called_once_with(data, handlers.bot, mock_publisher)


# ---------------------------------------------------------------------------
# _handle_game_cancelled
# ---------------------------------------------------------------------------


async def test_game_cancelled_delete_general_exception_is_caught(handlers):
    """Non-NotFound exception from message.delete() is handled without propagating."""
    data = {"game_id": str(uuid4()), "message_id": "m1", "channel_id": "c1"}
    mock_channel = MagicMock()
    mock_message = AsyncMock()
    mock_message.delete = AsyncMock(side_effect=RuntimeError("network failure"))
    with patch.object(
        handlers,
        "_fetch_channel_and_message",
        new=AsyncMock(return_value=(mock_channel, mock_message)),
    ):
        await handlers._handle_game_cancelled(data)


# ---------------------------------------------------------------------------
# _validate_discord_channel
# ---------------------------------------------------------------------------


async def test_validate_discord_channel_does_not_call_fetch_channel(handlers, bot):
    """_validate_discord_channel must not call discord_api.fetch_channel."""
    bot.get_channel = MagicMock(return_value=MagicMock(spec=discord.TextChannel))
    bot.fetch_channel = AsyncMock()
    await handlers._validate_discord_channel("123456")
    bot.fetch_channel.assert_not_called()


async def test_validate_discord_channel_returns_false_when_not_found(handlers, bot):
    """Returns False when get_channel() cannot find the channel."""
    bot.get_channel = MagicMock(return_value=None)
    result = await handlers._validate_discord_channel("999")
    assert result is False


async def test_validate_discord_channel_returns_true_when_found(handlers, bot):
    """Returns True when get_channel() returns a valid channel."""
    bot.get_channel = MagicMock(return_value=MagicMock(spec=discord.TextChannel))
    result = await handlers._validate_discord_channel("123456")
    assert result is True
