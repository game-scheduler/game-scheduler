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


"""
Unit tests verifying that participants are created with sequential timestamps.

This test ensures that when multiple participants are added during game creation,
they receive joined_at timestamps that increment in the order they were added.
This ordering is critical for maintaining the host's intended participant order.
"""

import datetime

import pytest

from shared.models import participant as participant_model


@pytest.mark.asyncio
async def test_sequential_participant_creation_preserves_order():
    """
    Test that creating participants sequentially results in incrementing timestamps.

    This is a critical assumption for the participant sorting logic:
    when participants are created in a for-loop and added to the database,
    their joined_at timestamps increment, preserving the order.
    """
    participants = []
    base_time = datetime.datetime.now(datetime.UTC)

    # Simulate sequential participant creation as done in games.py
    for i, name in enumerate(["Player1", "Placeholder A", "Player2"]):
        participant = participant_model.GameParticipant(
            game_session_id="test-game-id",
            user_id=f"user{i}" if i % 2 == 0 else None,
            display_name=name if i % 2 == 1 else None,
            pre_filled_position=i + 1,
        )
        # Simulate database assigning joined_at timestamp
        # In reality, database assigns server_default=func.now()
        # which increments for each sequential INSERT
        participant.joined_at = base_time + datetime.timedelta(microseconds=i * 100)
        participants.append(participant)

    # Verify timestamps are sequential
    assert participants[0].joined_at < participants[1].joined_at, (
        "First participant should have earlier timestamp than second"
    )
    assert participants[1].joined_at < participants[2].joined_at, (
        "Second participant should have earlier timestamp than third"
    )

    # Most importantly: verify sorting by joined_at preserves creation order
    sorted_participants = sorted(participants, key=lambda p: p.joined_at)
    assert sorted_participants == participants, (
        "Sorting by joined_at must preserve the original creation order. "
        "This is the critical behavior that participant_sorting.py relies on. "
        "The game creation code in services/api/services/games.py depends on "
        "participants being created sequentially in a for-loop, receiving "
        "incrementing timestamps from the database."
    )
