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


"""Unit tests for EventHandlers game reminder methods."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.models import participant as participant_model
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.participant import ParticipantType
from shared.models.user import User


@pytest.mark.asyncio
async def test_send_reminder_dm_participant(event_handlers):
    """Test sending reminder DM to a regular participant."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=jump_url,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "123456789"
        message = call_args[0][1]
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Waitlist" not in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_participant_no_jump_url(event_handlers):
    """Test sending reminder DM to a participant when game has no jump URL."""
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=None,
        )

        message = mock_send_dm.call_args[0][1]
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert "discord.com" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_waitlist(event_handlers):
    """Test sending reminder DM to a waitlist participant."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=True,
            jump_url=jump_url,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        message = call_args[0][1]
        assert "🎫 **[Waitlist]**" in message
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_host(event_handlers):
    """Test sending reminder DM to game host."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="987654321",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=jump_url,
            is_host=True,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "987654321"
        message = call_args[0][1]
        assert "🎮 **[Host]**" in message
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Waitlist" not in message


@pytest.mark.asyncio
async def test_handle_game_reminder_due_success(event_handlers, sample_game, sample_user):
    """Test successful game reminder handling with host notification."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participant_user_1 = User(id=str(uuid4()), discord_id="participant456")
    participant_user_2 = User(id=str(uuid4()), discord_id="participant789")

    mock_participant_1 = MagicMock()
    mock_participant_1.user_id = participant_user_1.id
    mock_participant_1.user = participant_user_1
    mock_participant_1.position_type = ParticipantType.SELF_ADDED
    mock_participant_1.position = 0
    mock_participant_1.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    mock_participant_2 = MagicMock()
    mock_participant_2.user_id = participant_user_2.id
    mock_participant_2.user = participant_user_2
    mock_participant_2.position_type = ParticipantType.SELF_ADDED
    mock_participant_2.position = 0
    mock_participant_2.joined_at = datetime(2025, 11, 1, 11, 0, 0, tzinfo=UTC)

    sample_game.host = host_user
    sample_game.participants = [mock_participant_1, mock_participant_2]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 3

                    expected_jump_url = (
                        "https://discord.com/channels/disc_guild_123/disc_channel_456/999888777"
                    )

                    participant_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_host", False)
                    ]
                    assert len(participant_calls) == 2
                    for call in participant_calls:
                        assert call.kwargs["jump_url"] == expected_jump_url

                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"
                    assert host_calls[0].kwargs["is_host"] is True
                    assert host_calls[0].kwargs["jump_url"] == expected_jump_url
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_no_participants_but_host(
    event_handlers, sample_game, sample_user
):
    """Test game reminder when no participants but host should still receive notification."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    sample_game.host = host_user
    sample_game.participants = []
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {"game_id": sample_game.id, "notification_type": "reminder"}
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 1
                    assert mock_send_reminder.call_args.kwargs["user_discord_id"] == "host123"
                    assert mock_send_reminder.call_args.kwargs["is_host"] is True
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_no_host(event_handlers, sample_game):
    """Test game reminder when game has no host."""
    participant_user = User(id=str(uuid4()), discord_id="participant456")

    mock_participant = MagicMock()
    mock_participant.user_id = participant_user.id
    mock_participant.user = participant_user
    mock_participant.position_type = ParticipantType.SELF_ADDED
    mock_participant.position = 0
    mock_participant.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    sample_game.host = None
    sample_game.participants = [mock_participant]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 1
                    assert mock_send_reminder.call_args.kwargs.get("is_host", False) is False
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_host_error_doesnt_affect_participants(
    event_handlers, sample_game
):
    """Test that host notification failure doesn't prevent participant notifications."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participant_user = User(id=str(uuid4()), discord_id="participant456")

    mock_participant = MagicMock()
    mock_participant.user_id = participant_user.id
    mock_participant.user = participant_user
    mock_participant.position_type = ParticipantType.SELF_ADDED
    mock_participant.position = 0
    mock_participant.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    sample_game.host = host_user
    sample_game.participants = [mock_participant]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                call_count = 0

                async def mock_send_reminder_side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 2 and kwargs.get("is_host"):
                        error_msg = "Host notification failed"
                        raise Exception(error_msg)

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    mock_send_reminder.side_effect = mock_send_reminder_side_effect

                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 2
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_with_waitlist(event_handlers, sample_game):
    """Test game reminder with confirmed and waitlist participants plus host."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    participants = []
    for i in range(3):
        user = User(id=str(uuid4()), discord_id=f"participant{i}")
        mock_participant = MagicMock()
        mock_participant.user_id = user.id
        mock_participant.user = user
        mock_participant.position_type = ParticipantType.SELF_ADDED
        mock_participant.position = 0
        mock_participant.joined_at = datetime(2025, 11, 1, 10 + i, 0, 0, tzinfo=UTC)
        participants.append(mock_participant)

    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 4

                    confirmed_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_waitlist", False)
                        and not call.kwargs.get("is_host", False)
                    ]
                    assert len(confirmed_calls) == 2

                    waitlist_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_waitlist", False)
                    ]
                    assert len(waitlist_calls) == 1

                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_validate_game_for_reminder_already_started(event_handlers):
    """Test validation rejects game that already started."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() - timedelta(hours=1),
        status="SCHEDULED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is False


@pytest.mark.asyncio
async def test_validate_game_for_reminder_wrong_status(event_handlers):
    """Test validation rejects non-scheduled game."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() + timedelta(hours=1),
        status="COMPLETED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is False


@pytest.mark.asyncio
async def test_validate_game_for_reminder_valid(event_handlers):
    """Test validation accepts valid scheduled game."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() + timedelta(hours=1),
        status="SCHEDULED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is True


def test_partition_and_filter_participants_with_users(event_handlers):
    """Test partitioning with real user participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")
    user2 = User(id=str(uuid4()), discord_id="user2")
    user3 = User(id=str(uuid4()), discord_id="user3")

    participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p3",
            game_session_id="game1",
            user_id=user3.id,
            user=user3,
            position=2,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    game = GameSession(
        id="game1",
        max_players=2,
        participants=participants,
    )

    confirmed, overflow = event_handlers._partition_and_filter_participants(game)

    assert len(confirmed) == 2
    assert len(overflow) == 1
    assert confirmed[0].user == user1
    assert confirmed[1].user == user2
    assert overflow[0].user == user3


def test_partition_and_filter_participants_excludes_placeholders(event_handlers):
    """Test filtering excludes placeholder participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")

    participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=None,
            user=None,
            position=1,
            position_type=ParticipantType.HOST_ADDED,
        ),
    ]

    game = GameSession(
        id="game1",
        max_players=2,
        participants=participants,
    )

    confirmed, overflow = event_handlers._partition_and_filter_participants(game)

    assert len(confirmed) == 1
    assert len(overflow) == 0
    assert confirmed[0].user == user1


@pytest.mark.asyncio
async def test_send_participant_reminders_success(event_handlers):
    """Test sending reminders to participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")
    user2 = User(id=str(uuid4()), discord_id="user2")

    participants_list = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_participant_reminders(
            participants_list,
            "Test Game",
            1234567890,
            is_waitlist=False,
            jump_url=None,
        )

        assert mock_send.call_count == 2
        mock_send.assert_any_await(
            user_discord_id="user1",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
        )
        mock_send.assert_any_await(
            user_discord_id="user2",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
        )


@pytest.mark.asyncio
async def test_send_participant_reminders_handles_errors(event_handlers):
    """Test error handling when sending reminders."""
    user1 = User(id=str(uuid4()), discord_id="user1")

    participants_list = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    with patch.object(
        event_handlers,
        "_send_reminder_dm",
        new=AsyncMock(side_effect=Exception("DM failed")),
    ):
        await event_handlers._send_participant_reminders(
            participants_list,
            "Test Game",
            1234567890,
            is_waitlist=False,
            jump_url=None,
        )
    assert True  # verifies exception is caught without propagating


@pytest.mark.asyncio
async def test_send_host_reminder_success(event_handlers):
    """Test sending reminder to game host."""
    host = User(id=str(uuid4()), discord_id="host123")

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_awaited_once_with(
            user_discord_id="host123",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
            is_host=True,
        )


@pytest.mark.asyncio
async def test_send_host_reminder_no_host(event_handlers):
    """Test handling when no host present."""
    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            None,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_host_reminder_no_discord_id(event_handlers):
    """Test handling when host has no Discord ID."""
    host = User(id=str(uuid4()), discord_id=None)

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_host_reminder_handles_error(event_handlers):
    """Test error handling when sending host reminder."""
    host = User(id=str(uuid4()), discord_id="host123")

    with patch.object(
        event_handlers,
        "_send_reminder_dm",
        new=AsyncMock(side_effect=Exception("DM failed")),
    ):
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )
    assert True  # verifies exception is caught without propagating
