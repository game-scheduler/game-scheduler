# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for bot event handlers."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import EventType
from shared.models.game import GameSession, GameStatus
from shared.models.participant import ParticipantType
from shared.models.user import User


@pytest.fixture
def mock_bot():
    """Create mock Discord bot."""
    bot = MagicMock(spec=discord.Client)
    bot.get_channel = MagicMock()
    bot.fetch_user = AsyncMock()
    return bot


@pytest.fixture
def event_handlers(mock_bot):
    """Create EventHandlers instance."""
    return EventHandlers(mock_bot)


@pytest.fixture
def sample_game():
    """Create sample game session."""
    game = GameSession(
        id=str(uuid4()),
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC),
        guild_id="987654321",
        channel_id="123456789",
        host_id="host789",
        status=GameStatus.SCHEDULED.value,
        max_players=10,
        message_id="999888777",
    )
    return game


@pytest.fixture
def sample_user():
    """Create sample user."""
    return User(id=str(uuid4()), discord_id="123456789")


def test_event_handlers_initialization(event_handlers, mock_bot):
    """Test EventHandlers initializes correctly."""
    assert event_handlers.bot is mock_bot
    assert event_handlers.consumer is None
    assert EventType.GAME_UPDATED in event_handlers._handlers
    assert EventType.NOTIFICATION_DUE in event_handlers._handlers
    assert EventType.GAME_STATUS_TRANSITION_DUE in event_handlers._handlers
    assert EventType.NOTIFICATION_SEND_DM in event_handlers._handlers
    assert EventType.GAME_CREATED in event_handlers._handlers
    assert EventType.PLAYER_JOINED not in event_handlers._handlers
    assert EventType.PLAYER_LEFT not in event_handlers._handlers


@pytest.mark.asyncio
async def test_start_consuming(event_handlers):
    """Test starting event consumption."""
    with patch("services.bot.events.handlers.EventConsumer") as mock_consumer_class:
        mock_consumer = MagicMock()
        mock_consumer.connect = AsyncMock()
        mock_consumer.bind = AsyncMock()
        mock_consumer.register_handler = MagicMock()
        mock_consumer.start_consuming = AsyncMock()
        mock_consumer_class.return_value = mock_consumer

        await event_handlers.start_consuming("test_queue")

        mock_consumer_class.assert_called_once_with(queue_name="test_queue")
        mock_consumer.connect.assert_awaited_once()
        assert mock_consumer.bind.await_count == 2
        mock_consumer.bind.assert_any_await("game.*")
        mock_consumer.bind.assert_any_await("notification.*")
        # GAME_CREATED, GAME_UPDATED, GAME_CANCELLED, GAME_STATUS_CHANGED,
        # GAME_PARTICIPANT_JOINED, GAME_PARTICIPANT_LEFT, GAME_PARTICIPANT_PROMOTED
        assert mock_consumer.register_handler.call_count == 7
        mock_consumer.start_consuming.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_consuming(event_handlers):
    """Test stopping event consumption."""
    mock_consumer = MagicMock()
    mock_consumer.close = AsyncMock()
    event_handlers.consumer = mock_consumer

    await event_handlers.stop_consuming()

    mock_consumer.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_consuming_no_consumer(event_handlers):
    """Test stopping when no consumer exists."""
    await event_handlers.stop_consuming()


@pytest.mark.asyncio
async def test_handle_game_created_success(event_handlers, mock_bot, sample_game, sample_user):
    """Test game.created event handler processes without errors."""
    sample_game.host = sample_user
    sample_game.participants = []

    mock_guild = MagicMock()
    mock_guild.guild_id = sample_game.guild_id
    sample_game.guild = mock_guild

    with patch("services.bot.events.handlers.get_discord_client"):
        with patch("services.bot.events.handlers.get_db_session"):
            with patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ):
                with patch(
                    "services.bot.events.handlers.get_member_display_info",
                    return_value=("Test User", "https://example.com/avatar.png"),
                ):
                    data = {
                        "game_id": sample_game.id,
                        "channel_id": sample_game.channel_id,
                    }
                    # Should complete without raising an exception
                    await event_handlers._handle_game_created(data)


@pytest.mark.asyncio
async def test_handle_game_created_missing_data(event_handlers):
    """Test game.created event with missing data."""
    data = {"game_id": "123"}
    await event_handlers._handle_game_created(data)


@pytest.mark.asyncio
async def test_handle_game_created_invalid_channel(event_handlers, mock_bot):
    """Test game.created event with invalid channel."""
    mock_bot.get_channel.return_value = None

    data = {"game_id": str(uuid4()), "channel_id": "invalid"}
    await event_handlers._handle_game_created(data)


@pytest.mark.asyncio
async def test_handle_game_updated_success(event_handlers, mock_bot, sample_game, sample_user):
    """Test game.updated event handler processes without errors."""
    sample_game.host = sample_user
    sample_game.participants = []

    mock_guild = MagicMock()
    mock_guild.guild_id = sample_game.guild_id
    sample_game.guild = mock_guild

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_discord_client"):
        with patch("services.bot.events.handlers.get_db_session"):
            with patch(
                "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                return_value=sample_game,
            ):
                with patch(
                    "services.bot.events.handlers.get_member_display_info",
                    return_value=("Test User", "https://example.com/avatar.png"),
                ):
                    data = {"game_id": sample_game.id}
                    # Should complete without raising an exception
                    await event_handlers._handle_game_updated(data)
                    await asyncio.sleep(0.01)  # Let event loop process


@pytest.mark.asyncio
async def test_handle_game_updated_message_not_found(
    event_handlers, mock_bot, sample_game, sample_user
):
    """Test game.updated event when message not found."""
    mock_discord_channel = MagicMock(spec=discord.TextChannel)
    mock_discord_channel.fetch_message = AsyncMock(
        side_effect=discord.NotFound(MagicMock(), MagicMock())
    )
    mock_bot.fetch_channel = AsyncMock(return_value=mock_discord_channel)

    sample_game.host = sample_user
    sample_game.participants = []

    # Add mock channel configuration with Discord channel_id
    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ):
            data = {"game_id": sample_game.id}
            await event_handlers._handle_game_updated(data)

            # Wait for debounced refresh to complete
            await asyncio.sleep(2.1)


@pytest.mark.asyncio
async def test_handle_game_updated_debouncing(event_handlers, mock_bot, sample_game, sample_user):
    """Test that rapid game updates are debounced and only refreshed once."""
    sample_game.host = sample_user
    sample_game.participants = []

    mock_guild = MagicMock()
    mock_guild.guild_id = sample_game.guild_id
    sample_game.guild = mock_guild

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    with patch("services.bot.events.handlers.get_discord_client"):
        with patch("services.bot.events.handlers.get_db_session"):
            with patch("services.bot.events.handlers.get_redis_client"):
                with patch(
                    "services.bot.events.handlers.EventHandlers._get_game_with_participants",
                    return_value=sample_game,
                ):
                    with patch(
                        "services.bot.events.handlers.get_member_display_info",
                        return_value=("Test User", "https://example.com/avatar.png"),
                    ):
                        data = {"game_id": sample_game.id}

                        # Send 5 rapid updates
                        for _i in range(5):
                            await event_handlers._handle_game_updated(data)

                        # Should have a pending refresh
                        assert sample_game.id in event_handlers._pending_refreshes


@pytest.mark.asyncio
async def test_handle_send_notification_success(event_handlers, mock_bot):
    """Test successful handling of notification.send_dm event."""
    mock_user = MagicMock()
    mock_user.send = AsyncMock()
    mock_bot.fetch_user.return_value = mock_user

    mock_discord_api = MagicMock()
    mock_discord_api.fetch_user = AsyncMock(
        return_value={"id": "123456789", "username": "test_user"}
    )

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Game starts in 1 hour!",
    }

    with patch("services.bot.events.handlers.get_discord_client", return_value=mock_discord_api):
        await event_handlers._handle_send_notification(data)

    mock_discord_api.fetch_user.assert_awaited_once_with("123456789")
    mock_bot.fetch_user.assert_awaited_once_with(123456789)
    mock_user.send.assert_awaited_once_with("Game starts in 1 hour!")


@pytest.mark.asyncio
async def test_handle_send_notification_dm_disabled(event_handlers, mock_bot):
    """Test notification when user has DMs disabled."""
    mock_user = MagicMock()
    mock_user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), MagicMock()))
    mock_bot.fetch_user.return_value = mock_user

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Test message",
    }

    await event_handlers._handle_send_notification(data)


@pytest.mark.asyncio
async def test_handle_send_notification_invalid_data(event_handlers):
    """Test notification with invalid data."""
    data = {"user_id": "123"}

    await event_handlers._handle_send_notification(data)


@pytest.mark.asyncio
async def test_get_game_with_participants(event_handlers, sample_game, sample_user):
    """Test fetching game with participants."""
    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        result = await event_handlers._get_game_with_participants(mock_db, sample_game.id)

        assert result == sample_game
        mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_game_with_participants_not_found(event_handlers):
    """Test fetching non-existent game."""
    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        result = await event_handlers._get_game_with_participants(mock_db, str(uuid4()))

        assert result is None


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

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ):
            with patch(
                "services.bot.events.handlers.EventHandlers._refresh_game_message"
            ) as mock_refresh:
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

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ):
            with patch(
                "services.bot.events.handlers.EventHandlers._refresh_game_message"
            ) as mock_refresh:
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


@pytest.mark.asyncio
async def test_handle_status_transition_due_invalid_data(event_handlers):
    """Test status transition with invalid event data."""
    data = {"invalid": "data"}
    await event_handlers._handle_status_transition_due(data)


@pytest.mark.asyncio
async def test_send_reminder_dm_participant(event_handlers):
    """Test sending reminder DM to a regular participant."""
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            reminder_minutes=60,
            is_waitlist=False,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "123456789"
        message = call_args[0][1]
        assert "Test Game" in message
        assert "<t:1700000000:R>" in message
        assert "Waitlist" not in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_waitlist(event_handlers):
    """Test sending reminder DM to a waitlist participant."""
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            reminder_minutes=60,
            is_waitlist=True,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        message = call_args[0][1]
        assert "🎫 **[Waitlist]**" in message
        assert "Test Game" in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_host(event_handlers):
    """Test sending reminder DM to game host."""
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="987654321",
            game_title="Test Game",
            game_time_unix=1700000000,
            reminder_minutes=60,
            is_waitlist=False,
            is_host=True,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "987654321"
        message = call_args[0][1]
        assert "🎮 **[Host]**" in message
        assert "Test Game" in message
        assert "Waitlist" not in message


@pytest.mark.asyncio
async def test_handle_game_reminder_due_success(event_handlers, sample_game, sample_user):
    """Test successful game reminder handling with host notification."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participant_user_1 = User(id=str(uuid4()), discord_id="participant456")
    participant_user_2 = User(id=str(uuid4()), discord_id="participant789")

    # Create mock participants
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

                    # Should send 3 reminders: 2 participants + 1 host
                    assert mock_send_reminder.await_count == 3

                    # Check participant reminders
                    participant_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_host", False)
                    ]
                    assert len(participant_calls) == 2

                    # Check host reminder
                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"
                    assert host_calls[0].kwargs["is_host"] is True


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

                    # Should still send host reminder even with no participants
                    assert mock_send_reminder.await_count == 1
                    assert mock_send_reminder.call_args.kwargs["user_discord_id"] == "host123"
                    assert mock_send_reminder.call_args.kwargs["is_host"] is True


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

                    # Should only send participant reminder, no host reminder
                    assert mock_send_reminder.await_count == 1
                    # is_host defaults to False, may not be in kwargs
                    assert mock_send_reminder.call_args.kwargs.get("is_host", False) is False


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
                    # First call is participant (succeeds), second is host (fails)
                    if call_count == 2 and kwargs.get("is_host"):
                        raise Exception("Host notification failed")

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    mock_send_reminder.side_effect = mock_send_reminder_side_effect

                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    # Should not raise exception despite host notification failure
                    await event_handlers._handle_notification_due(data)

                    # Should have tried to send both notifications
                    assert mock_send_reminder.await_count == 2


@pytest.mark.asyncio
async def test_handle_game_reminder_due_with_waitlist(event_handlers, sample_game):
    """Test game reminder with confirmed and waitlist participants plus host."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    # Create 3 participants when max_players is 2
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

                    # Should send 4 reminders: 2 confirmed + 1 waitlist + 1 host
                    assert mock_send_reminder.await_count == 4

                    # Check confirmed participants (is_waitlist=False, is_host=False)
                    confirmed_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_waitlist", False)
                        and not call.kwargs.get("is_host", False)
                    ]
                    assert len(confirmed_calls) == 2

                    # Check waitlist participants (is_waitlist=True)
                    waitlist_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_waitlist", False)
                    ]
                    assert len(waitlist_calls) == 1

                    # Check host (is_host=True)
                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"


@pytest.mark.asyncio
async def test_handle_join_notification_with_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM with signup instructions when present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = "Click the link to create your character: https://example.com"
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert sample_game.signup_instructions in sent_message


@pytest.mark.asyncio
async def test_handle_join_notification_without_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM without signup instructions when not present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = None
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert "signup instructions" not in sent_message.lower()


@pytest.mark.asyncio
async def test_handle_join_notification_missing_participant_id(event_handlers, sample_game):
    """Test join notification handles missing participant_id gracefully."""
    data = {
        "game_id": str(uuid4()),
        "notification_type": "join_notification",
        "participant_id": None,
    }

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            # Should complete without error
            await event_handlers._handle_notification_due(data)


@pytest.mark.asyncio
async def test_handle_join_notification_user_not_found(event_handlers, sample_game):
    """Test join notification handles missing participant gracefully."""
    participant_id = str(uuid4())

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch("services.bot.events.handlers.logger") as mock_logger:
                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant_id,
                }
                await event_handlers._handle_notification_due(data)
                # Should log that participant no longer active
                mock_logger.info.assert_called()
                assert any(
                    "no longer active" in str(call) for call in mock_logger.info.call_args_list
                )
