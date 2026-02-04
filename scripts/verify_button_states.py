#!/usr/bin/env python3
"""Verify Discord button states for a specific game.

Usage: python scripts/verify_button_states.py <game_id>
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from shared.discord.client import DiscordClientWrapper
from shared.models.game import GameSession


def _print_game_info(game: GameSession) -> None:
    """Display game information."""
    print("\n📊 Game Information:")
    print(f"   ID: {game.id}")
    print(f"   Title: {game.title}")
    print(f"   Status: {game.status}")
    print(f"   Signup Method: {game.signup_method}")
    print(f"   Discord Message ID: {game.discord_message_id}")
    print(f"   Channel ID: {game.guild_configuration.channel_id}")


def _calculate_expected_button_states(game: GameSession) -> tuple[bool, bool]:
    """Calculate expected button disabled states based on game status and signup method."""
    is_started = game.status in ("IN_PROGRESS", "COMPLETED", "CANCELLED")
    join_should_be_disabled = is_started or game.signup_method == "HOST_SELECTED"
    leave_should_be_disabled = is_started
    return join_should_be_disabled, leave_should_be_disabled


def _print_expected_button_states(
    game: GameSession, join_disabled: bool, leave_disabled: bool
) -> None:
    """Display expected button states with reasoning."""
    print("\n🔘 Expected Button States:")
    is_started = game.status in ("IN_PROGRESS", "COMPLETED", "CANCELLED")

    print(f"   Join Button: {'DISABLED' if join_disabled else 'ENABLED'}")
    print("     Reason: ", end="")
    if is_started:
        print("Game has started")
    elif game.signup_method == "HOST_SELECTED":
        print("Signup method is HOST_SELECTED")
    else:
        print("Players can self-join")

    print(f"   Leave Button: {'DISABLED' if leave_disabled else 'ENABLED'}")
    print("     Reason: ", end="")
    if is_started:
        print("Game has started")
    else:
        print("Players can self-leave")


async def _fetch_and_verify_discord_buttons(
    game: GameSession, expected_join_disabled: bool, expected_leave_disabled: bool
) -> None:
    """Fetch Discord message and verify actual button states match expectations."""
    print("\n🔍 Fetching actual Discord message...")
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        print("❌ DISCORD_BOT_TOKEN not set")
        return

    try:
        client = DiscordClientWrapper(discord_token)
        await client.start_in_background()
        await asyncio.sleep(2)

        channel = await client.fetch_channel(str(game.guild_configuration.channel_id))
        message = await channel.fetch_message(int(game.discord_message_id))

        if not message.components:
            print("❌ Message has no button components")
            await client.close()
            return

        action_row = message.components[0]
        join_button = action_row.children[0]
        leave_button = action_row.children[1]

        print("\n✅ Actual Button States:")
        print(f"   Join Button: {'DISABLED' if join_button.disabled else 'ENABLED'}")
        print(f"   Leave Button: {'DISABLED' if leave_button.disabled else 'ENABLED'}")

        if join_button.disabled != expected_join_disabled:
            print("\n⚠️  Join button mismatch!")
        if leave_button.disabled != expected_leave_disabled:
            print("\n⚠️  Leave button mismatch!")

        await client.close()
    except Exception as e:
        print(f"❌ Error fetching Discord message: {e}")


async def verify_game_buttons(game_id: str) -> None:
    """Verify button states for a game."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://gamebot:gamebot@localhost:5432/gamebot"
    )
    engine = create_async_engine(db_url)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(GameSession).where(GameSession.id == game_id))
        game = result.scalar_one_or_none()

        if not game:
            print(f"❌ Game {game_id} not found")
            return

        _print_game_info(game)

        join_disabled, leave_disabled = _calculate_expected_button_states(game)
        _print_expected_button_states(game, join_disabled, leave_disabled)

        if game.discord_message_id:
            await _fetch_and_verify_discord_buttons(game, join_disabled, leave_disabled)

    await engine.dispose()


if __name__ == "__main__":
    EXPECTED_ARGS = 2
    if len(sys.argv) != EXPECTED_ARGS:
        print("Usage: python scripts/verify_button_states.py <game_id>")
        sys.exit(1)

    asyncio.run(verify_game_buttons(sys.argv[1]))
