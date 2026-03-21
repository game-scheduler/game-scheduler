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


"""Unit tests for DMFormats and DMPredicates in shared/message_formats.py."""

from dataclasses import dataclass

from shared.message_formats import DMFormats, DMPredicates

# ---------------------------------------------------------------------------
# DMFormats.rewards_reminder
# ---------------------------------------------------------------------------


def test_rewards_reminder_contains_game_title():
    """Returned message includes the game title."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "Epic Quest" in msg


def test_rewards_reminder_contains_edit_link():
    """Returned message includes the edit URL as a markdown link."""
    edit_url = "https://example.com/games/abc-123/edit"
    msg = DMFormats.rewards_reminder("Epic Quest", edit_url)
    assert edit_url in msg


def test_rewards_reminder_mentions_rewards():
    """Returned message references rewards."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "rewards" in msg.lower()


def test_rewards_reminder_mentions_completed():
    """Returned message references game completion."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "completed" in msg.lower()


# ---------------------------------------------------------------------------
# DMPredicates.rewards_reminder
# ---------------------------------------------------------------------------


@dataclass
class _DM:
    content: str | None


def test_rewards_reminder_predicate_matches_valid_dm():
    """Predicate matches a valid rewards reminder DM."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    predicate = DMPredicates.rewards_reminder("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_rewards_reminder_predicate_rejects_wrong_title():
    """Predicate does not match when game title differs."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    predicate = DMPredicates.rewards_reminder("Other Game")
    assert predicate(_DM(msg)) is False


def test_rewards_reminder_predicate_rejects_none_content():
    """Predicate returns False for None message content."""
    predicate = DMPredicates.rewards_reminder("Epic Quest")
    assert predicate(_DM(None)) is False
