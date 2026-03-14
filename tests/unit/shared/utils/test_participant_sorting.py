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


"""Tests for participant sorting utilities."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from shared.models.participant import ParticipantType
from shared.utils.games import DEFAULT_MAX_PLAYERS
from shared.utils.participant_sorting import (
    PartitionedParticipants,
    partition_participants,
    sort_participants,
)


@pytest.fixture
def mock_participant():
    """Create a mock participant with configurable attributes."""

    def _create(
        participant_id: str,
        joined_at: datetime | None = None,
        position_type: int = ParticipantType.SELF_ADDED,
        position: int = 0,
    ):
        participant = Mock()
        participant.id = participant_id
        participant.joined_at = joined_at or datetime.now(UTC)
        participant.position_type = position_type
        participant.position = position
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
        p2 = mock_participant(
            "2",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        )

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_placeholders_come_before_regular(self, mock_participant):
        """Test that placeholder participants come before regular participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time)
        p2 = mock_participant(
            "2",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        )

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_pre_populated_order_preserved(self, mock_participant):
        """Test that pre-populated participants maintain position-based order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant(
            "1",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        )
        p2 = mock_participant(
            "2",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=2,
        )
        p3 = mock_participant(
            "3",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=3,
        )

        # Should be sorted by position (1, 2, 3)
        result = sort_participants([p1, p2, p3])
        assert result == [p1, p2, p3]

        # Reverse input order - should still sort by position
        result = sort_participants([p3, p2, p1])
        assert result == [p1, p2, p3]

    def test_placeholder_order_preserved(self, mock_participant):
        """Test that placeholder participants maintain position-based order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant(
            "1",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        )
        p2 = mock_participant(
            "2",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=2,
        )
        p3 = mock_participant(
            "3",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=3,
        )

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

        pre1 = mock_participant(
            "pre1", joined_at=t1, position_type=ParticipantType.HOST_ADDED, position=1
        )
        pre2 = mock_participant(
            "pre2", joined_at=t1, position_type=ParticipantType.HOST_ADDED, position=2
        )
        placeholder = mock_participant(
            "placeholder",
            joined_at=t1,
            position_type=ParticipantType.HOST_ADDED,
            position=3,
        )
        regular1 = mock_participant("reg1", joined_at=t3)
        regular2 = mock_participant("reg2", joined_at=t2)

        result = sort_participants([regular1, pre2, placeholder, regular2, pre1])

        # Expected order: priority by position (pre1, pre2, placeholder), then regular by join time
        assert result == [pre1, pre2, placeholder, regular2, regular1]

    def test_pre_populated_placeholder_order_preserved(self, mock_participant):
        """Test that pre-populated and placeholder participants sort by position."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        pre = mock_participant(
            "pre",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        )
        ph = mock_participant(
            "ph",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=2,
        )

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
                position_type=ParticipantType.HOST_ADDED,
                position=i + 1,
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


class TestPartitionParticipants:
    """Tests for partition_participants function."""

    def test_partition_all_real_users(self, mock_participant):
        """Test partitioning with only real users (no placeholders)."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create participants with user objects
        participants = []
        for i in range(5):
            p = mock_participant(f"user{i}", joined_at=base_time.replace(minute=i))
            p.user = Mock()
            p.user.discord_id = f"discord_{i}"
            participants.append(p)

        result = partition_participants(participants, max_players=3)

        assert len(result.all_sorted) == 5
        assert len(result.confirmed) == 3
        assert len(result.overflow) == 2
        assert result.confirmed_real_user_ids == {"discord_0", "discord_1", "discord_2"}
        assert result.overflow_real_user_ids == {"discord_3", "discord_4"}

    def test_partition_with_placeholders_in_confirmed(self, mock_participant):
        """Test partitioning when placeholders occupy confirmed slots."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Placeholder in position 0
        placeholder = mock_participant(
            "placeholder",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        )
        placeholder.user = None
        placeholder.display_name = "Reserved"

        # Real users
        user1 = mock_participant("user1", joined_at=base_time.replace(minute=1))
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=2))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        result = partition_participants([placeholder, user1, user2], max_players=2)

        assert len(result.confirmed) == 2
        assert result.confirmed[0] == placeholder
        assert result.confirmed[1] == user1
        assert len(result.overflow) == 1
        assert result.overflow[0] == user2
        assert result.confirmed_real_user_ids == {"discord_1"}
        assert result.overflow_real_user_ids == {"discord_2"}

    def test_partition_with_placeholders_in_overflow(self, mock_participant):
        """Test partitioning when placeholders are in overflow."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Real users
        user1 = mock_participant("user1", joined_at=base_time)
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=1))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Placeholder in overflow
        placeholder = mock_participant("placeholder", joined_at=base_time.replace(minute=2))
        placeholder.user = None
        placeholder.display_name = "Reserved"

        result = partition_participants([user1, user2, placeholder], max_players=2)

        assert len(result.confirmed) == 2
        assert len(result.overflow) == 1
        assert result.overflow[0] == placeholder
        assert result.confirmed_real_user_ids == {"discord_1", "discord_2"}
        assert result.overflow_real_user_ids == set()

    def test_partition_mixed_placeholders_and_users(self, mock_participant):
        """Test complex scenario with placeholders in both confirmed and overflow."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Placeholder in confirmed (position 0)
        placeholder1 = mock_participant(
            "ph1",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        )
        placeholder1.user = None

        # Real users
        user1 = mock_participant("user1", joined_at=base_time.replace(minute=1))
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=2))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Placeholder in overflow
        placeholder2 = mock_participant("ph2", joined_at=base_time.replace(minute=3))
        placeholder2.user = None

        result = partition_participants([placeholder1, user1, user2, placeholder2], max_players=2)

        assert len(result.confirmed) == 2
        assert len(result.overflow) == 2
        assert result.confirmed_real_user_ids == {"discord_1"}
        assert result.overflow_real_user_ids == {"discord_2"}

    def test_partition_empty_list(self, mock_participant):
        """Test partitioning an empty list."""
        result = partition_participants([], max_players=5)

        assert len(result.all_sorted) == 0
        assert len(result.confirmed) == 0
        assert len(result.overflow) == 0
        assert result.confirmed_real_user_ids == set()
        assert result.overflow_real_user_ids == set()

    def test_partition_default_max_players(self, mock_participant):
        """Test that max_players defaults to DEFAULT_MAX_PLAYERS when None."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        participants = []
        for i in range(15):
            p = mock_participant(f"user{i}", joined_at=base_time.replace(minute=i))
            p.user = Mock()
            p.user.discord_id = f"discord_{i}"
            participants.append(p)

        result = partition_participants(participants, max_players=None)

        assert len(result.confirmed) == DEFAULT_MAX_PLAYERS
        assert len(result.overflow) == 15 - DEFAULT_MAX_PLAYERS
        assert len(result.confirmed_real_user_ids) == DEFAULT_MAX_PLAYERS
        assert len(result.overflow_real_user_ids) == 15 - DEFAULT_MAX_PLAYERS

    def test_partition_max_players_zero(self, mock_participant):
        """Test that max_players=0 uses default (DEFAULT_MAX_PLAYERS)."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        user = mock_participant("user1", joined_at=base_time)
        user.user = Mock()
        user.user.discord_id = "discord_1"

        result = partition_participants([user], max_players=0)

        # max_players=0 triggers default behavior (DEFAULT_MAX_PLAYERS)
        assert len(result.confirmed) == 1
        assert len(result.overflow) == 0
        assert result.confirmed_real_user_ids == {"discord_1"}
        assert result.overflow_real_user_ids == set()

    def test_partition_max_players_exceeds_count(self, mock_participant):
        """Test partitioning when max_players exceeds participant count."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        participants = []
        for i in range(3):
            p = mock_participant(f"user{i}", joined_at=base_time.replace(minute=i))
            p.user = Mock()
            p.user.discord_id = f"discord_{i}"
            participants.append(p)

        result = partition_participants(participants, max_players=10)

        assert len(result.confirmed) == 3
        assert len(result.overflow) == 0
        assert result.confirmed_real_user_ids == {"discord_0", "discord_1", "discord_2"}
        assert result.overflow_real_user_ids == set()

    def test_partition_preserves_sort_order(self, mock_participant):
        """Test that partitioning preserves the sort order from sort_participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create priority participant
        priority = mock_participant(
            "priority",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        )
        priority.user = Mock()
        priority.user.discord_id = "discord_priority"

        # Create regular participants
        user1 = mock_participant("user1", joined_at=base_time.replace(minute=2))
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=1))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Submit in random order
        result = partition_participants([user1, priority, user2], max_players=2)

        # Should be sorted: priority, user2, user1
        assert result.all_sorted == [priority, user2, user1]
        assert result.confirmed == [priority, user2]
        assert result.overflow == [user1]

    def test_partition_confirmed_overflow_id_sets_correct(self, mock_participant):
        """Test that ID sets correctly identify users in confirmed vs overflow."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create mix of users with and without discord_id
        user1 = mock_participant("user1", joined_at=base_time)
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=1))
        user2.user = Mock()
        user2.user.discord_id = None  # No discord_id

        user3 = mock_participant("user3", joined_at=base_time.replace(minute=2))
        user3.user = None  # No user object

        user4 = mock_participant("user4", joined_at=base_time.replace(minute=3))
        user4.user = Mock()
        user4.user.discord_id = "discord_4"

        result = partition_participants([user1, user2, user3, user4], max_players=2)

        # Only users with valid discord_id should be in sets
        assert result.confirmed_real_user_ids == {"discord_1"}
        assert result.overflow_real_user_ids == {"discord_4"}

    def test_partition_returns_correct_dataclass(self, mock_participant):
        """Test that partition_participants returns PartitionedParticipants instance."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        user = mock_participant("user1", joined_at=base_time)
        user.user = Mock()
        user.user.discord_id = "discord_1"

        result = partition_participants([user], max_players=1)

        assert isinstance(result, PartitionedParticipants)
        assert hasattr(result, "all_sorted")
        assert hasattr(result, "confirmed")
        assert hasattr(result, "overflow")
        assert hasattr(result, "confirmed_real_user_ids")
        assert hasattr(result, "overflow_real_user_ids")

    def test_cleared_waitlist_basic_promotion(self, mock_participant):
        """Test cleared_waitlist() detects basic overflow to confirmed promotion."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        user1 = mock_participant("user1", joined_at=base_time)
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=1))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Old state: user1 confirmed, user2 overflow
        old_partitioned = partition_participants([user1, user2], max_players=1)
        assert old_partitioned.confirmed_real_user_ids == {"discord_1"}
        assert old_partitioned.overflow_real_user_ids == {"discord_2"}

        # New state: both confirmed
        new_partitioned = partition_participants([user1, user2], max_players=2)
        assert new_partitioned.confirmed_real_user_ids == {"discord_1", "discord_2"}
        assert new_partitioned.overflow_real_user_ids == set()

        # user2 should be detected as cleared
        cleared = new_partitioned.cleared_waitlist(old_partitioned)
        assert cleared == {"discord_2"}

    def test_cleared_waitlist_with_placeholders_in_confirmed(self, mock_participant):
        """Test cleared_waitlist() with placeholder occupying confirmed slot."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        placeholder = mock_participant(
            "placeholder",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        )
        placeholder.user = None

        user1 = mock_participant("user1", joined_at=base_time.replace(minute=1))
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=2))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Old state: placeholder + user1 confirmed, user2 overflow
        old_partitioned = partition_participants([placeholder, user1, user2], max_players=2)
        assert old_partitioned.confirmed_real_user_ids == {"discord_1"}
        assert old_partitioned.overflow_real_user_ids == {"discord_2"}

        # New state: placeholder removed, all confirmed (user1, user2)
        new_partitioned = partition_participants([user1, user2], max_players=2)
        assert new_partitioned.confirmed_real_user_ids == {"discord_1", "discord_2"}
        assert new_partitioned.overflow_real_user_ids == set()

        # user2 should be detected as cleared
        cleared = new_partitioned.cleared_waitlist(old_partitioned)
        assert cleared == {"discord_2"}

    def test_cleared_waitlist_multiple_promotions(self, mock_participant):
        """Test cleared_waitlist() with multiple users promoted."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        users = []
        for i in range(4):
            user = mock_participant(f"user{i}", joined_at=base_time.replace(minute=i))
            user.user = Mock()
            user.user.discord_id = f"discord_{i + 1}"
            users.append(user)

        # Old state: only first confirmed, rest overflow
        old_partitioned = partition_participants(users, max_players=1)
        assert old_partitioned.confirmed_real_user_ids == {"discord_1"}
        assert old_partitioned.overflow_real_user_ids == {
            "discord_2",
            "discord_3",
            "discord_4",
        }

        # New state: first three confirmed
        new_partitioned = partition_participants(users, max_players=3)
        assert new_partitioned.confirmed_real_user_ids == {
            "discord_1",
            "discord_2",
            "discord_3",
        }
        assert new_partitioned.overflow_real_user_ids == {"discord_4"}

        # discord_2 and discord_3 should be detected as cleared
        cleared = new_partitioned.cleared_waitlist(old_partitioned)
        assert cleared == {"discord_2", "discord_3"}

    def test_cleared_waitlist_no_promotions(self, mock_participant):
        """Test cleared_waitlist() returns empty set when no promotions occur."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        user1 = mock_participant("user1", joined_at=base_time)
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=1))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Old state: user1 confirmed, user2 overflow
        old_partitioned = partition_participants([user1, user2], max_players=1)

        # New state: same as old (no changes)
        new_partitioned = partition_participants([user1, user2], max_players=1)

        # No promotions should be detected
        cleared = new_partitioned.cleared_waitlist(old_partitioned)
        assert cleared == set()

    def test_cleared_waitlist_ignores_placeholders(self, mock_participant):
        """Test cleared_waitlist() doesn't detect placeholders as cleared."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        placeholder1 = mock_participant(
            "placeholder1",
            joined_at=base_time,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        )
        placeholder1.user = None

        user1 = mock_participant("user1", joined_at=base_time.replace(minute=1))
        user1.user = Mock()
        user1.user.discord_id = "discord_1"

        user2 = mock_participant("user2", joined_at=base_time.replace(minute=2))
        user2.user = Mock()
        user2.user.discord_id = "discord_2"

        # Old state: placeholder + user1 confirmed, user2 overflow
        old_partitioned = partition_participants([placeholder1, user1, user2], max_players=2)
        assert old_partitioned.overflow_real_user_ids == {"discord_2"}

        # New state: removed first placeholder, user1 + user2 confirmed
        new_partitioned = partition_participants([user1, user2], max_players=2)

        # Only user2 should be detected (not placeholder1)
        cleared = new_partitioned.cleared_waitlist(old_partitioned)
        assert cleared == {"discord_2"}
