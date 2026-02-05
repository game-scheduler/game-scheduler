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


"""Unit tests for bot event handlers."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import EventType, NotificationDueEvent
from shared.models import participant as participant_model
from shared.models.base import utc_now
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
    return GameSession(
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

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = MagicMock()
    mock_message.id = 987654321
    mock_channel.send = AsyncMock(return_value=mock_message)

    with (
        patch("services.bot.events.handlers.get_discord_client"),
        patch("services.bot.events.handlers.get_db_session"),
        patch(
            "services.bot.events.handlers.EventHandlers._validate_discord_channel",
            return_value=True,
        ),
        patch(
            "services.bot.events.handlers.EventHandlers._get_bot_channel",
            return_value=mock_channel,
        ),
        patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ),
        patch(
            "services.bot.events.handlers.get_member_display_info",
            return_value=("Test User", "https://example.com/avatar.png"),
        ),
        patch("services.bot.events.handlers.discord.AllowedMentions") as mock_mentions,
    ):
        data = {
            "game_id": sample_game.id,
            "channel_id": sample_game.channel_id,
        }
        await event_handlers._handle_game_created(data)
        mock_mentions.assert_called_once_with(roles=True, everyone=True)


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
async def test_validate_game_created_event_success(event_handlers):
    """Test successful validation of game.created event."""
    result = await event_handlers._validate_game_created_event("game123", "channel456")
    assert result == ("game123", "channel456")


@pytest.mark.asyncio
async def test_validate_game_created_event_missing_game_id(event_handlers):
    """Test validation fails with missing game_id."""
    result = await event_handlers._validate_game_created_event(None, "channel456")
    assert result is None


@pytest.mark.asyncio
async def test_validate_game_created_event_missing_channel_id(event_handlers):
    """Test validation fails with missing channel_id."""
    result = await event_handlers._validate_game_created_event("game123", None)
    assert result is None


@pytest.mark.asyncio
async def test_validate_discord_channel_success(event_handlers):
    """Test successful Discord channel validation."""
    with patch("services.bot.events.handlers.get_discord_client") as mock_client:
        mock_api = AsyncMock()
        mock_api.fetch_channel.return_value = {"id": "123"}
        mock_client.return_value = mock_api

        result = await event_handlers._validate_discord_channel("123")
        assert result is True


@pytest.mark.asyncio
async def test_validate_discord_channel_invalid(event_handlers):
    """Test Discord channel validation with invalid channel."""
    with patch("services.bot.events.handlers.get_discord_client") as mock_client:
        mock_api = AsyncMock()
        mock_api.fetch_channel.return_value = None
        mock_client.return_value = mock_api

        result = await event_handlers._validate_discord_channel("invalid")
        assert result is False


@pytest.mark.asyncio
async def test_get_bot_channel_success(event_handlers, mock_bot):
    """Test getting bot channel successfully."""
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_bot.get_channel.return_value = mock_channel

    result = await event_handlers._get_bot_channel("123")
    assert result == mock_channel


@pytest.mark.asyncio
async def test_get_bot_channel_fetch_required(event_handlers, mock_bot):
    """Test getting bot channel requires fetching."""
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_bot.get_channel.return_value = None
    mock_bot.fetch_channel.return_value = mock_channel

    result = await event_handlers._get_bot_channel("123")
    assert result == mock_channel


@pytest.mark.asyncio
async def test_get_bot_channel_invalid_type(event_handlers, mock_bot):
    """Test getting bot channel with invalid channel type."""
    mock_channel = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    result = await event_handlers._get_bot_channel("123")
    assert result is None


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
            _reminder_minutes=60,
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
            _reminder_minutes=60,
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
            _reminder_minutes=60,
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


class TestHandleJoinNotificationHelpers:
    """Test helper methods extracted from _handle_join_notification."""

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_success(self, event_handlers, sample_game):
        """Test successful fetch of game and participant data."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = MagicMock()

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

            assert game == sample_game
            assert part == participant

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_game_not_found(self, event_handlers):
        """Test fetch when game doesn't exist."""
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = None

            event = NotificationDueEvent(
                game_id=str(uuid4()),
                notification_type="join_notification",
                participant_id=str(uuid4()),
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_not_found(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant doesn't exist."""
        participant_id = str(uuid4())
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_without_user(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant exists but has no user."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = None

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_logger.info.assert_called_once()

    def test_is_participant_confirmed_when_confirmed(self, event_handlers, sample_game):
        """Test participant is confirmed (not waitlisted)."""
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = [participant]
            mock_partition.return_value = mock_partitioned

            is_confirmed = event_handlers._is_participant_confirmed(participant, sample_game)

            assert is_confirmed is True
            mock_partition.assert_called_once_with(
                sample_game.participants, sample_game.max_players
            )

    def test_is_participant_confirmed_when_waitlisted(self, event_handlers, sample_game):
        """Test participant is waitlisted (not confirmed)."""
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.logger") as mock_logger:
                is_confirmed = event_handlers._is_participant_confirmed(participant, sample_game)

                assert is_confirmed is False
                mock_logger.info.assert_called_once()

    def test_format_join_notification_message_with_instructions(self, event_handlers, sample_game):
        """Test message formatting with signup instructions."""
        sample_game.signup_instructions = "Join our Discord at https://discord.gg/test"

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_with_instructions.return_value = "Test message with instructions"

            message = event_handlers._format_join_notification_message(sample_game)

            mock_formats.join_with_instructions.assert_called_once_with(
                sample_game.title,
                sample_game.signup_instructions,
                int(sample_game.scheduled_at.timestamp()),
            )
            assert message == "Test message with instructions"

    def test_format_join_notification_message_without_instructions(
        self, event_handlers, sample_game
    ):
        """Test message formatting without signup instructions."""
        sample_game.signup_instructions = None

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_simple.return_value = "Test simple message"

            message = event_handlers._format_join_notification_message(sample_game)

            mock_formats.join_simple.assert_called_once_with(sample_game.title)
            assert message == "Test simple message"

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_success(self, event_handlers):
        """Test successful DM sending with success logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.info.assert_called_once()
                assert "✓ Sent join notification" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_failure(self, event_handlers):
        """Test failed DM sending with warning logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.warning.assert_called_once()
                assert "Failed to send join notification" in str(mock_logger.warning.call_args)


@pytest.mark.asyncio
async def test_update_message_for_player_removal_success(
    event_handlers, mock_bot, sample_game, sample_user
):
    """Test successful message update after player removal."""
    channel_id = "123456789"
    message_id = "987654321"

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)
    mock_bot.get_channel.return_value = mock_channel

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=sample_game),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            return_value=("content", "embed", "view"),
        ),
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            sample_game.id, message_id, channel_id
        )

        mock_channel.fetch_message.assert_awaited_once_with(int(message_id))
        mock_message.edit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_message_for_player_removal_game_not_found(event_handlers, mock_bot):
    """Test message update when game is not found."""
    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=None),
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            "invalid_game_id", "msg123", "channel123"
        )

        mock_logger.error.assert_called()
        assert any("Game not found" in str(call) for call in mock_logger.error.call_args_list)


@pytest.mark.asyncio
async def test_update_message_for_player_removal_message_not_found(
    event_handlers, mock_bot, sample_game
):
    """Test message update when Discord message is not found."""
    channel_id = "123456789"
    message_id = "987654321"

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(MagicMock(), MagicMock()))
    mock_bot.get_channel.return_value = mock_channel

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=sample_game),
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            sample_game.id, message_id, channel_id
        )

        mock_logger.error.assert_called()
        assert any(
            "Failed to fetch message" in str(call) for call in mock_logger.error.call_args_list
        )


def test_build_removal_dm_message_without_schedule(event_handlers):
    """Test building removal DM message without scheduled time."""
    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", None)

        assert message == "You have been removed from Test Game"
        mock_removal.assert_called_once_with("Test Game")


def test_build_removal_dm_message_with_schedule(event_handlers):
    """Test building removal DM message with scheduled time."""
    scheduled_at = "2026-01-20T15:00:00+00:00"

    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", scheduled_at)

        assert "You have been removed from Test Game" in message
        assert " scheduled for <t:" in message
        assert ":F>" in message


def test_build_removal_dm_message_with_invalid_schedule(event_handlers):
    """Test building removal DM message with invalid scheduled time."""
    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", "invalid-date")

        assert message == "You have been removed from Test Game"


@pytest.mark.asyncio
async def test_notify_removed_player_success(event_handlers):
    """Test successful notification to removed player."""
    with patch.object(event_handlers, "_send_dm", return_value=True) as mock_send_dm:
        await event_handlers._notify_removed_player(
            "123456789", "Test Game", "2026-01-20T15:00:00+00:00"
        )

        mock_send_dm.assert_awaited_once()
        assert mock_send_dm.call_args[0][0] == "123456789"


@pytest.mark.asyncio
async def test_notify_removed_player_no_discord_id(event_handlers):
    """Test notification attempt with no Discord ID."""
    with (
        patch.object(event_handlers, "_send_dm") as mock_send_dm,
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        await event_handlers._notify_removed_player(None, "Test Game", None)

        mock_send_dm.assert_not_awaited()
        mock_logger.warning.assert_called()
        assert any(
            "No discord_id provided" in str(call) for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_notify_removed_player_dm_failure(event_handlers):
    """Test handling of DM send failure."""
    with (
        patch.object(event_handlers, "_send_dm", return_value=False) as mock_send_dm,
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        await event_handlers._notify_removed_player("123456789", "Test Game", None)

        mock_send_dm.assert_awaited_once()
        mock_logger.warning.assert_called()
        assert any(
            "Failed to send removal DM" in str(call) for call in mock_logger.warning.call_args_list
        )


# ==============================================================================
# Helper Method Tests: _handle_game_reminder Extraction (Phase 2 Task 2.2)
# ==============================================================================


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
        )

        assert mock_send.call_count == 2
        mock_send.assert_any_await(
            user_discord_id="user1",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
        )
        mock_send.assert_any_await(
            user_discord_id="user2",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
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
        )


@pytest.mark.asyncio
async def test_send_host_reminder_success(event_handlers):
    """Test sending reminder to game host."""
    host = User(id=str(uuid4()), discord_id="host123")

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
        )

        mock_send.assert_awaited_once_with(
            user_discord_id="host123",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
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
        )


# --- _handle_game_cancelled Helper Tests ---


class TestHandleGameCancelledHelpers:
    """Tests for _handle_game_cancelled extracted helper methods."""

    def test_validate_cancellation_event_data_success(self, event_handlers):
        """Test successful validation of cancellation event data."""
        data = {
            "game_id": str(uuid4()),
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is not None
        game_id, message_id, channel_id = result
        assert game_id == data["game_id"]
        assert message_id == data["message_id"]
        assert channel_id == data["channel_id"]

    def test_validate_cancellation_event_data_missing_game_id(self, event_handlers):
        """Test validation fails when game_id is missing."""
        data = {
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_missing_message_id(self, event_handlers):
        """Test validation fails when message_id is missing."""
        data = {
            "game_id": str(uuid4()),
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_missing_channel_id(self, event_handlers):
        """Test validation fails when channel_id is missing."""
        data = {
            "game_id": str(uuid4()),
            "message_id": "123456789",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None

    def test_validate_cancellation_event_data_empty_values(self, event_handlers):
        """Test validation fails when values are empty strings."""
        data = {
            "game_id": "",
            "message_id": "123456789",
            "channel_id": "987654321",
        }

        result = event_handlers._validate_cancellation_event_data(data)

        assert result is None


@pytest.mark.asyncio
async def test_handle_game_cancelled_success(event_handlers):
    """Test successful handling of game.cancelled event."""
    game_id = str(uuid4())
    message_id = "123456789"
    channel_id = "987654321"

    data = {
        "game_id": game_id,
        "message_id": message_id,
        "channel_id": channel_id,
    }

    mock_game = MagicMock(spec=GameSession)
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_message.edit = AsyncMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=mock_game),
        ),
        patch.object(
            event_handlers,
            "_fetch_channel_and_message",
            new=AsyncMock(return_value=(mock_channel, mock_message)),
        ),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("Content", MagicMock(), MagicMock())),
        ),
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db.return_value.__aexit__ = AsyncMock()

        await event_handlers._handle_game_cancelled(data)

        mock_message.edit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_game_cancelled_invalid_data(event_handlers):
    """Test handling of invalid event data."""
    data = {"message_id": "123456789"}

    with patch.object(
        event_handlers,
        "_get_game_with_participants",
        new=AsyncMock(),
    ) as mock_get_game:
        await event_handlers._handle_game_cancelled(data)

        mock_get_game.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_game_not_found(event_handlers):
    """Test handling when game is not found."""
    game_id = str(uuid4())
    data = {
        "game_id": game_id,
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            event_handlers,
            "_fetch_channel_and_message",
            new=AsyncMock(),
        ) as mock_fetch,
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db.return_value.__aexit__ = AsyncMock()

        await event_handlers._handle_game_cancelled(data)

        mock_fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_channel_invalid(event_handlers):
    """Test handling when channel/message is invalid or inaccessible."""
    game_id = str(uuid4())
    data = {
        "game_id": game_id,
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    mock_game = MagicMock(spec=GameSession)

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=mock_game),
        ),
        patch.object(
            event_handlers,
            "_fetch_channel_and_message",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(),
        ) as mock_create,
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db.return_value.__aexit__ = AsyncMock()

        await event_handlers._handle_game_cancelled(data)

        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_cancelled_handles_exception(event_handlers):
    """Test handling of exceptions during cancellation processing."""
    data = {
        "game_id": str(uuid4()),
        "message_id": "123456789",
        "channel_id": "987654321",
    }

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(side_effect=Exception("Database error")),
        ),
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db.return_value.__aexit__ = AsyncMock()

        await event_handlers._handle_game_cancelled(data)


# --- _refresh_game_message Helper Tests ---


class TestRefreshGameMessageHelpers:
    """Tests for _refresh_game_message extracted helper methods."""

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_success(self, event_handlers, sample_game):
        """Test successful game fetch with message_id."""
        mock_db = MagicMock()
        sample_game.message_id = "123456789"

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=sample_game),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, sample_game.id)

        assert result is sample_game

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_no_game(self, event_handlers):
        """Test game fetch when game not found."""
        mock_db = MagicMock()
        game_id = str(uuid4())

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=None),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, game_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_no_message_id(self, event_handlers, sample_game):
        """Test game fetch when game has no message_id."""
        mock_db = MagicMock()
        sample_game.message_id = None

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=sample_game),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, sample_game.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_success(self, event_handlers, mock_bot):
        """Test successful channel validation."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel.return_value = mock_channel

        with patch("services.bot.events.handlers.get_discord_client") as mock_discord_api:
            mock_api = AsyncMock()
            mock_api.fetch_channel.return_value = {"id": channel_id}
            mock_discord_api.return_value = mock_api

            result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is mock_channel

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_api_fails(self, event_handlers, mock_bot):
        """Test channel validation when API fetch fails."""
        channel_id = "123456789"

        with patch("services.bot.events.handlers.get_discord_client") as mock_discord_api:
            mock_api = AsyncMock()
            mock_api.fetch_channel.return_value = None
            mock_discord_api.return_value = mock_api

            result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_with_fetch(self, event_handlers, mock_bot):
        """Test channel validation with bot fetch when get fails."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel.return_value = None
        mock_bot.fetch_channel.return_value = mock_channel

        with patch("services.bot.events.handlers.get_discord_client") as mock_discord_api:
            mock_api = AsyncMock()
            mock_api.fetch_channel.return_value = {"id": channel_id}
            mock_discord_api.return_value = mock_api

            result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is mock_channel
        mock_bot.fetch_channel.assert_called_once_with(int(channel_id))

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_invalid_type(self, event_handlers, mock_bot):
        """Test channel validation when channel is not TextChannel."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_bot.get_channel.return_value = mock_channel

        with patch("services.bot.events.handlers.get_discord_client") as mock_discord_api:
            mock_api = AsyncMock()
            mock_api.fetch_channel.return_value = {"id": channel_id}
            mock_discord_api.return_value = mock_api

            result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_message_for_refresh_success(self, event_handlers):
        """Test successful message fetch."""
        message_id = "123456789"
        mock_message = MagicMock(spec=discord.Message)
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.fetch_message.return_value = mock_message

        result = await event_handlers._fetch_message_for_refresh(mock_channel, message_id)

        assert result is mock_message
        mock_channel.fetch_message.assert_called_once_with(int(message_id))

    @pytest.mark.asyncio
    async def test_fetch_message_for_refresh_not_found(self, event_handlers):
        """Test message fetch when message not found."""
        message_id = "123456789"
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.fetch_message.side_effect = discord.NotFound(MagicMock(), "Not found")

        result = await event_handlers._fetch_message_for_refresh(mock_channel, message_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_success(self, event_handlers, mock_bot):
        """Test successful channel and message fetch."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = MagicMock(spec=discord.Message)
        mock_channel.fetch_message.return_value = mock_message
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is not None
        assert result[0] is mock_channel
        assert result[1] is mock_message
        mock_bot.get_channel.assert_called_once_with(int(channel_id))
        mock_channel.fetch_message.assert_called_once_with(int(message_id))

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_channel_not_cached(self, event_handlers, mock_bot):
        """Test channel and message fetch when channel not cached."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = MagicMock(spec=discord.Message)
        mock_channel.fetch_message.return_value = mock_message
        mock_bot.get_channel.return_value = None
        mock_bot.fetch_channel.return_value = mock_channel

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is not None
        assert result[0] is mock_channel
        assert result[1] is mock_message
        mock_bot.get_channel.assert_called_once_with(int(channel_id))
        mock_bot.fetch_channel.assert_called_once_with(int(channel_id))
        mock_channel.fetch_message.assert_called_once_with(int(message_id))

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_invalid_channel(self, event_handlers, mock_bot):
        """Test channel and message fetch with invalid channel."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_bot.get_channel.return_value = None
        mock_bot.fetch_channel.side_effect = Exception("Channel not found")

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is None
        mock_bot.get_channel.assert_called_once_with(int(channel_id))
        mock_bot.fetch_channel.assert_called_once_with(int(channel_id))

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_wrong_channel_type(self, event_handlers, mock_bot):
        """Test channel and message fetch when channel is not TextChannel."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_voice_channel = MagicMock(spec=discord.VoiceChannel)
        mock_bot.get_channel.return_value = mock_voice_channel

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is None
        mock_bot.get_channel.assert_called_once_with(int(channel_id))

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_message_not_found(self, event_handlers, mock_bot):
        """Test channel and message fetch when message not found."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.fetch_message.side_effect = discord.NotFound(MagicMock(), "Not found")
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is None
        mock_bot.get_channel.assert_called_once_with(int(channel_id))
        mock_channel.fetch_message.assert_called_once_with(int(message_id))

    @pytest.mark.asyncio
    async def test_fetch_channel_and_message_fetch_error(self, event_handlers, mock_bot):
        """Test channel and message fetch with fetch error."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.fetch_message.side_effect = Exception("API error")
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._fetch_channel_and_message(channel_id, message_id)

        assert result is None
        mock_bot.get_channel.assert_called_once_with(int(channel_id))
        mock_channel.fetch_message.assert_called_once_with(int(message_id))

    @pytest.mark.asyncio
    async def test_update_game_message_content(self, event_handlers, sample_game):
        """Test message content update."""
        mock_message = AsyncMock(spec=discord.Message)
        mock_content = "Test content"
        mock_embed = MagicMock(spec=discord.Embed)
        mock_view = MagicMock()

        with patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=(mock_content, mock_embed, mock_view)),
        ):
            await event_handlers._update_game_message_content(mock_message, sample_game)

        mock_message.edit.assert_called_once_with(
            content=mock_content, embed=mock_embed, view=mock_view
        )

    @pytest.mark.asyncio
    async def test_set_message_refresh_throttle(self, event_handlers):
        """Test setting Redis throttle key."""
        game_id = str(uuid4())
        mock_redis = AsyncMock()

        with patch("services.bot.events.handlers.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            await event_handlers._set_message_refresh_throttle(game_id)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert game_id in call_args[0][0]
        assert call_args[0][1] == "1"


# --- _refresh_game_message Integration Tests ---


@pytest.mark.asyncio
async def test_refresh_game_message_success(event_handlers, sample_game, mock_bot):
    """Test successful game message refresh through all steps."""
    sample_game.message_id = "123456789"

    # Add mock channel config to sample_game
    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_message = AsyncMock(spec=discord.Message)
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=mock_channel
        ) as mock_validate,
        patch.object(
            event_handlers, "_fetch_message_for_refresh", return_value=mock_message
        ) as mock_fetch_msg,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
        patch.object(event_handlers, "_set_message_refresh_throttle") as mock_throttle,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_fetch.assert_called_once_with(mock_db_instance, sample_game.id)
        mock_validate.assert_called_once_with(str(sample_game.channel.channel_id))
        mock_fetch_msg.assert_called_once_with(mock_channel, sample_game.message_id)
        mock_update.assert_called_once_with(mock_message, sample_game)
        mock_throttle.assert_called_once_with(sample_game.id)


@pytest.mark.asyncio
async def test_refresh_game_message_game_not_found(event_handlers, mock_bot):
    """Test refresh when game not found or has no message_id."""
    game_id = str(uuid4())
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(event_handlers, "_fetch_game_for_refresh", return_value=None) as mock_fetch,
        patch.object(event_handlers, "_validate_channel_for_refresh") as mock_validate,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(game_id)

        mock_fetch.assert_called_once_with(mock_db_instance, game_id)
        mock_validate.assert_not_called()
        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_game_message_channel_validation_fails(event_handlers, sample_game, mock_bot):
    """Test refresh when channel validation fails."""
    sample_game.message_id = "123456789"

    # Add mock channel config to sample_game
    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=None
        ) as mock_validate,
        patch.object(event_handlers, "_fetch_message_for_refresh") as mock_fetch_msg,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_fetch.assert_called_once()
        mock_validate.assert_called_once()
        mock_fetch_msg.assert_not_called()
        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_game_message_message_not_found(event_handlers, sample_game, mock_bot):
    """Test refresh when Discord message not found."""
    sample_game.message_id = "123456789"

    # Add mock channel config to sample_game
    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=mock_channel
        ) as mock_validate,
        patch.object(
            event_handlers, "_fetch_message_for_refresh", return_value=None
        ) as mock_fetch_msg,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
        patch.object(event_handlers, "_set_message_refresh_throttle") as mock_throttle,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_fetch.assert_called_once()
        mock_validate.assert_called_once()
        mock_fetch_msg.assert_called_once()
        mock_update.assert_not_called()
        mock_throttle.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_game_message_handles_exception(event_handlers, sample_game, mock_bot):
    """Test refresh handles exceptions gracefully."""
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_game_for_refresh",
            side_effect=Exception("Database error"),
        ) as mock_fetch,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_fetch.assert_called_once()
