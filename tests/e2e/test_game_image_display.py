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


"""End-to-end tests for game image display in Discord embeds.

Tests the complete image flow:
1. POST /games with thumbnail and banner → Images stored
2. Bot posts announcement to Discord with images
3. Discord successfully fetches and displays images (verified by width/height)

This prevents regressions where images are:
- Not stored correctly in database
- Not referenced correctly in Discord embed URLs
- Not accessible via public endpoints
- Not displayed in Discord (URL fetch failed)

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
async def test_game_with_images_displays_in_discord(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
    valid_png_data,
    valid_jpeg_data,
):
    """
    E2E: Creating game with images shows thumbnail and banner in Discord embed.

    Verifies:
    - Game created with both thumbnail and banner image data
    - Discord message contains embed with thumbnail set
    - Discord message contains embed with image (banner) set
    - Discord successfully fetched images (width/height are set)
    - Image URLs point to public endpoints
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

    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Image Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing image display in Discord",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    files = {
        "thumbnail": ("thumbnail.png", valid_png_data, "image/png"),
        "image": ("banner.jpg", valid_jpeg_data, "image/jpeg"),
    }

    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data=game_data,
        files=files,
    )
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

    # Verify basic embed structure
    discord_helper.verify_game_embed(
        embed=embed,
        expected_title=game_title,
        expected_host_id=discord_user_id,
        expected_max_players=4,
    )

    # Verify images are present and Discord successfully fetched them
    discord_helper.verify_embed_images(
        embed=embed,
        expect_thumbnail=True,
        expect_image=True,
        expected_thumbnail_url_fragment="/api/v1/public/images/",
        expected_image_url_fragment="/api/v1/public/images/",
    )

    print(f"[TEST] Thumbnail URL: {embed.thumbnail.url}")
    print(f"[TEST] Thumbnail dimensions: {embed.thumbnail.width}x{embed.thumbnail.height}")
    print(f"[TEST] Image URL: {embed.image.url}")
    print(f"[TEST] Image dimensions: {embed.image.width}x{embed.image.height}")


@pytest.mark.asyncio
async def test_game_with_only_thumbnail_displays_correctly(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
    valid_png_data,
):
    """
    E2E: Game with only thumbnail (no banner) displays correctly in Discord.

    Verifies thumbnail can be uploaded independently without banner image.
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

    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Thumbnail Only {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing thumbnail-only display",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    files = {
        "thumbnail": ("thumbnail.png", valid_png_data, "image/png"),
    }

    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data=game_data,
        files=files,
    )
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should exist"
    assert len(message.embeds) == 1, "Message should have exactly one embed"

    embed = message.embeds[0]

    discord_helper.verify_embed_images(
        embed=embed,
        expect_thumbnail=True,
        expect_image=False,
        expected_thumbnail_url_fragment="/api/v1/public/images/",
    )

    print(f"[TEST] Thumbnail URL: {embed.thumbnail.url}")
    print(f"[TEST] Thumbnail dimensions: {embed.thumbnail.width}x{embed.thumbnail.height}")
