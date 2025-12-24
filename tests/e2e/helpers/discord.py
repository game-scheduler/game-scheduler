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

import discord


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

    async def connect(self):
        """Connect to Discord using bot token."""
        if not self._connected:
            await self.client.login(self.bot_token)
            self._connected = True

    async def disconnect(self):
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
    ):
        """
        Verify game announcement embed structure and content.

        Args:
            embed: Discord embed object to verify
            expected_title: Expected game title
            expected_host_id: Expected Discord host user ID
            expected_max_players: Expected maximum player count

        Raises:
            AssertionError: If embed does not match expected values
        """
        assert embed.title == expected_title, f"Title mismatch: {embed.title}"

        assert embed.author and embed.author.name, "Embed should have author with name"
        assert "Host:" in embed.author.name, f"Author should contain 'Host:': {embed.author.name}"

        # Find the participants field - it has format "Participants (X/Y)"
        participants_field = None
        for field in embed.fields:
            if field.name and "Participants" in field.name:
                participants_field = field.value
                break

        assert participants_field is not None, "Participants field missing"
        assert f"/{expected_max_players}" in field.name, (
            f"Max players incorrect in field name: {field.name}"
        )
