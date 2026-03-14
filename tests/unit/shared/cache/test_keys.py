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
        assert key == "display:guild123:user456"

    def test_user_roles_key(self):
        """Test user roles cache key generation."""
        key = CacheKeys.user_roles("user456", "guild123")
        assert key == "user_roles:user456:guild123"

    def test_session_key(self):
        """Test session cache key generation."""
        key = CacheKeys.session("session_abc123")
        assert key == "session:session_abc123"

    def test_guild_config_key(self):
        """Test guild config cache key generation."""
        key = CacheKeys.guild_config("guild123")
        assert key == "guild_config:guild123"

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
        assert key == "oauth_state:state_random123"

    def test_message_update_throttle_key(self):
        """Test message update throttle cache key generation."""
        key = CacheKeys.message_update_throttle("game_uuid_123")
        assert key == "message_update:game_uuid_123"
