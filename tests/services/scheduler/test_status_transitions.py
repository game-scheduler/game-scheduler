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


"""Tests for game status transition validation."""

from services.scheduler.utils.status_transitions import (
    GameStatus,
    get_next_status,
    is_valid_transition,
)


class TestStatusTransitions:
    """Test suite for status transition validation."""

    def test_valid_scheduled_to_in_progress(self):
        """SCHEDULED can transition to IN_PROGRESS."""
        assert is_valid_transition("SCHEDULED", "IN_PROGRESS") is True

    def test_valid_scheduled_to_cancelled(self):
        """SCHEDULED can transition to CANCELLED."""
        assert is_valid_transition("SCHEDULED", "CANCELLED") is True

    def test_valid_in_progress_to_completed(self):
        """IN_PROGRESS can transition to COMPLETED."""
        assert is_valid_transition("IN_PROGRESS", "COMPLETED") is True

    def test_valid_in_progress_to_cancelled(self):
        """IN_PROGRESS can transition to CANCELLED."""
        assert is_valid_transition("IN_PROGRESS", "CANCELLED") is True

    def test_invalid_scheduled_to_completed(self):
        """SCHEDULED cannot directly transition to COMPLETED."""
        assert is_valid_transition("SCHEDULED", "COMPLETED") is False

    def test_invalid_completed_transitions(self):
        """COMPLETED is a terminal state with no valid transitions."""
        assert is_valid_transition("COMPLETED", "IN_PROGRESS") is False
        assert is_valid_transition("COMPLETED", "SCHEDULED") is False
        assert is_valid_transition("COMPLETED", "CANCELLED") is False

    def test_invalid_cancelled_transitions(self):
        """CANCELLED is a terminal state with no valid transitions."""
        assert is_valid_transition("CANCELLED", "IN_PROGRESS") is False
        assert is_valid_transition("CANCELLED", "SCHEDULED") is False
        assert is_valid_transition("CANCELLED", "COMPLETED") is False

    def test_invalid_status_values(self):
        """Invalid status values return False."""
        assert is_valid_transition("INVALID", "IN_PROGRESS") is False
        assert is_valid_transition("SCHEDULED", "INVALID") is False
        assert is_valid_transition("INVALID", "INVALID") is False

    def test_get_next_status_scheduled(self):
        """Next status after SCHEDULED is IN_PROGRESS."""
        assert get_next_status("SCHEDULED") == GameStatus.IN_PROGRESS

    def test_get_next_status_in_progress(self):
        """Next status after IN_PROGRESS is COMPLETED."""
        assert get_next_status("IN_PROGRESS") == GameStatus.COMPLETED

    def test_get_next_status_completed(self):
        """COMPLETED has no next automatic status."""
        assert get_next_status("COMPLETED") is None

    def test_get_next_status_cancelled(self):
        """CANCELLED has no next automatic status."""
        assert get_next_status("CANCELLED") is None

    def test_game_status_enum_values(self):
        """GameStatus enum has expected values."""
        assert GameStatus.SCHEDULED == "SCHEDULED"
        assert GameStatus.IN_PROGRESS == "IN_PROGRESS"
        assert GameStatus.COMPLETED == "COMPLETED"
        assert GameStatus.CANCELLED == "CANCELLED"
