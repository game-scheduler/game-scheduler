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


"""Status transition utilities for game lifecycle management."""

from enum import StrEnum


class GameStatus(StrEnum):
    """Valid game status values."""

    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @property
    def display_name(self) -> str:
        """User-friendly display name for the status."""
        display_map = {
            "SCHEDULED": "Scheduled",
            "IN_PROGRESS": "In Progress",
            "COMPLETED": "Completed",
            "CANCELLED": "Cancelled",
        }
        return display_map[self.value]


class StatusTransitionError(Exception):
    """Raised when invalid status transition is attempted."""

    pass


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Check if status transition is valid.

    Valid transitions:
    - SCHEDULED -> IN_PROGRESS (game starts)
    - SCHEDULED -> CANCELLED (game cancelled before start)
    - IN_PROGRESS -> COMPLETED (game ends)
    - IN_PROGRESS -> CANCELLED (game cancelled during play)

    Args:
        current_status: Current game status
        new_status: Proposed new status

    Returns:
        True if transition is valid
    """
    valid_transitions = {
        GameStatus.SCHEDULED: [GameStatus.IN_PROGRESS, GameStatus.CANCELLED],
        GameStatus.IN_PROGRESS: [GameStatus.COMPLETED, GameStatus.CANCELLED],
        GameStatus.COMPLETED: [],
        GameStatus.CANCELLED: [],
    }

    try:
        current = GameStatus(current_status)
        new = GameStatus(new_status)
        return new in valid_transitions[current]
    except (ValueError, KeyError):
        return False


def get_next_status(current_status: str) -> str | None:
    """
    Get next automatic status in game lifecycle.

    Args:
        current_status: Current game status

    Returns:
        Next status or None if no automatic transition
    """
    if current_status == GameStatus.SCHEDULED:
        return GameStatus.IN_PROGRESS
    if current_status == GameStatus.IN_PROGRESS:
        return GameStatus.COMPLETED
    return None
