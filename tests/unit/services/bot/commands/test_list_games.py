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


"""Tests for list_games command."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.list_games import (
    _determine_fetch_strategy,
    _fetch_games_by_strategy,
    list_games_command,
)
from shared.discord.game_embeds import build_game_list_embed
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
    """Test build_game_list_embed with one game."""
    embed = build_game_list_embed(sample_games[:1], "Test Title")

    assert embed.title == "Test Title"
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Game 1"
    assert "1 game(s) found" in embed.footer.text


def test_create_games_list_embed_multiple_games(sample_games):
    """Test build_game_list_embed with multiple games."""
    embed = build_game_list_embed(sample_games, "Test Title")

    assert embed.title == "Test Title"
    assert len(embed.fields) == 3
    assert "3 game(s) found" in embed.footer.text


def test_create_games_list_embed_pagination():
    """Test build_game_list_embed pagination at 10+ games."""
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

    embed = build_game_list_embed(many_games, "Test Title")

    assert len(embed.fields) == 10
    assert "Showing 10 of 15 games" in embed.footer.text


def test_create_games_list_embed_long_description(sample_games):
    """Test build_game_list_embed truncates long descriptions."""
    sample_games[0].description = "A" * 200

    embed = build_game_list_embed(sample_games, "Test Title")

    field_value = embed.fields[0].value
    assert "A" * 100 in field_value
    assert len([c for c in field_value if c == "A"]) == 100


class TestDetermineFetchStrategy:
    """Tests for _determine_fetch_strategy helper."""

    def test_no_guild_returns_none(self):
        """Test returns None when interaction has no guild."""
        interaction = MagicMock(spec=Interaction)
        interaction.guild = None

        result = _determine_fetch_strategy(interaction, None, False)

        assert result is None

    def test_show_all_returns_guild_strategy(self, mock_interaction, mock_guild):
        """Test returns guild strategy when show_all is True."""
        mock_interaction.guild = mock_guild

        result = _determine_fetch_strategy(mock_interaction, None, True)

        assert result is not None
        strategy, title, channel = result
        assert strategy == "guild"
        assert "All Scheduled Games" in title
        assert "Test Guild" in title
        assert channel is None

    def test_specific_channel_returns_channel_strategy(
        self, mock_interaction, mock_guild, mock_channel
    ):
        """Test returns specific_channel strategy when channel provided."""
        mock_interaction.guild = mock_guild

        result = _determine_fetch_strategy(mock_interaction, mock_channel, False)

        assert result is not None
        strategy, title, channel = result
        assert strategy == "specific_channel"
        assert "general" in title
        assert channel is mock_channel

    def test_current_channel_returns_channel_strategy(
        self, mock_interaction, mock_guild, mock_channel
    ):
        """Test returns current_channel strategy for current channel."""
        mock_interaction.guild = mock_guild
        mock_interaction.channel = mock_channel

        result = _determine_fetch_strategy(mock_interaction, None, False)

        assert result is not None
        strategy, title, channel = result
        assert strategy == "current_channel"
        assert "general" in title
        assert channel is mock_channel

    def test_invalid_channel_returns_none(self, mock_interaction, mock_guild):
        """Test returns None when current channel is invalid."""
        mock_interaction.guild = mock_guild
        mock_interaction.channel = None

        result = _determine_fetch_strategy(mock_interaction, None, False)

        assert result is None

    def test_non_text_channel_returns_none(self, mock_interaction, mock_guild):
        """Test returns None when current channel is not a TextChannel."""
        mock_interaction.guild = mock_guild
        mock_interaction.channel = MagicMock(spec=discord.VoiceChannel)

        result = _determine_fetch_strategy(mock_interaction, None, False)

        assert result is None


class TestFetchGamesByStrategy:
    """Tests for _fetch_games_by_strategy helper."""

    @pytest.mark.asyncio
    async def test_guild_strategy_calls_get_all_guild_games(self, sample_games):
        """Test guild strategy fetches all guild games."""
        mock_db = AsyncMock()

        with patch(
            "services.bot.commands.list_games._get_all_guild_games",
            return_value=sample_games,
        ) as mock_get:
            result = await _fetch_games_by_strategy(mock_db, "guild", "123", None)

        mock_get.assert_called_once_with(mock_db, "123")
        assert result == sample_games

    @pytest.mark.asyncio
    async def test_channel_strategy_calls_get_channel_games(self, mock_channel, sample_games):
        """Test channel strategy fetches channel games."""
        mock_db = AsyncMock()

        with patch(
            "services.bot.commands.list_games._get_channel_games",
            return_value=sample_games,
        ) as mock_get:
            result = await _fetch_games_by_strategy(
                mock_db, "specific_channel", "123", mock_channel
            )

        mock_get.assert_called_once_with(mock_db, str(mock_channel.id))
        assert result == sample_games

    @pytest.mark.asyncio
    async def test_no_channel_returns_empty(self):
        """Test returns empty list when channel is None for channel strategy."""
        mock_db = AsyncMock()

        result = await _fetch_games_by_strategy(mock_db, "specific_channel", "123", None)

        assert result == []

    @pytest.mark.asyncio
    async def test_unknown_strategy_returns_empty(self, mock_channel):
        """Test returns empty list for unknown strategy."""
        mock_db = AsyncMock()

        result = await _fetch_games_by_strategy(mock_db, "unknown_strategy", "123", mock_channel)

        assert result == []
