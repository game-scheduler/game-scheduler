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


"""
Discord API client dependency for bot service.

Provides singleton instance configured with bot service credentials.
"""

from services.bot import config
from shared.discord.client import DiscordAPIClient

_discord_client_instance: DiscordAPIClient | None = None


def get_discord_client() -> DiscordAPIClient:
    """
    Get Discord API client singleton for bot service.

    Returns:
        Configured DiscordAPIClient instance using bot service credentials
    """
    global _discord_client_instance
    if _discord_client_instance is None:
        bot_config = config.get_config()
        _discord_client_instance = DiscordAPIClient(
            client_id=bot_config.discord_bot_client_id or "",
            client_secret="",  # Bot service doesn't need OAuth2 secret
            bot_token=bot_config.discord_bot_token or "",
        )
    return _discord_client_instance
