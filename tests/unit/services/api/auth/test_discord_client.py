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


"""
Unit tests for API service Discord client integration.

Note: Core DiscordAPIClient functionality is comprehensively tested in
tests/shared/discord/test_client.py. This file focuses on API-specific
integration, particularly the singleton pattern.
"""

from unittest.mock import MagicMock, patch

from services.api.dependencies.discord import get_discord_client


def test_get_discord_client_singleton():
    """Test Discord client singleton pattern for API service."""
    with patch("services.api.dependencies.discord.config.get_api_config") as mock_config:
        mock_config.return_value = MagicMock(
            discord_client_id="test_id",
            discord_client_secret="test_secret",
            discord_bot_token="test_token",
        )

        client1 = get_discord_client()
        client2 = get_discord_client()

        assert client1 is client2
