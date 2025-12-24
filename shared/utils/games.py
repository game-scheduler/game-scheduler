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


"""Game-related utilities and constants."""

DEFAULT_MAX_PLAYERS = 10
"""Default maximum number of players when max_players is not specified."""


def resolve_max_players(max_players_value: int | None) -> int:
    """
    Resolve max_players value, defaulting to DEFAULT_MAX_PLAYERS if None.

    This utility function provides a single place to handle the common pattern
    of: max_players = value or DEFAULT_MAX_PLAYERS

    Args:
        max_players_value: The max_players value to resolve (may be None)

    Returns:
        The max_players value if provided, otherwise DEFAULT_MAX_PLAYERS

    Example:
        >>> resolve_max_players(5)
        5
        >>> resolve_max_players(None)
        10
    """
    return max_players_value or DEFAULT_MAX_PLAYERS
