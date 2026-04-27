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


"""Unit tests for EventHandlers._handle_status_transition_due and _archive_game_announcement."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from shared.models import GameStatus, GameStatusSchedule


@pytest.mark.asyncio
async def test_handle_status_transition_due_success(event_handlers, sample_game, sample_user):
    """Test successful handling of game.status_transition_due event."""
    game_id = sample_game.id
    target_status = "IN_PROGRESS"

    sample_game.host = sample_user
    sample_game.participants = []
    sample_game.status = GameStatus.SCHEDULED.value

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with (
            patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ),
            patch(
                "services.bot.events.handlers.EventHandlers._refresh_game_message"
            ) as mock_refresh,
        ):
            mock_refresh.return_value = AsyncMock()

            data = {
                "game_id": game_id,
                "target_status": target_status,
                "transition_time": datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC),
            }
            await event_handlers._handle_status_transition_due(data)

            assert sample_game.status == target_status
            mock_db.commit.assert_awaited_once()
            mock_refresh.assert_called_once_with(game_id)
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_handle_status_transition_due_game_not_found(event_handlers):
    """Test status transition when game not found."""
    game_id = str(uuid4())

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=None,
        ):
            data = {
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC),
            }
            await event_handlers._handle_status_transition_due(data)
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_handle_status_transition_due_already_transitioned(
    event_handlers, sample_game, sample_user
):
    """Test status transition when game already at target status (idempotency)."""
    game_id = sample_game.id
    target_status = "COMPLETED"

    sample_game.host = sample_user
    sample_game.participants = []
    sample_game.status = "COMPLETED"  # Already at target status

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with (
            patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ),
            patch(
                "services.bot.events.handlers.EventHandlers._refresh_game_message"
            ) as mock_refresh,
        ):
            data = {
                "game_id": game_id,
                "target_status": target_status,
                "transition_time": datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC),
            }
            await event_handlers._handle_status_transition_due(data)

            # Game should remain at COMPLETED, no commit or refresh
            assert sample_game.status == "COMPLETED"
            mock_db.commit.assert_not_awaited()
            mock_refresh.assert_not_called()
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_handle_status_transition_due_invalid_data(event_handlers):
    """Test status transition with invalid event data."""
    data = {"invalid": "data"}
    await event_handlers._handle_status_transition_due(data)
    assert True  # handler completed without raising


@pytest.mark.asyncio
async def test_handle_status_transition_creates_archived_schedule_when_delay_set(
    event_handlers, sample_game, sample_user
):
    """Test COMPLETED transition schedules ARCHIVED when delay is set."""
    fixed_now = datetime(2025, 11, 20, 19, 0, 0, tzinfo=UTC)
    sample_game.host = sample_user
    sample_game.participants = []
    sample_game.status = GameStatus.IN_PROGRESS.value
    sample_game.archive_delay_seconds = 3600

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db_session,
        patch("services.bot.events.handlers.utc_now", return_value=fixed_now),
    ):
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with (
            patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ),
            patch.object(event_handlers, "_refresh_game_message", new=AsyncMock()),
        ):
            data = {
                "game_id": sample_game.id,
                "target_status": GameStatus.COMPLETED.value,
                "transition_time": fixed_now,
            }
            await event_handlers._handle_status_transition_due(data)

            added_schedules = [
                call.args[0]
                for call in mock_db.add.call_args_list
                if isinstance(call.args[0], GameStatusSchedule)
            ]
            assert len(added_schedules) == 1
            schedule = added_schedules[0]
            assert schedule.game_id == sample_game.id
            assert schedule.target_status == GameStatus.ARCHIVED.value
            assert schedule.transition_time == fixed_now + timedelta(seconds=3600)
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_handle_status_transition_no_archived_schedule_when_delay_none(
    event_handlers, sample_game, sample_user
):
    """Test COMPLETED transition does not schedule ARCHIVED when delay is None."""
    sample_game.host = sample_user
    sample_game.participants = []
    sample_game.status = GameStatus.IN_PROGRESS.value
    sample_game.archive_delay_seconds = None

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with (
            patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ),
            patch.object(event_handlers, "_refresh_game_message", new=AsyncMock()),
        ):
            data = {
                "game_id": sample_game.id,
                "target_status": GameStatus.COMPLETED.value,
                "transition_time": datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC),
            }
            await event_handlers._handle_status_transition_due(data)

            assert not any(
                isinstance(call.args[0], GameStatusSchedule) for call in mock_db.add.call_args_list
            )
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_archive_game_announcement_deletes_original(event_handlers, sample_game):
    """Test archive handler deletes original announcement when no archive channel set."""
    sample_game.archive_channel_id = None
    sample_game.archive_channel = None
    sample_game.message_id = "999888777"

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock()
    mock_channel.get_partial_message = MagicMock(return_value=mock_message)

    with (
        patch.object(
            event_handlers,
            "_get_bot_channel",
            new=AsyncMock(return_value=mock_channel),
        ) as mock_get_channel,
        patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(),
        ) as mock_create,
    ):
        await event_handlers._archive_game_announcement(sample_game)

        mock_get_channel.assert_awaited_once_with(sample_game.channel.channel_id)
        mock_channel.get_partial_message.assert_called_once_with(int(sample_game.message_id))
        mock_message.delete.assert_awaited_once()
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_game_announcement_posts_to_archive_channel(event_handlers, sample_game):
    """Test archive handler reposts announcement when archive channel configured."""
    sample_game.message_id = "999888777"
    sample_game.archive_channel_id = "archive-config"

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_archive_config = MagicMock()
    mock_archive_config.channel_id = "222333444"
    sample_game.archive_channel = mock_archive_config

    mock_active_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock()
    mock_active_channel.get_partial_message = MagicMock(return_value=mock_message)

    mock_archive_channel = AsyncMock(spec=discord.TextChannel)

    with (
        patch.object(
            event_handlers,
            "_get_bot_channel",
            new=AsyncMock(side_effect=[mock_active_channel, mock_archive_channel]),
        ),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("content", "embed", "view")),
        ),
    ):
        await event_handlers._archive_game_announcement(sample_game)

        mock_archive_channel.send.assert_awaited_once_with(content=None, embed="embed")
        mock_active_channel.get_partial_message.assert_called_once_with(int(sample_game.message_id))
        mock_message.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_status_transition_creates_archived_schedule_when_delay_zero(
    event_handlers, sample_game, sample_user
):
    """Test COMPLETED transition schedules ARCHIVED when delay is zero."""
    fixed_now = datetime(2025, 11, 20, 19, 30, 0, tzinfo=UTC)
    sample_game.host = sample_user
    sample_game.participants = []
    sample_game.status = GameStatus.IN_PROGRESS.value
    sample_game.archive_delay_seconds = 0

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db_session,
        patch("services.bot.events.handlers.utc_now", return_value=fixed_now),
    ):
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with (
            patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ),
            patch.object(event_handlers, "_refresh_game_message", new=AsyncMock()),
        ):
            data = {
                "game_id": sample_game.id,
                "target_status": GameStatus.COMPLETED.value,
                "transition_time": fixed_now,
            }
            await event_handlers._handle_status_transition_due(data)

            added_schedules = [
                call.args[0]
                for call in mock_db.add.call_args_list
                if isinstance(call.args[0], GameStatusSchedule)
            ]
            assert len(added_schedules) == 1
            schedule = added_schedules[0]
            assert schedule.transition_time == fixed_now
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_archive_game_announcement_no_message_id_is_noop(event_handlers, sample_game):
    """Test archive handler exits when no message_id is set."""
    sample_game.archive_channel_id = None
    sample_game.archive_channel = None
    sample_game.message_id = None

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch.object(event_handlers, "_get_bot_channel", new=AsyncMock()) as mock_get_channel:
        await event_handlers._archive_game_announcement(sample_game)

        mock_get_channel.assert_not_awaited()
