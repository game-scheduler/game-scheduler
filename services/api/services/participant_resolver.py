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
Participant resolver service for validating and resolving @mentions.

Handles resolution of Discord user mentions and placeholder strings for
pre-populating game participant lists.
"""

import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared.cache import client as cache_client
from shared.cache import projection as member_projection
from shared.models import user as user_model

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation error for participant resolution."""

    def __init__(self, invalid_mentions: list[dict], valid_participants: list[str]) -> None:
        """
        Initialize validation error.

        Args:
            invalid_mentions: List of invalid mention errors
            valid_participants: List of successfully resolved participants
        """
        self.invalid_mentions = invalid_mentions
        self.valid_participants = valid_participants
        super().__init__(f"Failed to resolve {len(invalid_mentions)} mentions")


class ParticipantResolver:
    """Resolves initial participant list from @mentions and placeholders."""

    def __init__(self) -> None:
        # Pattern to match Discord mention format: <@123456789012345678>
        self._discord_mention_pattern = re.compile(r"^<@(\d{17,20})>$")

    async def _resolve_discord_mention_format(
        self,
        guild_discord_id: str,
        input_text: str,
        discord_id: str,
    ) -> tuple[dict | None, dict | None]:
        """
        Resolve Discord internal mention format <@discord_id>.

        Args:
            guild_discord_id: Discord guild snowflake ID
            input_text: Original input text
            discord_id: Extracted Discord user ID

        Returns:
            Tuple of (valid_participant, validation_error)
            Returns (participant_dict, None) on success, (None, error_dict) on failure
        """
        try:
            redis = await cache_client.get_redis_client()
            member = await member_projection.get_member(guild_discord_id, discord_id, redis=redis)
            if member is None:
                return (
                    None,
                    {
                        "input": input_text,
                        "reason": "User not found in server",
                        "suggestions": [],
                    },
                )
            return (
                {
                    "type": "discord",
                    "discord_id": discord_id,
                    "username": member["username"],
                    "display_name": (
                        member.get("nick") or member.get("global_name") or member["username"]
                    ),
                    "original_input": input_text,
                },
                None,
            )
        except Exception as e:
            logger.exception(
                "Unexpected error fetching guild member %s: %s",
                discord_id,
                e,
            )
            return (
                None,
                {
                    "input": input_text,
                    "reason": "Internal error fetching user",
                    "suggestions": [],
                },
            )

    async def _resolve_user_friendly_mention(
        self,
        guild_discord_id: str,
        input_text: str,
        mention_text: str,
    ) -> tuple[dict | None, dict | None]:
        """
        Resolve user-friendly @username mention via Redis sorted set prefix search.

        Args:
            guild_discord_id: Discord guild snowflake ID
            input_text: Original input text (@username)
            mention_text: Username to search (without @)

        Returns:
            Tuple of (valid_participant, validation_error)
            Returns (participant_dict, None) on single match
            Returns (None, error_dict) on no match, multiple matches, or error
        """
        try:
            redis = await cache_client.get_redis_client()
            members = await member_projection.search_members_by_prefix(
                guild_discord_id, mention_text, redis=redis
            )

            if len(members) == 0:
                return (
                    None,
                    {
                        "input": input_text,
                        "reason": "User not found in server",
                        "suggestions": [],
                    },
                )
            if len(members) == 1:
                return (
                    {
                        "type": "discord",
                        "discord_id": members[0]["uid"],
                        "original_input": input_text,
                    },
                    None,
                )

            # Multiple matches - disambiguation needed
            suggestions: list[dict[str, str]] = [
                {
                    "discordId": m["uid"],
                    "username": m["username"],
                    "displayName": (m.get("nick") or m.get("global_name") or m["username"]),
                }
                for m in members[:5]
            ]
            return (
                None,
                {
                    "input": input_text,
                    "reason": "Multiple matches found",
                    "suggestions": suggestions,
                },
            )

        except Exception as e:
            logger.exception(
                "Unexpected error searching guild members for '%s': %s",
                mention_text,
                e,
            )
            return (
                None,
                {
                    "input": input_text,
                    "reason": "Internal error searching for user",
                    "suggestions": [],
                },
            )

    def _create_placeholder_participant(self, input_text: str) -> dict:
        """
        Create placeholder participant entry.

        Args:
            input_text: Placeholder display name

        Returns:
            Placeholder participant dictionary
        """
        return {
            "type": "placeholder",
            "display_name": input_text,
            "original_input": input_text,
        }

    async def _process_single_participant_input(
        self,
        guild_discord_id: str,
        input_text: str,
    ) -> tuple[dict | None, dict | None]:
        """
        Process a single participant input and resolve to participant or error.

        Args:
            guild_discord_id: Discord guild snowflake ID
            input_text: Single participant input (@mention, <@id>, or placeholder)

        Returns:
            Tuple of (participant_dict, error_dict) - one will be None
        """
        input_text = input_text.strip()

        if not input_text:
            return None, None

        mention_match = self._discord_mention_pattern.match(input_text)
        if mention_match:
            discord_id = mention_match.group(1)
            return await self._resolve_discord_mention_format(
                guild_discord_id, input_text, discord_id
            )

        if input_text.startswith("@"):
            mention_text = input_text[1:].lower()
            return await self._resolve_user_friendly_mention(
                guild_discord_id, input_text, mention_text
            )

        return self._create_placeholder_participant(input_text), None

    async def resolve_initial_participants(
        self,
        guild_discord_id: str,
        participant_inputs: list[str],
    ) -> tuple[list[dict], list[dict]]:
        """
        Resolve initial participant list from @mentions and placeholders.

        Accepts both user-friendly format (@username) and Discord internal format (<@discord_id>).

        Args:
            guild_discord_id: Discord guild snowflake ID
            participant_inputs: List of @mentions, <@discord_id>, or placeholder strings

        Returns:
            Tuple of (valid_participants, validation_errors)
            valid_participants: List of dicts with type, discord_id/display_name
            validation_errors: List of dicts with input, reason, suggestions
        """
        valid_participants = []
        validation_errors: list[dict[str, Any]] = []

        for input_text in participant_inputs:
            participant, error = await self._process_single_participant_input(
                guild_discord_id, input_text
            )

            if participant:
                valid_participants.append(participant)
            if error:
                validation_errors.append(error)

        return valid_participants, validation_errors

    async def ensure_user_exists(
        self,
        db: AsyncSession,
        discord_id: str,
    ) -> user_model.User:
        """
        Ensure user exists in database, create if not.

        Does not commit. Caller must commit transaction. Uses flush() to
        generate user ID if creating new user.

        Args:
            db: Database session
            discord_id: Discord user snowflake ID

        Returns:
            User model instance
        """
        result = await db.execute(
            select(user_model.User).where(user_model.User.discord_id == discord_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = user_model.User(discord_id=discord_id)
            db.add(user)
            await db.flush()

        return user
