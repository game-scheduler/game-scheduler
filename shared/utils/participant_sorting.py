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


"""Participant sorting utilities for consistent ordering across services."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from shared.models.participant import ParticipantType
from shared.utils.games import DEFAULT_MAX_PLAYERS

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant


@dataclass
class PartitionedParticipants:
    """Result of partitioning participants into confirmed and overflow groups.

    This provides a single source of truth for participant ordering that accounts
    for placeholders, ensuring consistent behavior across bot formatters, API
    services, and notification logic.

    Participants are sorted by (position_type, position, joined_at) before
    partitioning into confirmed/overflow groups based on max_players.
    """

    all_sorted: list["GameParticipant"]
    """All participants sorted by (position_type, position, joined_at)"""

    confirmed: list["GameParticipant"]
    """Participants in confirmed slots (0 to max_players-1)"""

    overflow: list["GameParticipant"]
    """Participants in overflow/waitlist (max_players onwards)"""

    confirmed_real_user_ids: set[str]
    """Discord IDs of confirmed participants with user accounts"""

    overflow_real_user_ids: set[str]
    """Discord IDs of overflow participants with user accounts"""

    def cleared_waitlist(self, previous: "PartitionedParticipants") -> set[str]:
        """
        Identify users who cleared the waitlist (promoted from overflow to confirmed).

        Compares this state with a previous state to find users who were in overflow
        before but are now in confirmed participants.

        Args:
            previous: Previous PartitionedParticipants state

        Returns:
            Set of Discord IDs of users promoted from overflow to confirmed
        """
        return {
            discord_id
            for discord_id in previous.overflow_real_user_ids
            if discord_id in self.confirmed_real_user_ids
        }


def resolve_role_position(
    user_role_ids: list[str], priority_role_ids: list[str]
) -> tuple[int, int]:
    """Determine position_type and position for a joining user based on role priority.

    Checks priority_role_ids in order and returns the index of the first match.
    Returns SELF_ADDED when there is no match or when priority_role_ids is empty.

    Args:
        user_role_ids: Role IDs the user holds in the guild
        priority_role_ids: Ordered list of priority role IDs from the game template

    Returns:
        (ROLE_MATCHED, index) on a match, (SELF_ADDED, 0) otherwise
    """
    user_role_set = set(user_role_ids)
    for index, role_id in enumerate(priority_role_ids):
        if role_id in user_role_set:
            return (ParticipantType.ROLE_MATCHED, index)
    return (ParticipantType.SELF_ADDED, 0)


def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
    """Sort participants by position_type, position, and join time.

    Uses a three-tuple sort key for consistent ordering:
    1. position_type (8000=host-added, 24000=self-added) - determines priority class
    2. position - relative position within the priority class
    3. joined_at - tie-breaker for participants with same position_type and position

    This eliminates the need for NULL checking and two-list merging.

    Args:
        participants: List of GameParticipant models to sort

    Returns:
        Sorted list with host-added participants first (by position),
        followed by self-added participants (by position, then join time)
    """
    return sorted(
        participants,
        key=lambda p: (p.position_type, p.position, p.joined_at),
    )


def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
) -> PartitionedParticipants:
    """Sort and partition participants into confirmed and overflow groups.

    This function handles both real users and placeholder participants,
    ensuring consistent ordering logic across the application.

    Args:
        participants: List of all participants (including placeholders)
        max_players: Maximum confirmed participants (defaults to DEFAULT_MAX_PLAYERS if None)

    Returns:
        PartitionedParticipants with sorted lists and pre-computed ID sets

    Example:
        >>> partitioned = partition_participants(game.participants, game.max_players)
        >>> confirmed_ids = partitioned.confirmed_real_user_ids
        >>> overflow_ids = partitioned.overflow_real_user_ids
    """
    max_players = max_players or DEFAULT_MAX_PLAYERS
    sorted_all = sort_participants(participants)
    confirmed = sorted_all[:max_players]
    overflow = sorted_all[max_players:]

    confirmed_ids = {p.user.discord_id for p in confirmed if p.user and p.user.discord_id}
    overflow_ids = {p.user.discord_id for p in overflow if p.user and p.user.discord_id}

    return PartitionedParticipants(
        all_sorted=sorted_all,
        confirmed=confirmed,
        overflow=overflow,
        confirmed_real_user_ids=confirmed_ids,
        overflow_real_user_ids=overflow_ids,
    )
