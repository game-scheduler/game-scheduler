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

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import EventType
from shared.models.game import GameSession, GameStatus
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
    assert EventType.NOTIFICATION_SEND_DM in event_handlers._handlers
    assert EventType.GAME_CREATED in event_handlers._handlers


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
        assert mock_consumer.register_handler.call_count == 3
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
    """Test successful handling of game.created event."""
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_message = MagicMock()
    mock_message.id = 123456789
    mock_channel.send = AsyncMock(return_value=mock_message)
    mock_bot.get_channel.return_value = mock_channel

    sample_game.host = sample_user
    sample_game.participants = []

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ):
            with patch("services.bot.events.handlers.format_game_announcement") as mock_format:
                mock_embed = MagicMock()
                mock_view = MagicMock()
                mock_format.return_value = (mock_embed, mock_view)

                data = {"game_id": sample_game.id, "channel_id": sample_game.channel_id}
                await event_handlers._handle_game_created(data)

                mock_channel.send.assert_awaited_once_with(embed=mock_embed, view=mock_view)
                assert sample_game.message_id == str(mock_message.id)
                mock_db.commit.assert_awaited_once()


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
    """Test successful handling of game.updated event."""
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)
    mock_bot.get_channel.return_value = mock_channel

    sample_game.host = sample_user
    sample_game.participants = []

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch(
            "services.bot.events.handlers.EventHandlers._get_game_with_participants",
            return_value=sample_game,
        ):
            with patch("services.bot.events.handlers.format_game_announcement") as mock_format:
                mock_embed = MagicMock()
                mock_view = MagicMock()
                mock_format.return_value = (mock_embed, mock_view)

                data = {"game_id": sample_game.id}
                await event_handlers._handle_game_updated(data)

                mock_channel.fetch_message.assert_awaited_once_with(int(sample_game.message_id))
                mock_message.edit.assert_awaited_once_with(embed=mock_embed, view=mock_view)


@pytest.mark.asyncio
async def test_handle_game_updated_message_not_found(
    event_handlers, mock_bot, sample_game, sample_user
):
    """Test game.updated event when message not found."""
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(MagicMock(), MagicMock()))
    mock_bot.get_channel.return_value = mock_channel

    sample_game.host = sample_user
    sample_game.participants = []

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


@pytest.mark.asyncio
async def test_handle_send_notification_success(event_handlers, mock_bot):
    """Test successful handling of notification.send_dm event."""
    mock_user = MagicMock()
    mock_user.send = AsyncMock()
    mock_bot.fetch_user.return_value = mock_user

    data = {
        "user_id": "123456789",
        "game_id": str(uuid4()),
        "game_title": "Test Game",
        "game_time_unix": 1732125600,
        "notification_type": "reminder",
        "message": "Game starts in 1 hour!",
    }

    await event_handlers._handle_send_notification(data)

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
