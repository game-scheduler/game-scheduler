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


"""Shared fixtures for tests/unit/services/bot/events/."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.models import GameStatus
from shared.models.game import GameSession
from shared.models.user import User


@pytest.fixture
def mock_bot():
    """Create mock Discord bot."""
    bot = MagicMock(spec=discord.Client)
    bot.get_channel = MagicMock()
    bot.get_user = MagicMock()
    bot.fetch_channel = AsyncMock()
    bot.fetch_user = AsyncMock()
    return bot


@pytest.fixture
async def event_handlers(mock_bot):
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
    game.guild = MagicMock()
    game.guild.guild_id = "disc_guild_123"
    game.channel = MagicMock()
    game.channel.channel_id = "disc_channel_456"
    return game


@pytest.fixture
def sample_user():
    """Create sample user."""
    return User(id=str(uuid4()), discord_id="123456789")
