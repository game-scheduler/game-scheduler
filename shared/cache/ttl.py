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


"""Cache TTL configuration constants."""


class CacheTTL:
    """Time-to-live (TTL) constants for cache entries in seconds."""

    DISPLAY_NAME = 300  # 5 minutes
    USER_ROLES = 300  # 5 minutes
    SESSION = 86400  # 24 hours
    GUILD_CONFIG = 600  # 10 minutes
    CHANNEL_CONFIG = 600  # 10 minutes
    GAME_DETAILS = 60  # 1 minute
    USER_GUILDS = 300  # 5 minutes - Discord user guild membership
    DISCORD_CHANNEL = 300  # 5 minutes - Discord channel objects
    DISCORD_GUILD = 600  # 10 minutes - Discord guild objects
    DISCORD_USER = 300  # 5 minutes - Discord user objects
    MESSAGE_UPDATE_THROTTLE = 1.25  # 1.25 seconds - Rate limit for message updates
