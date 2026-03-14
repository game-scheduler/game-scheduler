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


"""Tests for calendar export service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from icalendar import Calendar
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services.calendar_export import CalendarExportService
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.participant import GameParticipant, ParticipantType
from shared.models.user import User


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(
        id="user-123",
        discord_id="123456789",
    )


@pytest.fixture
def mock_guild():
    """Create mock guild."""
    return GuildConfiguration(
        id="guild-123",
        guild_id="987654321",
    )


@pytest.fixture
def mock_channel(mock_guild):
    """Create mock channel."""
    channel = ChannelConfiguration(
        id="channel-123",
        channel_id="111222333",
        guild_id="guild-123",
    )
    channel.guild = mock_guild
    return channel


@pytest.fixture
def mock_game(mock_user, mock_guild, mock_channel):
    """Create mock game session."""
    scheduled_at = datetime(2025, 12, 15, 18, 0, 0)
    game = GameSession(
        id="game-123",
        title="Test Game Night",
        description="A fun game session",
        signup_instructions="Just show up!",
        scheduled_at=scheduled_at,
        where="Discord Voice Channel",
        max_players=5,
        guild_id="guild-123",
        channel_id="channel-123",
        host_id="user-123",
        reminder_minutes=[60, 15],
        expected_duration_minutes=120,
        status="SCHEDULED",
        created_at=datetime(2025, 12, 1, 12, 0, 0),
        updated_at=datetime(2025, 12, 1, 12, 0, 0),
    )
    game.host = mock_user
    game.guild = mock_guild
    game.channel = mock_channel
    return game


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_export_game_as_host(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test exporting a game as the host."""
    mock_game.host_id = "user-123"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    assert ical_data is not None
    assert isinstance(ical_data, bytes)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    assert len(events) == 1

    event = events[0]
    assert event.get("summary") == "Test Game Night"

    # Verify Discord API functions were called
    mock_fetch_user.assert_called_once_with("123456789")
    mock_fetch_channel.assert_called_once_with("111222333")
    mock_fetch_guild.assert_called_once_with("987654321")


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_export_game_as_participant(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test exporting a game as a participant."""
    mock_game.host_id = "different-user"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    # Create a participant
    participant = GameParticipant(
        id="part-123",
        game_session_id="game-123",
        user_id="123456789",
        position_type=ParticipantType.HOST_ADDED,
        position=0,
    )
    participant.user = mock_user
    mock_game.participants = [participant]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    assert ical_data is not None
    assert isinstance(ical_data, bytes)


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_export_game_as_bot_manager(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test exporting a game as a bot manager."""
    mock_game.host_id = "different-user"
    mock_game.participants = []
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    assert ical_data is not None
    assert isinstance(ical_data, bytes)


@pytest.mark.asyncio
async def test_export_game_not_found(mock_db):
    """Test exporting a non-existent game raises ValueError."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)

    with pytest.raises(ValueError, match="Game with ID game-999 not found"):
        await service.export_game("game-999", "user-123", "123456789", can_export=True)


@pytest.mark.asyncio
async def test_export_game_permission_denied(mock_db, mock_game):
    """Test exporting a game without permission raises PermissionError."""
    mock_game.host_id = "different-user"
    mock_game.participants = []

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)

    with pytest.raises(
        PermissionError,
        match="You must be the host, a participant, or have admin/bot manager permissions",
    ):
        await service.export_game("game-123", "user-123", "123456789", can_export=False)


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_event_has_correct_duration(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test that event duration is calculated correctly."""
    mock_game.host_id = "user-123"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    event = events[0]

    dtstart = event.get("dtstart").dt
    dtend = event.get("dtend").dt
    duration = dtend - dtstart

    assert duration == timedelta(minutes=120)


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_event_has_alarms(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test that reminders are converted to alarms."""
    mock_game.host_id = "user-123"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    event = events[0]

    alarms = [component for component in event.walk() if component.name == "VALARM"]
    assert len(alarms) == 2


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_event_status_mapping(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test that game status is correctly mapped to calendar status."""
    mock_game.host_id = "user-123"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    event = events[0]

    assert event.get("status") == "CONFIRMED"


@pytest.mark.asyncio
@patch("services.api.services.calendar_export.fetch_guild_name_safe")
@patch("services.api.services.calendar_export.fetch_channel_name_safe")
@patch("services.api.services.calendar_export.fetch_user_display_name_safe")
async def test_cancelled_game_status(
    mock_fetch_user, mock_fetch_channel, mock_fetch_guild, mock_db, mock_game, mock_user
):
    """Test that cancelled games are marked correctly."""
    mock_game.status = "CANCELLED"
    mock_game.host_id = "user-123"
    mock_fetch_user.return_value = "@TestUser"
    mock_fetch_channel.return_value = "#game-channel"
    mock_fetch_guild.return_value = "Test Server"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service.export_game("game-123", "user-123", "123456789", can_export=True)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    event = events[0]

    assert event.get("status") == "CANCELLED"


@pytest.mark.asyncio
async def test_export_empty_games_list(mock_db):
    """Test exporting when no games are found."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = CalendarExportService(mock_db)
    ical_data = await service._generate_calendar([])

    assert ical_data is not None
    assert isinstance(ical_data, bytes)

    cal = Calendar.from_ical(ical_data)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    assert len(events) == 0
