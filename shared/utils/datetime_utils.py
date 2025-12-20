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


"""Datetime utility functions for consistent formatting."""

from datetime import UTC, datetime


def format_datetime_as_utc(dt: datetime) -> str:
    """
    Format a naive datetime as UTC ISO8601 with 'Z' suffix.

    This function assumes the input datetime is in UTC and explicitly marks it
    as such for serialization. It converts Python's "+00:00" timezone format
    to the more standard "Z" (Zulu time) suffix.

    Args:
        dt: A naive datetime object assumed to be in UTC timezone

    Returns:
        ISO8601 formatted string with 'Z' suffix (e.g., "2025-12-20T15:30:00Z")

    Examples:
        >>> dt = datetime(2025, 12, 20, 15, 30, 0)
        >>> format_datetime_as_utc(dt)
        '2025-12-20T15:30:00Z'

        >>> # Midnight case (no offset applied)
        >>> dt = datetime(2025, 11, 27, 0, 15, 0)
        >>> format_datetime_as_utc(dt)
        '2025-11-27T00:15:00Z'
    """
    return dt.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
