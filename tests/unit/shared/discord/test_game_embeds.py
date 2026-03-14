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


"""Tests for shared Discord game embed utilities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import discord
import pytest

from shared.discord.game_embeds import build_game_list_embed
from shared.utils.limits import DEFAULT_PAGE_SIZE


@pytest.fixture
def mock_game():
    """Create a mock game object."""
    game = Mock()
    game.id = "test-game-id-123"
    game.title = "Test Game Session"
    game.description = "A test game description"
    game.scheduled_at = datetime.now(UTC) + timedelta(hours=2)
    return game


@pytest.fixture
def mock_game_no_description():
    """Create a mock game object without description."""
    game = Mock()
    game.id = "test-game-id-456"
    game.title = "Game Without Description"
    game.description = None
    game.scheduled_at = datetime.now(UTC) + timedelta(days=1)
    return game


@pytest.fixture
def mock_game_long_description():
    """Create a mock game object with long description."""
    game = Mock()
    game.id = "test-game-id-789"
    game.title = "Game With Long Description"
    game.description = "A" * 200
    game.scheduled_at = datetime.now(UTC) + timedelta(days=2)
    return game


def test_build_game_list_embed_single_game(mock_game):
    """Test building embed with single game."""
    embed = build_game_list_embed([mock_game], "Test Title")

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Test Title"
    assert embed.color == discord.Color.blue()
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Test Game Session"
    assert "🕒 <t:" in embed.fields[0].value
    assert "A test game description" in embed.fields[0].value
    assert "ID: `test-game-id-123`" in embed.fields[0].value
    assert embed.footer.text == "1 game(s) found"


def test_build_game_list_embed_no_description(mock_game_no_description):
    """Test building embed with game that has no description."""
    embed = build_game_list_embed([mock_game_no_description], "Games Without Desc")

    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Game Without Description"
    value_lines = embed.fields[0].value.split("\n")
    assert any("🕒 <t:" in line for line in value_lines)
    assert any("ID: `test-game-id-456`" in line for line in value_lines)
    assert "None" not in embed.fields[0].value


def test_build_game_list_embed_long_description_truncated(mock_game_long_description):
    """Test that descriptions longer than 100 characters are truncated."""
    embed = build_game_list_embed([mock_game_long_description], "Long Description Test")

    assert len(embed.fields) == 1
    field_value = embed.fields[0].value
    description_part = field_value.split("\n")[1]
    assert len(description_part) == 100


def test_build_game_list_embed_multiple_games(
    mock_game, mock_game_no_description, mock_game_long_description
):
    """Test building embed with multiple games."""
    games = [mock_game, mock_game_no_description, mock_game_long_description]
    embed = build_game_list_embed(games, "Multiple Games")

    assert len(embed.fields) == 3
    assert embed.footer.text == "3 game(s) found"


def test_build_game_list_embed_exceeds_page_size():
    """Test that games exceeding DEFAULT_PAGE_SIZE are truncated and footer reflects this."""
    games = []
    for i in range(DEFAULT_PAGE_SIZE + 5):
        game = Mock()
        game.id = f"game-{i}"
        game.title = f"Game {i}"
        game.description = f"Description {i}"
        game.scheduled_at = datetime.now(UTC) + timedelta(hours=i)
        games.append(game)

    embed = build_game_list_embed(games, "Many Games")

    assert len(embed.fields) == DEFAULT_PAGE_SIZE
    assert embed.footer.text == f"Showing {DEFAULT_PAGE_SIZE} of {DEFAULT_PAGE_SIZE + 5} games"


def test_build_game_list_embed_empty_list():
    """Test building embed with empty game list."""
    embed = build_game_list_embed([], "No Games")

    assert len(embed.fields) == 0
    assert embed.footer.text == "0 game(s) found"


def test_build_game_list_embed_custom_color():
    """Test building embed with custom color."""
    game = Mock()
    game.id = "custom-color-game"
    game.title = "Custom Color Game"
    game.description = "Testing custom color"
    game.scheduled_at = datetime.now(UTC) + timedelta(hours=3)

    embed = build_game_list_embed([game], "Custom Color", color=discord.Color.red())

    assert embed.color == discord.Color.red()


def test_build_game_list_embed_has_timestamp():
    """Test that embed includes current timestamp."""
    game = Mock()
    game.id = "timestamp-test"
    game.title = "Timestamp Test"
    game.description = "Testing timestamp"
    game.scheduled_at = datetime.now(UTC) + timedelta(hours=1)

    before = datetime.now(UTC)
    embed = build_game_list_embed([game], "Timestamp Test")
    after = datetime.now(UTC)

    assert embed.timestamp is not None
    assert before <= embed.timestamp <= after


def test_build_game_list_embed_field_not_inline():
    """Test that all fields are set to not inline."""
    game = Mock()
    game.id = "inline-test"
    game.title = "Inline Test"
    game.description = "Testing inline setting"
    game.scheduled_at = datetime.now(UTC) + timedelta(hours=1)

    embed = build_game_list_embed([game], "Inline Test")

    for field in embed.fields:
        assert field.inline is False


def test_build_game_list_embed_unix_timestamp_format(mock_game):
    """Test that unix timestamps are properly formatted in field values."""
    embed = build_game_list_embed([mock_game], "Timestamp Format Test")

    expected_timestamp = int(mock_game.scheduled_at.timestamp())
    assert f"<t:{expected_timestamp}:F>" in embed.fields[0].value
    assert f"<t:{expected_timestamp}:R>" in embed.fields[0].value


def test_build_game_list_embed_exactly_page_size():
    """Test embed when games list is exactly DEFAULT_PAGE_SIZE."""
    games = []
    for i in range(DEFAULT_PAGE_SIZE):
        game = Mock()
        game.id = f"game-{i}"
        game.title = f"Game {i}"
        game.description = f"Description {i}"
        game.scheduled_at = datetime.now(UTC) + timedelta(hours=i)
        games.append(game)

    embed = build_game_list_embed(games, "Exact Page Size")

    assert len(embed.fields) == DEFAULT_PAGE_SIZE
    assert embed.footer.text == f"{DEFAULT_PAGE_SIZE} game(s) found"
