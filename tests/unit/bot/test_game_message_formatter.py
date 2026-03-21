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


"""Unit tests for GameMessageFormatter in services/bot/formatters/game_message.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

# Initialize the full bot import chain before importing the formatter directly,
# to avoid the circular import that arises when formatters/__init__.py is loaded
# in isolation (formatters → views → events → formatters).
import services.bot.events.handlers  # noqa: F401
from services.bot.formatters.game_message import GameMessageFormatter

_NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=UTC)

_BASE_KWARGS = {
    "game_title": "Test Game",
    "description": "A fun game",
    "scheduled_at": _NOW,
    "host_id": "111222333444555666",
    "participant_ids": [],
    "overflow_ids": [],
    "current_count": 0,
    "max_players": 4,
    "status": "SCHEDULED",
}


def _config():
    cfg = MagicMock()
    cfg.frontend_url = "https://example.com"
    cfg.backend_url = "https://api.example.com"
    return cfg


def test_create_game_embed_with_rewards_adds_spoiler_field():
    """Rewards field is added to the embed as a spoiler when rewards non-empty."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(
            **_BASE_KWARGS,
            rewards="Gold coins for all",
        )

    field_names = [f.name for f in embed.fields]
    field_values = [f.value for f in embed.fields]
    assert "🏆 Rewards" in field_names
    rewards_value = field_values[field_names.index("🏆 Rewards")]
    assert rewards_value == "||Gold coins for all||"


def test_create_game_embed_without_rewards_has_no_rewards_field():
    """No rewards field is added when rewards is None."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(**_BASE_KWARGS)

    field_names = [f.name for f in embed.fields]
    assert "🏆 Rewards" not in field_names


def test_create_game_embed_with_empty_string_rewards_has_no_rewards_field():
    """Empty string rewards is treated as falsy — no field added."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(
            **_BASE_KWARGS,
            rewards="",
        )

    field_names = [f.name for f in embed.fields]
    assert "🏆 Rewards" not in field_names
