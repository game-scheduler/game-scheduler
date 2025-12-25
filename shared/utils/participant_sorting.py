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


"""Participant sorting utilities for consistent ordering across services."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant

from shared.utils.games import DEFAULT_MAX_PLAYERS


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
