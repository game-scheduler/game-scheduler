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


"""Tests for my_games command."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.my_games import (
    my_games_command,
)
from shared.discord.game_embeds import build_game_list_embed
from shared.models import GameSession, User


@pytest.fixture
def mock_interaction():
    """Create mock Discord interaction."""
    interaction = MagicMock(spec=Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 987654321
    return interaction


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(id=1, discord_id="987654321")


@pytest.fixture
def sample_games():
    """Create sample game sessions."""
    now = datetime.now(UTC)
    games = []
    for i in range(2):
        game = GameSession(
            id=i + 1,
            title=f"Game {i + 1}",
            description=f"Description {i + 1}",
            scheduled_at=now + timedelta(days=i + 1),
            status="SCHEDULED",
            host_id=1,
            guild_id=1,
            channel_id=1,
        )
        games.append(game)
    return games


@pytest.mark.asyncio
async def test_my_games_no_games(mock_interaction, mock_user):
    """Test my_games_command when user has no games."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_games_result = MagicMock()
        mock_games_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_games_result, mock_games_result]
        )

        await my_games_command(mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "not hosting or participating" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_my_games_with_hosted_games(mock_interaction, mock_user, sample_games):
    """Test my_games_command when user is hosting games."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_hosted_result = MagicMock()
        mock_hosted_result.scalars.return_value.all.return_value = sample_games

        mock_participating_result = MagicMock()
        mock_participating_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[
                mock_user_result,
                mock_hosted_result,
                mock_participating_result,
            ]
        )

        await my_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    embeds = call_args[1]["embeds"]
    assert len(embeds) == 1
    assert "Hosting" in embeds[0].title


@pytest.mark.asyncio
async def test_my_games_with_participating_games(mock_interaction, mock_user, sample_games):
    """Test my_games_command when user is participating in games."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_hosted_result = MagicMock()
        mock_hosted_result.scalars.return_value.all.return_value = []

        mock_participating_result = MagicMock()
        mock_participating_result.scalars.return_value.all.return_value = sample_games

        mock_session.execute = AsyncMock(
            side_effect=[
                mock_user_result,
                mock_hosted_result,
                mock_participating_result,
            ]
        )

        await my_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    embeds = call_args[1]["embeds"]
    assert len(embeds) == 1
    assert "Joined" in embeds[0].title


@pytest.mark.asyncio
async def test_my_games_with_both_types(mock_interaction, mock_user, sample_games):
    """Test my_games_command when user is both hosting and participating."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_hosted_result = MagicMock()
        mock_hosted_result.scalars.return_value.all.return_value = sample_games[:1]

        mock_participating_result = MagicMock()
        mock_participating_result.scalars.return_value.all.return_value = sample_games[1:]

        mock_session.execute = AsyncMock(
            side_effect=[
                mock_user_result,
                mock_hosted_result,
                mock_participating_result,
            ]
        )

        await my_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    embeds = call_args[1]["embeds"]
    assert len(embeds) == 2
    assert "Hosting" in embeds[0].title
    assert "Joined" in embeds[1].title


@pytest.mark.asyncio
async def test_my_games_creates_new_user(mock_interaction):
    """Test my_games_command creates user if not exists."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = None

        mock_games_result = MagicMock()
        mock_games_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_games_result, mock_games_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        await my_games_command(mock_interaction)

    assert mock_session.add.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_my_games_error_handling(mock_interaction):
    """Test my_games_command error handling."""
    with patch("services.bot.commands.my_games.get_db_session") as mock_db:
        mock_db.return_value.__aenter__.side_effect = Exception("Database error")

        await my_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "error" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


def test_create_games_embed_basic(sample_games):
    """Test build_game_list_embed with basic games."""
    embed = build_game_list_embed(sample_games, "Test Title", discord.Color.blue())

    assert embed.title == "Test Title"
    assert len(embed.fields) == 2
    assert embed.fields[0].name == "Game 1"


def test_create_games_embed_pagination():
    """Test build_game_list_embed pagination."""
    now = datetime.now(UTC)
    many_games = [
        GameSession(
            id=i,
            title=f"Game {i}",
            description=f"Desc {i}",
            scheduled_at=now + timedelta(days=i),
            status="SCHEDULED",
            host_id=1,
            guild_id=1,
            channel_id=1,
        )
        for i in range(15)
    ]

    embed = build_game_list_embed(many_games, "Test Title", discord.Color.blue())

    assert len(embed.fields) == 10
    assert "Showing 10 of 15 games" in embed.footer.text
