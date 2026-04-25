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


"""Unit tests for cache key patterns."""

from shared.cache.keys import CacheKeys


class TestCacheKeys:
    """Test suite for CacheKeys pattern generation."""

    def test_display_name_key(self):
        """Test display name cache key generation."""
        key = CacheKeys.display_name("guild123", "user456")
        assert key == "api:display:guild123:user456"

    def test_user_roles_key(self):
        """Test user roles cache key generation."""
        key = CacheKeys.user_roles("user456", "guild123")
        assert key == "api:user_roles:user456:guild123"

    def test_discord_member_key(self):
        """Test Discord guild member cache key generation."""
        key = CacheKeys.discord_member("guild123", "user456")
        assert key == "api:member:guild123:user456"

    def test_session_key(self):
        """Test session cache key generation."""
        key = CacheKeys.session("session_abc123")
        assert key == "api:session:session_abc123"

    def test_channel_config_key(self):
        """Test channel config cache key generation."""
        key = CacheKeys.channel_config("channel789")
        assert key == "channel_config:channel789"

    def test_game_details_key(self):
        """Test game details cache key generation."""
        key = CacheKeys.game_details("game_uuid_123")
        assert key == "game:game_uuid_123"

    def test_oauth_state_key(self):
        """Test OAuth state cache key generation."""
        key = CacheKeys.oauth_state("state_random123")
        assert key == "api:oauth:state_random123"

    def test_user_guilds_key(self):
        """Test user guilds cache key generation."""
        key = CacheKeys.user_guilds("user456")
        assert key == "api:user_guilds:user456"

    def test_proj_gen_key(self):
        """Test projection generation pointer key."""
        key = CacheKeys.proj_gen()
        assert key == "proj:gen"

    def test_proj_member_key(self):
        """Test projection member key generation."""
        key = CacheKeys.proj_member("gen123", "guild456", "user789")
        assert key == "proj:member:gen123:guild456:user789"

    def test_proj_user_guilds_key(self):
        """Test projection user guilds key generation."""
        key = CacheKeys.proj_user_guilds("gen123", "user789")
        assert key == "proj:user_guilds:gen123:user789"

    def test_bot_last_seen_key(self):
        """Test bot last seen key."""
        key = CacheKeys.bot_last_seen()
        assert key == "bot:last_seen"

    def test_proj_usernames_key(self):
        """Test projection username sorted set key generation."""
        key = CacheKeys.proj_usernames("gen123", "guild456")
        assert key == "proj:usernames:gen123:guild456"
