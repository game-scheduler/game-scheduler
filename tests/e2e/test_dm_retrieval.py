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
Experimental test to verify DM sending and retrieval between bots.

Tests the basic mechanism:
1. Main bot (DISCORD_TOKEN) sends DM to admin bot
2. Admin bot (DISCORD_ADMIN_BOT_TOKEN) retrieves the DM
"""

import asyncio
import os
from uuid import uuid4

import discord
import pytest


@pytest.fixture(scope="session")
def main_bot_token():
    """Main bot token (sends DMs)."""
    return os.environ["DISCORD_TOKEN"]


@pytest.fixture(scope="session")
def admin_bot_token():
    """Admin bot token (receives DMs)."""
    return os.environ["DISCORD_ADMIN_BOT_TOKEN"]


@pytest.fixture
async def main_bot_client(main_bot_token):
    """Create main bot client for sending DMs."""
    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    await client.login(main_bot_token)
    yield client
    await client.close()


@pytest.fixture
async def admin_bot_client(admin_bot_token):
    """Create admin bot client for receiving DMs."""
    intents = discord.Intents(message_content=True)
    client = discord.Client(intents=intents)
    await client.login(admin_bot_token)
    yield client
    await client.close()


def extract_bot_id_from_token(token: str) -> str:
    """Extract bot Discord ID from token (base64 encoded in first part)."""
    import base64

    parts = token.split(".")
    if len(parts) < 1:
        raise ValueError("Invalid token format")

    # First part is base64-encoded bot ID
    bot_id = base64.b64decode(parts[0] + "==").decode("utf-8")
    return bot_id


@pytest.mark.asyncio
async def test_dm_send_and_retrieve(main_bot_client, admin_bot_client, admin_bot_token):
    """
    Test basic DM sending and retrieval.

    1. Extract admin bot's Discord ID
    2. Main bot sends DM to admin bot
    3. Admin bot retrieves its own DMs
    4. Verify message is found
    """
    # Get admin bot's Discord ID
    admin_bot_id = extract_bot_id_from_token(admin_bot_token)
    print(f"\n[TEST] Admin bot ID: {admin_bot_id}")

    # Generate unique test message
    test_message = f"E2E DM Test {uuid4().hex[:8]}"
    print(f"[TEST] Sending test message: {test_message}")

    # Main bot sends DM to admin bot
    try:
        admin_user = await main_bot_client.fetch_user(int(admin_bot_id))
        print(f"[TEST] Fetched admin user: {admin_user.name}#{admin_user.discriminator}")

        await admin_user.send(test_message)
        print("[TEST] ✓ Message sent successfully")
    except Exception as e:
        pytest.fail(f"Failed to send DM: {e}")

    # Wait a moment for message delivery
    await asyncio.sleep(2)

    # Admin bot retrieves its own DMs
    print("[TEST] Admin bot checking DMs...")
    dm_found = False

    # Get DM channel for admin bot
    dm_channels = [
        channel
        for channel in admin_bot_client.private_channels
        if isinstance(channel, discord.DMChannel)
    ]

    print(f"[TEST] Admin bot has {len(dm_channels)} cached DM channels")

    # If no cached channels, we need to fetch recent messages differently
    # Try to get the user's DM channel by fetching the admin bot's own user
    admin_bot_user = admin_bot_client.user
    print(
        f"[TEST] Admin bot user: {admin_bot_user.name}#{admin_bot_user.discriminator} "
        f"(ID: {admin_bot_user.id})"
    )

    # Try to find DM from main bot
    main_bot_user = await admin_bot_client.fetch_user(
        int(extract_bot_id_from_token(os.environ["DISCORD_TOKEN"]))
    )
    print(
        f"[TEST] Main bot user: {main_bot_user.name}#{main_bot_user.discriminator} "
        f"(ID: {main_bot_user.id})"
    )

    # Create or get DM channel
    dm_channel = await main_bot_user.create_dm()
    print(f"[TEST] DM channel ID: {dm_channel.id}")

    # Fetch recent messages from DM channel
    async for message in dm_channel.history(limit=10):
        print(f"[TEST] Found message: '{message.content}' from {message.author.name}")
        if test_message in message.content:
            dm_found = True
            print("[TEST] ✓ Test message found!")
            break

    assert dm_found, f"Admin bot should receive DM containing '{test_message}'"
    print("[TEST] ✓ DM send and retrieve test passed")
