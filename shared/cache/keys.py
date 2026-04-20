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


"""Cache key pattern definitions for Redis."""


class CacheKeys:
    """Cache key patterns for consistent key generation."""

    @staticmethod
    def display_name(guild_id: str, user_id: str) -> str:
        """Return cache key for Discord user display names in a specific guild."""
        return f"display:{guild_id}:{user_id}"

    @staticmethod
    def user_roles(user_id: str, guild_id: str) -> str:
        """Return cache key for user's role IDs in a guild."""
        return f"user_roles:{user_id}:{guild_id}"

    @staticmethod
    def session(session_id: str) -> str:
        """Return cache key for user session data."""
        return f"session:{session_id}"

    @staticmethod
    def guild_config(guild_id: str) -> str:
        """Return cache key for guild configuration."""
        return f"guild_config:{guild_id}"

    @staticmethod
    def channel_config(channel_id: str) -> str:
        """Return cache key for channel configuration."""
        return f"channel_config:{channel_id}"

    @staticmethod
    def game_details(game_id: str) -> str:
        """Return cache key for game session details."""
        return f"game:{game_id}"

    @staticmethod
    def oauth_state(state: str) -> str:
        """Return cache key for OAuth2 state parameter."""
        return f"oauth_state:{state}"

    @staticmethod
    def user_guilds(user_id: str) -> str:
        """Return cache key for Discord user's guild list."""
        return f"user_guilds:{user_id}"

    @staticmethod
    def discord_channel(channel_id: str) -> str:
        """Return cache key for Discord channel information."""
        return f"discord:channel:{channel_id}"

    @staticmethod
    def discord_guild(guild_id: str) -> str:
        """Return cache key for Discord guild information."""
        return f"discord:guild:{guild_id}"

    @staticmethod
    def discord_guild_roles(guild_id: str) -> str:
        """Return cache key for Discord guild roles."""
        return f"discord:guild_roles:{guild_id}"

    @staticmethod
    def discord_guild_channels(guild_id: str) -> str:
        """Return cache key for Discord guild channels list."""
        return f"discord:guild_channels:{guild_id}"

    @staticmethod
    def discord_member(guild_id: str, user_id: str) -> str:
        """Return cache key for Discord guild member information."""
        return f"discord:member:{guild_id}:{user_id}"

    @staticmethod
    def discord_user(user_id: str) -> str:
        """Return cache key for Discord user information."""
        return f"discord:user:{user_id}"

    @staticmethod
    def app_info() -> str:
        """Return cache key for Discord application info."""
        return "discord:app_info"

    @staticmethod
    def proj_gen() -> str:
        """Return cache key for projection generation pointer."""
        return "proj:gen"

    @staticmethod
    def proj_member(gen: str, guild_id: str, uid: str) -> str:
        """Return cache key for projection member data."""
        return f"proj:member:{gen}:{guild_id}:{uid}"

    @staticmethod
    def proj_user_guilds(gen: str, uid: str) -> str:
        """Return cache key for projection user guilds list."""
        return f"proj:user_guilds:{gen}:{uid}"

    @staticmethod
    def bot_last_seen() -> str:
        """Return cache key for bot last seen timestamp."""
        return "bot:last_seen"

    @staticmethod
    def proj_guild_name(gen: str, guild_id: str) -> str:
        """Return cache key for projection guild name."""
        return f"proj:guild_name:{gen}:{guild_id}"

    @staticmethod
    def proj_usernames(gen: str, guild_id: str) -> str:
        """Return cache key for projection username sorted set."""
        return f"proj:usernames:{gen}:{guild_id}"
