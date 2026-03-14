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


"""Unit tests for Discord token utilities."""

import base64

import pytest

from shared.utils.discord_tokens import extract_bot_discord_id


def test_extract_bot_discord_id_valid_token():
    """Test extracting bot ID from valid Discord bot token."""
    bot_id = "1234567890"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    token = f"{bot_id_base64}.timestamp.hmac"

    result = extract_bot_discord_id(token)
    assert result == bot_id


def test_extract_bot_discord_id_with_padding():
    """Test extraction handles base64 padding correctly."""
    bot_id = "123456789"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    # Remove padding to test automatic padding addition
    bot_id_base64 = bot_id_base64.rstrip("=")
    token = f"{bot_id_base64}.timestamp.hmac"

    result = extract_bot_discord_id(token)
    assert result == bot_id


def test_extract_bot_discord_id_invalid_format_too_few_parts():
    """Test error handling for token with too few parts."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("invalid.token")


def test_extract_bot_discord_id_invalid_format_too_many_parts():
    """Test error handling for token with too many parts."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("part1.part2.part3.part4")


def test_extract_bot_discord_id_invalid_base64():
    """Test error handling for invalid base64 encoding."""
    with pytest.raises(ValueError, match="Failed to decode bot ID"):
        extract_bot_discord_id("!!!invalid_base64!!!.timestamp.hmac")


def test_extract_bot_discord_id_empty_token():
    """Test error handling for empty token."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("")


def test_extract_bot_discord_id_snowflake_id():
    """Test extracting real Discord snowflake ID format."""
    # Typical Discord snowflake is 17-19 digits
    bot_id = "1234567890123456789"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    token = f"{bot_id_base64}.MTYxNjM2NjQ2Mg.abc123"

    result = extract_bot_discord_id(token)
    assert result == bot_id
    assert len(result) == 19
