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


"""pytest configuration for backup/restore tests.

Re-exports all shared fixtures from e2e conftest so backup tests can use
the same database sessions, HTTP clients, and Discord helpers.
"""

# Re-export all fixtures from the e2e conftest — backup tests use the same
# infrastructure (real DB, real Discord, real API).
from tests.e2e.conftest import (  # noqa: F401
    GuildContext,
    authenticated_admin_client,
    bot_discord_id,
    discord_archive_channel_id,
    discord_channel_b_id,
    discord_channel_id,
    discord_guild_b_id,
    discord_guild_id,
    discord_helper,
    discord_ids,
    discord_token,
    discord_user_b_id,
    discord_user_b_token,
    discord_user_id,
    fresh_guild_a,
    fresh_guild_b,
    guild_a_db_id,
    guild_a_template_id,
    guild_b_db_id,
    guild_b_template_id,
    synced_guild,
    test_user_a,
    test_user_b,
    wait_for_game_message_id,
)
