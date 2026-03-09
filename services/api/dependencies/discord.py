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
Discord API client dependency for API service.

Provides singleton instance configured with API service credentials.
"""

from services.api import config
from shared.discord.client import DiscordAPIClient

_discord_client_instance: DiscordAPIClient | None = None


def get_discord_client() -> DiscordAPIClient:
    """
    Get Discord API client singleton for API service.

    Returns:
        Configured DiscordAPIClient instance using API service credentials
    """
    global _discord_client_instance  # noqa: PLW0603 - Singleton pattern for Discord client
    if _discord_client_instance is None:
        api_config = config.get_api_config()
        _discord_client_instance = DiscordAPIClient(
            client_id=api_config.discord_client_id,
            client_secret=api_config.discord_client_secret,
            bot_token=api_config.discord_bot_token,
            api_base_url=api_config.discord_api_base_url,
        )
    return _discord_client_instance
