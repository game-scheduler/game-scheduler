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


"""Tests for my_games command."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.my_games import (
    _create_games_embed,
    my_games_command,
)
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
    user = User(id=1, discord_id="987654321")
    return user


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
    """Test _create_games_embed with basic games."""
    embed = _create_games_embed("Test Title", sample_games, discord.Color.blue())

    assert embed.title == "Test Title"
    assert len(embed.fields) == 2
    assert embed.fields[0].name == "Game 1"


def test_create_games_embed_pagination():
    """Test _create_games_embed pagination."""
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

    embed = _create_games_embed("Test Title", many_games, discord.Color.blue())

    assert len(embed.fields) == 10
    assert "Showing 10 of 15 games" in embed.footer.text
