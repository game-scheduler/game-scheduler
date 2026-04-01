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
        self._channel_mention_pattern = re.compile(r"(?<!<)#([^\s<>]+)")
        self._discord_channel_url_pattern = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)")
        self._snowflake_token_pattern = re.compile(r"<#(\d+)>")

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

        url_matches = list(self._discord_channel_url_pattern.finditer(location_text))
        hash_matches = list(self._channel_mention_pattern.finditer(location_text))
        snowflake_matches = list(self._snowflake_token_pattern.finditer(location_text))

        if not url_matches and not hash_matches and not snowflake_matches:
            return location_text, []

        channels = await self.discord_client.get_guild_channels(guild_discord_id)
        text_channels = [ch for ch in channels if ch.get("type") == 0]
        text_channel_ids = {ch["id"] for ch in text_channels}

        resolved = location_text
        errors: list[dict] = []

        for url_match in url_matches:
            url_guild_id = url_match.group(1)
            url_channel_id = url_match.group(2)
            full_url = url_match.group(0)

            if url_guild_id != guild_discord_id:
                continue

            if url_channel_id not in text_channel_ids:
                errors.append({
                    "type": "not_found",
                    "input": full_url,
                    "reason": "This link is not a valid text channel in this server",
                    "suggestions": [],
                })
            else:
                resolved = resolved.replace(full_url, f"<#{url_channel_id}>", 1)

        errors.extend(self._check_snowflake_tokens(snowflake_matches, text_channel_ids))

        for match in hash_matches:
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

    def _check_snowflake_tokens(
        self,
        snowflake_matches: list[re.Match],
        text_channel_ids: set[str],
    ) -> list[dict]:
        """Validate <#id> tokens against the guild's text channel list."""
        errors: list[dict] = []
        for m in snowflake_matches:
            channel_id = m.group(1)
            if channel_id not in text_channel_ids:
                errors.append({
                    "type": "not_found",
                    "input": f"<#{channel_id}>",
                    "reason": f"Channel <#{channel_id}> is not a valid text channel in this server",
                    "suggestions": [],
                })
        return errors


def render_where_display(where: str | None, channels: list[dict]) -> str | None:
    """
    Replace `<#id>` tokens in a stored location string with `#name`.

    Returns None if `where` is None or contains no `<#id>` tokens (plain text).
    Leaves tokens with unknown IDs unchanged.
    """
    if where is None:
        return None
    pattern = re.compile(r"<#(\d+)>")
    if not pattern.search(where):
        return None
    id_to_name = {ch["id"]: ch["name"] for ch in channels}

    def _replace(m: re.Match) -> str:
        name = id_to_name.get(m.group(1))
        return f"#{name}" if name is not None else m.group(0)

    return pattern.sub(_replace, where)
