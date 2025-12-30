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


"""Discord test helper for E2E tests."""

import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

import discord

from shared.message_formats import DMPredicates

T = TypeVar("T")


class DMType(StrEnum):
    """Types of game-related DMs."""

    REMINDER = "reminder"
    JOIN = "join"
    REMOVAL = "removal"
    PROMOTION = "promotion"


async def wait_for_condition(
    check_func: Callable[[], Awaitable[tuple[bool, T | None]]],
    timeout: int = 30,
    interval: float = 1.0,
    description: str = "condition",
) -> T:
    """
    Poll for condition with timeout.

    Generic polling utility that repeatedly calls check_func until it returns
    (True, result) or timeout is reached.

    Args:
        check_func: Async function returning (condition_met: bool, result: T | None)
                   Should return (True, value) when condition met, (False, None) otherwise
        timeout: Maximum seconds to wait
        interval: Seconds between checks
        description: Human-readable description for error messages

    Returns:
        Result value returned by check_func when condition met

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        async def check_message_exists():
            try:
                msg = await channel.fetch_message(msg_id)
                return (True, msg)
            except discord.NotFound:
                return (False, None)

        message = await wait_for_condition(
            check_message_exists,
            timeout=10,
            description="Discord message to appear"
        )
    """
    start_time = asyncio.get_event_loop().time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = asyncio.get_event_loop().time() - start_time

        condition_met, result = await check_func()

        if condition_met:
            print(f"[WAIT] ✓ {description} met after {elapsed:.1f}s (attempt {attempt})")
            return result

        if elapsed >= timeout:
            raise AssertionError(
                f"{description} not met within {timeout}s timeout ({attempt} attempts)"
            )

        if attempt == 1:
            print(f"[WAIT] Waiting for {description} (timeout: {timeout}s, interval: {interval}s)")
        elif attempt % 5 == 0:
            print(
                f"[WAIT] Still waiting for {description}... "
                f"({elapsed:.0f}s elapsed, attempt {attempt})"
            )

        await asyncio.sleep(interval)


class DiscordTestHelper:
    """
    Helper class for Discord API interactions in E2E tests.

    Provides methods to fetch and verify Discord messages, embeds, and DMs
    during end-to-end testing of the game scheduling bot.
    """

    def __init__(self, bot_token: str):
        """
        Initialize Discord test helper.

        Args:
            bot_token: Discord bot authentication token
        """
        # MESSAGE_CONTENT intent is required to fetch embeds, attachments, and content
        # via REST API, even though it's not a gateway event
        intents = discord.Intents(message_content=True)
        self.client = discord.Client(intents=intents)
        self.bot_token = bot_token
        self._connected = False

    async def __aenter__(self):
        """Context manager entry - connect to Discord."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from Discord."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to Discord using bot token."""
        if not self._connected:
            await self.client.login(self.bot_token)
            self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        if self._connected:
            await self.client.close()
            self._connected = False

    async def get_message(self, channel_id: str, message_id: str) -> discord.Message:
        """
        Fetch specific message from channel.

        Args:
            channel_id: Discord channel snowflake ID
            message_id: Discord message snowflake ID

        Returns:
            Discord Message object
        """
        channel = await self.client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel | discord.Thread | discord.DMChannel):
            raise ValueError(f"Channel {channel_id} does not support messages")

        message = await channel.fetch_message(int(message_id))
        return message

    async def get_recent_messages(self, channel_id: str, limit: int = 10) -> list[discord.Message]:
        """
        Fetch recent messages from channel.

        Args:
            channel_id: Discord channel snowflake ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of recent Discord messages
        """
        channel = await self.client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel | discord.Thread | discord.DMChannel):
            raise ValueError(f"Channel {channel_id} does not support message history")
        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(msg)
        return messages

    async def find_message_by_embed_title(
        self, channel_id: str, title: str, limit: int = 10
    ) -> discord.Message | None:
        """
        Find message with specific embed title.

        Args:
            channel_id: Discord channel snowflake ID
            title: Embed title to search for
            limit: Maximum number of messages to search

        Returns:
            Message with matching embed title, or None if not found
        """
        messages = await self.get_recent_messages(channel_id, limit)
        for msg in messages:
            if msg.embeds and msg.embeds[0].title == title:
                return msg
        return None

    async def get_user_recent_dms(self, user_id: str, limit: int = 5) -> list[discord.Message]:
        """
        Fetch recent DM messages sent to user by the bot.

        Args:
            user_id: Discord user snowflake ID
            limit: Maximum number of DMs to retrieve

        Returns:
            List of recent DM messages sent by bot
        """
        user = await self.client.fetch_user(int(user_id))
        dm_channel = await user.create_dm()
        messages = []
        async for msg in dm_channel.history(limit=limit):
            if msg.author.id == self.client.user.id:
                messages.append(msg)
        return messages

    async def find_game_reminder_dm(self, user_id: str, game_title: str) -> discord.Message | None:
        """
        Find DM reminder for specific game.

        Args:
            user_id: Discord user snowflake ID
            game_title: Title of the game to find reminder for

        Returns:
            DM message containing game reminder, or None if not found
        """
        dms = await self.get_user_recent_dms(user_id, limit=10)
        for dm in dms:
            # Check content for game title (reminders are plain text, not embeds)
            if dm.content and game_title in dm.content and "starts <t:" in dm.content:
                return dm
        return None

    def extract_embed_field_value(self, embed: discord.Embed, field_name: str) -> str | None:
        """
        Extract value from embed field by name.

        Args:
            embed: Discord embed object
            field_name: Name of the field to extract

        Returns:
            Field value string, or None if field not found
        """
        for field in embed.fields:
            if field.name == field_name:
                return field.value
        return None

    def verify_game_embed(
        self,
        embed: discord.Embed,
        expected_title: str,
        expected_host_id: str,
        expected_max_players: int,
        expected_game_time: str | None = None,
        expected_run_time: str | None = None,
        expected_location: str | None = None,
        expected_voice_channel: str | None = None,
        expected_game_id: int | None = None,
        verify_numbered_participants: bool = True,
    ) -> None:
        """
        Verify game announcement embed structure and content.

        Args:
            embed: Discord embed object to verify
            expected_title: Expected game title
            expected_host_id: Expected Discord host user ID
            expected_max_players: Expected maximum player count
            expected_game_time: Optional timestamp to verify in Game Time field
            expected_run_time: Optional duration text to verify in Run Time field
            expected_location: Optional location text to verify in Where field
            expected_voice_channel: Optional voice channel name to verify
            expected_game_id: Optional game ID to verify Links field contains calendar URL
            verify_numbered_participants: Whether to verify participant list numbering
                (default True)

        Raises:
            AssertionError: If embed does not match expected values
        """
        assert embed.title == expected_title, f"Title mismatch: {embed.title}"

        assert embed.author and embed.author.name, "Embed should have author with name"
        assert embed.author.name.startswith("@"), (
            f"Author should start with '@': {embed.author.name}"
        )

        # Build field map for easier verification
        field_map = {}
        for field in embed.fields:
            if field.name:
                field_map[field.name] = field.value

        # Verify Game Time field exists and has Discord timestamp format
        game_time_field = None
        for name in field_map.keys():
            if "Game Time" in name:
                game_time_field = field_map[name]
                break
        assert game_time_field is not None, "Game Time field missing"
        assert "<t:" in game_time_field, (
            f"Game Time should contain Discord timestamp: {game_time_field}"
        )
        if expected_game_time:
            assert expected_game_time in game_time_field, (
                f"Game Time timestamp mismatch: {game_time_field}"
            )

        # Verify Run Time field if duration expected
        if expected_run_time:
            run_time_field = field_map.get("Run Time")
            assert run_time_field is not None, "Run Time field missing when duration expected"
            assert expected_run_time in run_time_field, f"Run Time mismatch: {run_time_field}"

        # Verify Where field if location expected
        if expected_location:
            where_field = field_map.get("Where")
            assert where_field is not None, "Where field missing when location expected"
            assert expected_location in where_field, f"Where field mismatch: {where_field}"

        # Verify Voice Channel field if expected
        if expected_voice_channel:
            voice_channel_field = field_map.get("Voice Channel")
            assert voice_channel_field is not None, "Voice Channel field missing when expected"
            assert expected_voice_channel in voice_channel_field, (
                f"Voice Channel mismatch: {voice_channel_field}"
            )

        # Find and verify Participants field - format "Participants (X/Y)"
        participants_field_name = None
        participants_field_value = None
        for name, value in field_map.items():
            if "Participants" in name:
                participants_field_name = name
                participants_field_value = value
                break

        assert participants_field_name is not None, "Participants field missing"
        assert f"/{expected_max_players}" in participants_field_name, (
            f"Max players incorrect in field name: {participants_field_name}"
        )

        # Verify numbered participant list format if requested
        if (
            verify_numbered_participants
            and participants_field_value
            and participants_field_value not in ("None yet", "No participants yet")
        ):
            lines = participants_field_value.split("\n")
            for i, line in enumerate(lines, start=1):
                if line.strip():
                    assert line.startswith(f"{i}."), (
                        f"Participant line {i} should start with '{i}.': {line}"
                    )

        # Verify Waitlisted field exists if there are any waitlisted players
        waitlisted_field_name = None
        waitlisted_field_value = None
        for name, value in field_map.items():
            if "Waitlisted" in name:
                waitlisted_field_name = name
                waitlisted_field_value = value
                break

        # If there are participants and max_players is set, waitlist field should exist
        if waitlisted_field_name and waitlisted_field_value and waitlisted_field_value != "None":
            # Verify waitlist numbering continues from participants
            if verify_numbered_participants:
                participant_count = len(
                    [line for line in participants_field_value.split("\n") if line.strip()]
                )
                waitlist_lines = waitlisted_field_value.split("\n")
                for i, line in enumerate(waitlist_lines, start=participant_count + 1):
                    if line.strip():
                        assert line.startswith(f"{i}."), (
                            f"Waitlist line should start with '{i}.': {line}"
                        )

        # Verify Links field with calendar download if game_id provided
        if expected_game_id:
            links_field = field_map.get("Links")
            assert links_field is not None, "Links field missing when game_id provided"
            assert f"/games/{expected_game_id}/calendar" in links_field, (
                f"Links field should contain calendar URL: {links_field}"
            )

        # Verify footer contains status
        assert embed.footer and embed.footer.text, "Embed should have footer with status"

    async def wait_for_message(
        self,
        channel_id: str,
        message_id: str,
        timeout: int = 10,
        interval: float = 0.5,
    ) -> discord.Message:
        """
        Wait for Discord message to exist.

        Polls channel.fetch_message() until message found or timeout.
        Useful after API operations that create/update Discord messages.

        Args:
            channel_id: Discord channel snowflake
            message_id: Discord message snowflake
            timeout: Maximum seconds to wait
            interval: Seconds between fetch attempts

        Returns:
            Discord Message object

        Raises:
            AssertionError: If message not found within timeout
        """

        async def check_message():
            try:
                msg = await self.get_message(channel_id, message_id)
                return (True, msg)
            except (discord.NotFound, discord.HTTPException):
                return (False, None)

        return await wait_for_condition(
            check_message,
            timeout=timeout,
            interval=interval,
            description=f"message {message_id} in channel {channel_id}",
        )

    async def wait_for_message_update(
        self,
        channel_id: str,
        message_id: str,
        check_func: Callable[[discord.Message], bool],
        timeout: int = 10,
        interval: float = 1.0,
        description: str = "message update",
    ) -> discord.Message:
        """
        Wait for Discord message to match condition.

        Polls message until check_func returns True. Useful for verifying
        embed updates, content changes, etc.

        Args:
            channel_id: Discord channel snowflake
            message_id: Discord message snowflake
            check_func: Function that returns True when message matches expected state
            timeout: Maximum seconds to wait
            interval: Seconds between checks
            description: Human-readable description for logging

        Returns:
            Updated Discord Message object

        Example:
            # Wait for embed title to change
            updated_msg = await helper.wait_for_message_update(
                channel_id,
                message_id,
                lambda msg: msg.embeds[0].title == "New Title",
                description="embed title update"
            )
        """

        async def check_update():
            try:
                msg = await self.get_message(channel_id, message_id)
                if check_func(msg):
                    return (True, msg)
                return (False, None)
            except (discord.NotFound, discord.HTTPException):
                return (False, None)

        return await wait_for_condition(
            check_update,
            timeout=timeout,
            interval=interval,
            description=description,
        )

    async def wait_for_dm_matching(
        self,
        user_id: str,
        predicate: Callable[[discord.Message], bool],
        timeout: int = 150,
        interval: float = 5.0,
        description: str = "DM",
    ) -> discord.Message:
        """
        Wait for DM matching predicate.

        Polls user's DM channel until message matching predicate found.
        Uses longer default timeout since DMs may be delayed by notification
        daemon polling intervals.

        Args:
            user_id: Discord user snowflake
            predicate: Function returning True for matching DM
            timeout: Maximum seconds to wait (default 150s for daemon delays)
            interval: Seconds between DM channel checks
            description: Human-readable description for logging

        Returns:
            Matching Discord Message object

        Example:
            # Wait for game reminder DM
            reminder_dm = await helper.wait_for_dm_matching(
                user_id,
                lambda dm: "Test Game" in dm.content and "starts <t:" in dm.content,
                description="game reminder DM"
            )
        """

        async def check_dms():
            dms = await self.get_user_recent_dms(user_id, limit=15)
            for dm in dms:
                if predicate(dm):
                    return (True, dm)
            return (False, None)

        return await wait_for_condition(
            check_dms,
            timeout=timeout,
            interval=interval,
            description=description,
        )

    async def wait_for_recent_dm(
        self,
        user_id: str,
        game_title: str,
        dm_type: DMType = DMType.REMINDER,
        timeout: int = 150,
        interval: float = 5.0,
    ) -> discord.Message:
        """
        Wait for specific type of game-related DM.

        Convenience wrapper around wait_for_dm_matching for common DM types.
        Uses centralized predicates from shared.message_formats to ensure
        tests stay in sync with production message formats.

        Args:
            user_id: Discord user snowflake
            game_title: Title of game to find DM for
            dm_type: Type of DM (DMType.REMINDER, JOIN, REMOVAL, or PROMOTION)
            timeout: Maximum seconds to wait
            interval: Seconds between checks

        Returns:
            Matching Discord Message object
        """
        predicates = {
            DMType.REMINDER: DMPredicates.reminder(game_title),
            DMType.JOIN: DMPredicates.join(game_title),
            DMType.REMOVAL: DMPredicates.removal(game_title),
            DMType.PROMOTION: DMPredicates.promotion(game_title),
        }

        return await self.wait_for_dm_matching(
            user_id,
            predicates[dm_type],
            timeout=timeout,
            interval=interval,
            description=f"{dm_type.value} DM for '{game_title}'",
        )
