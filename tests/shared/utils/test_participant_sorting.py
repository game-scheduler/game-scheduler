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


"""Tests for participant sorting utilities."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from shared.utils.participant_sorting import sort_participants


@pytest.fixture
def mock_participant():
    """Create a mock participant with configurable attributes."""

    def _create(
        participant_id: str,
        joined_at: datetime | None = None,
        pre_filled_position: int | None = None,
    ):
        participant = Mock()
        participant.id = participant_id
        participant.joined_at = joined_at or datetime.now(UTC)
        participant.pre_filled_position = pre_filled_position
        return participant

    return _create


class TestSortParticipants:
    """Tests for sort_participants function."""

    def test_empty_list_returns_empty(self, mock_participant):
        """Test that empty list returns empty list."""
        result = sort_participants([])
        assert result == []

    def test_single_participant_returns_unchanged(self, mock_participant):
        """Test that single participant list returns unchanged."""
        p1 = mock_participant("1")
        result = sort_participants([p1])
        assert result == [p1]

    def test_pre_populated_comes_before_regular(self, mock_participant):
        """Test that pre-populated participants come before regular participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time)
        p2 = mock_participant("2", joined_at=base_time, pre_filled_position=1)

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_placeholders_come_before_regular(self, mock_participant):
        """Test that placeholder participants come before regular participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time)
        p2 = mock_participant("2", joined_at=base_time, pre_filled_position=1)

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_pre_populated_order_preserved(self, mock_participant):
        """Test that pre-populated participants maintain position-based order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time, pre_filled_position=1)
        p2 = mock_participant("2", joined_at=base_time, pre_filled_position=2)
        p3 = mock_participant("3", joined_at=base_time, pre_filled_position=3)

        # Should be sorted by position (1, 2, 3)
        result = sort_participants([p1, p2, p3])
        assert result == [p1, p2, p3]

        # Reverse input order - should still sort by position
        result = sort_participants([p3, p2, p1])
        assert result == [p1, p2, p3]

    def test_placeholder_order_preserved(self, mock_participant):
        """Test that placeholder participants maintain position-based order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time, pre_filled_position=1)
        p2 = mock_participant("2", joined_at=base_time, pre_filled_position=2)
        p3 = mock_participant("3", joined_at=base_time, pre_filled_position=3)

        # Should be sorted by position (1, 2, 3)
        result = sort_participants([p1, p2, p3])
        assert result == [p1, p2, p3]

        # Reverse input order - should still sort by position
        result = sort_participants([p3, p2, p1])
        assert result == [p1, p2, p3]

    def test_regular_sorted_by_join_time(self, mock_participant):
        """Test that regular participants are sorted by joined_at timestamp."""
        t1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=UTC)
        t3 = datetime(2025, 1, 1, 12, 2, 0, tzinfo=UTC)

        p1 = mock_participant("1", joined_at=t2)
        p2 = mock_participant("2", joined_at=t3)
        p3 = mock_participant("3", joined_at=t1)

        result = sort_participants([p1, p2, p3])
        assert result == [p3, p1, p2]

    def test_mixed_participants_correct_order(self, mock_participant):
        """Test complex scenario with all participant types."""
        t1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=UTC)
        t3 = datetime(2025, 1, 1, 12, 2, 0, tzinfo=UTC)

        pre1 = mock_participant("pre1", joined_at=t1, pre_filled_position=1)
        pre2 = mock_participant("pre2", joined_at=t1, pre_filled_position=2)
        placeholder = mock_participant("placeholder", joined_at=t1, pre_filled_position=3)
        regular1 = mock_participant("reg1", joined_at=t3)
        regular2 = mock_participant("reg2", joined_at=t2)

        result = sort_participants([regular1, pre2, placeholder, regular2, pre1])

        # Expected order: priority by position (pre1, pre2, placeholder), then regular by join time
        assert result == [pre1, pre2, placeholder, regular2, regular1]

    def test_pre_populated_placeholder_order_preserved(self, mock_participant):
        """Test that pre-populated and placeholder participants sort by position."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        pre = mock_participant("pre", joined_at=base_time, pre_filled_position=1)
        ph = mock_participant("ph", joined_at=base_time, pre_filled_position=2)

        # Should sort by position (pre=1, ph=2)
        result = sort_participants([pre, ph])
        assert result == [pre, ph]

        # Reverse input order - should still sort by position
        result = sort_participants([ph, pre])
        assert result == [pre, ph]

    def test_large_list_maintains_order(self, mock_participant):
        """Test that sorting works correctly with larger lists."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create 5 priority and 10 regular participants
        priority = [
            mock_participant(
                f"priority{i}",
                joined_at=base_time,
                pre_filled_position=i + 1,
            )
            for i in range(5)
        ]
        regular = [
            mock_participant(f"regular{i}", joined_at=base_time.replace(minute=i))
            for i in range(10)
        ]

        # Mix them up
        mixed = regular[5:] + priority[2:] + regular[:5] + priority[:2]

        result = sort_participants(mixed)

        # First 5 should be priority sorted by position (0, 1, 2, 3, 4)
        assert result[:5] == priority
        # Next 10 should be regular sorted by time
        assert result[5:] == regular
