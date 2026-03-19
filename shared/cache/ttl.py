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


"""Cache TTL configuration constants."""


class CacheTTL:
    """Time-to-live (TTL) constants for cache entries in seconds."""

    DISPLAY_NAME: int = 300  # 5 minutes
    USER_ROLES: int = 300  # 5 minutes
    SESSION: int = 86400  # 24 hours
    GUILD_CONFIG: int = 600  # 10 minutes
    CHANNEL_CONFIG: int = 600  # 10 minutes
    GAME_DETAILS: int = 60  # 1 minute
    USER_GUILDS: int = 300  # 5 minutes - Discord user guild membership
    DISCORD_CHANNEL: int = 300  # 5 minutes - Discord channel objects
    DISCORD_GUILD: int = 600  # 10 minutes - Discord guild objects
    DISCORD_GUILD_CHANNELS: int = 300  # 5 minutes - Discord guild channels list
    DISCORD_USER: int = 300  # 5 minutes - Discord user objects
    APP_INFO: int = 3600  # 1 hour - Discord application info
