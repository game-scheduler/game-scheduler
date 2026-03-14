# Copyright 2025-2026 Bret McKee
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


"""Tests for notification schedule management service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.services.notification_schedule import NotificationScheduleService
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule


@pytest.mark.asyncio
async def test_populate_schedule_creates_future_notifications():
    """Test that populate_schedule creates notification records for future reminders."""
    # Mock database session
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    service = NotificationScheduleService(mock_db)

    # Game scheduled 2 hours in the future
    scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
    game = MagicMock(spec=GameSession)
    game.id = "test-game-id"
    game.scheduled_at = scheduled_at

    reminder_minutes = [60, 15]  # 1 hour and 15 minutes before
    await service.populate_schedule(game, reminder_minutes)

    # Verify two notification records were added to session
    assert mock_db.add.call_count == 2

    # Verify the added objects are NotificationSchedule instances
    calls = mock_db.add.call_args_list
    added_schedules = [call[0][0] for call in calls]

    assert all(isinstance(s, NotificationSchedule) for s in added_schedules)
    assert added_schedules[0].game_id == "test-game-id"
    assert added_schedules[0].reminder_minutes == 60
    assert added_schedules[0].game_scheduled_at == scheduled_at
    assert added_schedules[0].sent is False

    assert added_schedules[1].game_id == "test-game-id"
    assert added_schedules[1].reminder_minutes == 15
    assert added_schedules[1].game_scheduled_at == scheduled_at
    assert added_schedules[1].sent is False


@pytest.mark.asyncio
async def test_populate_schedule_skips_past_notifications():
    """Test that populate_schedule skips notifications in the past."""
    # Mock database session
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    service = NotificationScheduleService(mock_db)

    # Game scheduled 30 minutes in the future
    scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30)
    game = MagicMock(spec=GameSession)
    game.id = "test-game-id"
    game.scheduled_at = scheduled_at

    # 60 min is in the past, 15 min is future
    reminder_minutes = [60, 15]
    await service.populate_schedule(game, reminder_minutes)

    # Verify only one notification record was added (the 15 min one)
    assert mock_db.add.call_count == 1

    added_schedule = mock_db.add.call_args[0][0]
    assert added_schedule.reminder_minutes == 15


@pytest.mark.asyncio
async def test_update_schedule_deletes_and_creates():
    """Test that update_schedule deletes old and creates new notifications."""
    # Mock database session
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    service = NotificationScheduleService(mock_db)

    # Game scheduled 3 hours in the future
    scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=3)
    game = MagicMock(spec=GameSession)
    game.id = "test-game-id"
    game.scheduled_at = scheduled_at

    reminder_minutes = [120, 30]
    await service.update_schedule(game, reminder_minutes)

    # Verify delete was called
    assert mock_db.execute.call_count == 1

    # Verify new schedules were added
    assert mock_db.add.call_count == 2


@pytest.mark.asyncio
async def test_populate_schedule_with_empty_reminders():
    """Test that populate_schedule handles empty reminder list gracefully."""
    # Mock database session
    mock_db = AsyncMock()
    service = NotificationScheduleService(mock_db)

    scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
    game = MagicMock(spec=GameSession)
    game.id = "test-game-id"
    game.scheduled_at = scheduled_at

    await service.populate_schedule(game, [])

    # Verify no notifications were added
    assert mock_db.add.call_count == 0


@pytest.mark.asyncio
async def test_clear_schedule_deletes_all_notifications():
    """Test that clear_schedule deletes all notification records for a game."""
    # Mock database session
    mock_db = AsyncMock()
    service = NotificationScheduleService(mock_db)

    game_id = "test-game-id"
    await service.clear_schedule(game_id)

    # Verify delete was called
    assert mock_db.execute.call_count == 1
