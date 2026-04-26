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


"""Unit tests for EventHandlers clone confirmation methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.messaging.events import NotificationDueEvent


@pytest.mark.asyncio
async def test_handle_clone_confirmation_sends_dm_with_view(event_handlers, mock_bot, sample_game):
    """_handle_clone_confirmation sends a DM with CloneConfirmationView when schedule exists."""
    participant_id = str(uuid4())
    participant = MagicMock()
    participant.id = participant_id
    participant.user = MagicMock()
    participant.user.discord_id = "555000000000000001"

    schedule = MagicMock()
    schedule.id = str(uuid4())
    schedule.action_time = datetime(2026, 4, 1, 18, 0, 0, tzinfo=UTC)

    mock_user = MagicMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user

    event = NotificationDueEvent(
        game_id=sample_game.id,
        notification_type="clone_confirmation",
        participant_id=participant_id,
    )

    mock_db_instance = MagicMock()
    schedule_result = MagicMock()
    schedule_result.scalar_one_or_none = MagicMock(return_value=schedule)
    mock_db_instance.execute = AsyncMock(return_value=schedule_result)

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_join_notification_data",
            new_callable=AsyncMock,
            return_value=(sample_game, participant),
        ),
        patch("services.bot.events.handlers.get_bot_publisher"),
        patch("services.bot.events.handlers.CloneConfirmationView") as mock_view_cls,
        patch("services.bot.events.handlers.DMFormats") as mock_fmt,
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_fmt.clone_confirmation.return_value = "Clone confirmation DM text"

        await event_handlers._handle_clone_confirmation(event)

    mock_bot.fetch_user.assert_not_called()
    mock_view_cls.assert_called_once()
    mock_user.send.assert_awaited_once()
    send_kwargs = mock_user.send.call_args
    assert send_kwargs[1]["view"] is mock_view_cls.return_value


@pytest.mark.asyncio
async def test_handle_clone_confirmation_skips_when_participant_not_found(event_handlers, mock_bot):
    """_handle_clone_confirmation returns early when participant is not found."""
    event = NotificationDueEvent(
        game_id=str(uuid4()),
        notification_type="clone_confirmation",
        participant_id=str(uuid4()),
    )

    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_join_notification_data",
            new_callable=AsyncMock,
            return_value=(None, None),
        ),
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        await event_handlers._handle_clone_confirmation(event)

    mock_bot.fetch_user.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clone_confirmation_falls_back_to_join_dm_when_no_schedule(
    event_handlers, mock_bot, sample_game
):
    """_handle_clone_confirmation sends a plain join DM when no ParticipantActionSchedule."""
    participant_id = str(uuid4())
    participant = MagicMock()
    participant.id = participant_id
    participant.user = MagicMock()
    participant.user.discord_id = "555000000000000002"

    event = NotificationDueEvent(
        game_id=sample_game.id,
        notification_type="clone_confirmation",
        participant_id=participant_id,
    )

    mock_db_instance = MagicMock()
    no_schedule_result = MagicMock()
    no_schedule_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db_instance.execute = AsyncMock(return_value=no_schedule_result)

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_join_notification_data",
            new_callable=AsyncMock,
            return_value=(sample_game, participant),
        ),
        patch.object(
            event_handlers,
            "_send_join_notification_dm",
            new_callable=AsyncMock,
        ) as mock_send_join,
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        await event_handlers._handle_clone_confirmation(event)

    mock_send_join.assert_awaited_once()
    mock_bot.fetch_user.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clone_confirmation_user_not_in_cache(event_handlers, mock_bot, sample_game):
    """_handle_clone_confirmation skips DM when user is absent from gateway cache."""
    participant_id = str(uuid4())
    participant = MagicMock()
    participant.id = participant_id
    participant.user = MagicMock()
    participant.user.discord_id = "555000000000000099"

    schedule = MagicMock()
    schedule.id = str(uuid4())
    schedule.action_time = datetime(2026, 4, 1, 18, 0, 0, tzinfo=UTC)

    mock_bot.get_user.return_value = None

    event = NotificationDueEvent(
        game_id=sample_game.id,
        notification_type="clone_confirmation",
        participant_id=participant_id,
    )

    mock_db_instance = MagicMock()
    schedule_result = MagicMock()
    schedule_result.scalar_one_or_none = MagicMock(return_value=schedule)
    mock_db_instance.execute = AsyncMock(return_value=schedule_result)

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_join_notification_data",
            new_callable=AsyncMock,
            return_value=(sample_game, participant),
        ),
        patch("services.bot.events.handlers.get_bot_publisher"),
        patch("services.bot.events.handlers.CloneConfirmationView"),
        patch("services.bot.events.handlers.DMFormats") as mock_fmt,
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_fmt.clone_confirmation.return_value = "Clone confirmation DM text"

        await event_handlers._handle_clone_confirmation(event)

    mock_bot.fetch_user.assert_not_called()
