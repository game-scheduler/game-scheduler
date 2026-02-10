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


"""
Channel resolver service for validating and resolving #channel mentions.

Handles resolution of Discord channel mentions in game location text,
converting #channel-name references to clickable Discord links.
"""

import re

from shared.discord import client as discord_client_module


class ChannelResolver:
    """Resolves channel mentions in location text to Discord link format."""

    def __init__(self, discord_client: discord_client_module.DiscordAPIClient) -> None:
        """
        Initialize channel resolver.

        Args:
            discord_client: Discord API client for channel lookup
        """
        self.discord_client = discord_client
        self._channel_mention_pattern = re.compile(r"#([\w-]+)")

    async def resolve_channel_mentions(
        self,
        location_text: str,
        guild_discord_id: str,
    ) -> tuple[str, list[dict]]:
        """
        Resolve channel mentions in location text.

        Args:
            location_text: User input location text (e.g., "Meet in #general")
            guild_discord_id: Discord guild ID

        Returns:
            Tuple of (resolved_text, validation_errors):
            - resolved_text: Text with valid channels converted to <#id> format
            - validation_errors: List of error dicts for invalid/ambiguous channels
        """
        if not location_text:
            return location_text, []

        matches = list(self._channel_mention_pattern.finditer(location_text))
        if not matches:
            return location_text, []

        channels = await self.discord_client.get_guild_channels(guild_discord_id)
        text_channels = [ch for ch in channels if ch.get("type") == 0]

        resolved = location_text
        errors = []

        for match in matches:
            channel_name = match.group(1)
            matching_channels = [
                ch for ch in text_channels if ch["name"].lower() == channel_name.lower()
            ]

            if len(matching_channels) == 1:
                resolved = resolved.replace(
                    f"#{channel_name}",
                    f"<#{matching_channels[0]['id']}>",
                    1,
                )
            elif len(matching_channels) > 1:
                errors.append({
                    "type": "ambiguous",
                    "input": f"#{channel_name}",
                    "reason": f"Multiple channels match '#{channel_name}'",
                    "suggestions": [
                        {"id": ch["id"], "name": ch["name"]} for ch in matching_channels
                    ],
                })
            else:
                similar_channels = [
                    ch for ch in text_channels if channel_name.lower() in ch["name"].lower()
                ][:5]
                errors.append({
                    "type": "not_found",
                    "input": f"#{channel_name}",
                    "reason": f"Channel '#{channel_name}' not found",
                    "suggestions": [
                        {"id": ch["id"], "name": ch["name"]} for ch in similar_channels
                    ],
                })

        return resolved, errors
