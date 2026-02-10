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


"""End-to-end tests for Discord channel mentions in game location field.

Tests the complete flow:
1. POST /games with location containing #channel-name
2. Backend resolves channel name to Discord channel ID
3. Bot posts announcement with <#channel_id> format in Where field
4. Verification that Discord renders channel mention as clickable link

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test host user (from DISCORD_USER_ID)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_channel_mention_in_location_displays_as_discord_link(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Channel mention in location field converts to clickable Discord link.

    Verifies:
    - Game created with location containing #channel-name
    - Backend resolves channel name to channel ID
    - Discord embed Where field contains <#channel_id> format
    - Channel ID matches actual guild channel
    - Discord renders mention as clickable link
    """
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Test guild {discord_guild_id} not found"
    test_guild_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {test_guild_id}"
    test_template_id = row[0]

    guild = await discord_helper.client.fetch_guild(int(discord_guild_id))
    channels = await guild.fetch_channels()

    text_channels = [ch for ch in channels if hasattr(ch, "send")]
    assert len(text_channels) > 0, "No text channels found in test guild"

    target_channel = text_channels[0]
    channel_name = target_channel.name

    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Channel Link Test {uuid4().hex[:8]}"
    game_location = f"Meet in #{channel_name} voice lobby"
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing channel mention resolution",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "where": game_location,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    print(f"[TEST] Database - message_id: {message_id}")
    print(f"[TEST] Expected Discord channel_id: {discord_channel_id}")
    assert message_id is not None, "Message ID should be populated after announcement"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    print(f"[TEST] Discord message fetched: {message}")
    assert message is not None, "Discord message should exist"
    assert len(message.embeds) == 1, "Message should have exactly one embed"

    embed = message.embeds[0]
    where_field = next((f for f in embed.fields if f.name.startswith("Where")), None)
    assert where_field is not None, "Where field should exist in embed"

    expected_mention = f"<#{target_channel.id}>"
    assert expected_mention in where_field.value, (
        f"Where field should contain Discord channel mention format. "
        f"Expected: {expected_mention}, Got: {where_field.value}"
    )

    assert f"Meet in {expected_mention} voice lobby" == where_field.value, (
        f"Location text should preserve non-channel content. "
        f"Expected: 'Meet in {expected_mention} voice lobby', Got: {where_field.value}"
    )

    print(f"[TEST] ✓ Channel mention #{channel_name} resolved to {expected_mention}")
    print("[TEST] ✓ Discord will render this as clickable link")
