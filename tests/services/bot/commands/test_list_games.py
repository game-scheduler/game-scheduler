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


"""Tests for list_games command."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.list_games import (
    _create_games_list_embed,
    list_games_command,
)
from shared.models import GameSession


@pytest.fixture
def mock_interaction():
    """Create mock Discord interaction."""
    interaction = MagicMock(spec=Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_guild():
    """Create mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_channel():
    """Create mock Discord text channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "general"
    return channel


@pytest.fixture
def sample_games():
    """Create sample game sessions."""
    now = datetime.now(UTC)
    games = []
    for i in range(3):
        game = GameSession(
            id=i + 1,
            title=f"Game {i + 1}",
            description=f"Description for game {i + 1}",
            scheduled_at=now + timedelta(days=i + 1),
            status="SCHEDULED",
            host_id=1,
            guild_id=1,
            channel_id=1,
        )
        games.append(game)
    return games


@pytest.mark.asyncio
async def test_list_games_no_guild(mock_interaction):
    """Test list_games_command when not in a guild."""
    mock_interaction.guild = None

    await list_games_command(mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "server" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_games_current_channel_success(
    mock_interaction, mock_guild, mock_channel, sample_games
):
    """Test list_games_command for current channel with results."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel

    with patch("services.bot.commands.list_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_games
        mock_session.execute = AsyncMock(return_value=mock_result)

        await list_games_command(mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "embed" in call_args[1]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_games_current_channel_no_results(mock_interaction, mock_guild, mock_channel):
    """Test list_games_command for current channel with no results."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel

    with patch("services.bot.commands.list_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        await list_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "No scheduled games" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_games_specific_channel(
    mock_interaction, mock_guild, mock_channel, sample_games
):
    """Test list_games_command for specific channel."""
    mock_interaction.guild = mock_guild
    other_channel = MagicMock(spec=discord.TextChannel)
    other_channel.id = 111222333
    other_channel.name = "gaming"

    with patch("services.bot.commands.list_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_games
        mock_session.execute = AsyncMock(return_value=mock_result)

        await list_games_command(mock_interaction, channel=other_channel)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    embed = call_args[1]["embed"]
    assert "gaming" in embed.title


@pytest.mark.asyncio
async def test_list_games_show_all(mock_interaction, mock_guild, sample_games):
    """Test list_games_command with show_all flag."""
    mock_interaction.guild = mock_guild

    with patch("services.bot.commands.list_games.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_games
        mock_session.execute = AsyncMock(return_value=mock_result)

        await list_games_command(mock_interaction, show_all=True)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    embed = call_args[1]["embed"]
    assert "All Scheduled Games" in embed.title


@pytest.mark.asyncio
async def test_list_games_error_handling(mock_interaction, mock_guild, mock_channel):
    """Test list_games_command error handling."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel

    with patch("services.bot.commands.list_games.get_db_session") as mock_db:
        mock_db.return_value.__aenter__.side_effect = Exception("Database error")

        await list_games_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "error" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


def test_create_games_list_embed_single_game(sample_games):
    """Test _create_games_list_embed with one game."""
    embed = _create_games_list_embed("Test Title", sample_games[:1])

    assert embed.title == "Test Title"
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Game 1"
    assert "1 game(s) found" in embed.footer.text


def test_create_games_list_embed_multiple_games(sample_games):
    """Test _create_games_list_embed with multiple games."""
    embed = _create_games_list_embed("Test Title", sample_games)

    assert embed.title == "Test Title"
    assert len(embed.fields) == 3
    assert "3 game(s) found" in embed.footer.text


def test_create_games_list_embed_pagination():
    """Test _create_games_list_embed pagination at 10+ games."""
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

    embed = _create_games_list_embed("Test Title", many_games)

    assert len(embed.fields) == 10
    assert "Showing 10 of 15 games" in embed.footer.text


def test_create_games_list_embed_long_description(sample_games):
    """Test _create_games_list_embed truncates long descriptions."""
    sample_games[0].description = "A" * 200

    embed = _create_games_list_embed("Test Title", sample_games)

    field_value = embed.fields[0].value
    assert "A" * 100 in field_value
    assert len([c for c in field_value if c == "A"]) == 100
