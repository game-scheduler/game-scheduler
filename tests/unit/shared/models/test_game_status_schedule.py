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


"""Tests for GameStatusSchedule model."""

from datetime import timedelta

from shared.models import GameStatusSchedule
from shared.models.base import generate_uuid, utc_now


class TestGameStatusScheduleModel:
    """Test suite for GameStatusSchedule model."""

    def test_create_status_schedule(self):
        """Can create a GameStatusSchedule instance."""
        transition_time = utc_now() + timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=transition_time,
        )

        assert schedule.game_id == "game-123"
        assert schedule.target_status == "IN_PROGRESS"
        assert schedule.transition_time == transition_time

    def test_default_values(self):
        """Default values are set when explicitly provided or after persist."""
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
            executed=False,
        )

        assert schedule.executed is False

    def test_id_generation(self):
        """ID can be generated using default function."""

        schedule = GameStatusSchedule(
            id=generate_uuid(),
            game_id="game-1",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
        )

        assert schedule.id is not None

    def test_executed_flag(self):
        """Executed flag can be set and retrieved."""
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
            executed=False,
        )

        assert schedule.executed is False

        schedule.executed = True
        assert schedule.executed is True

    def test_transition_time_in_past(self):
        """Can create schedule with transition_time in the past."""
        past_time = utc_now() - timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=past_time,
        )

        assert schedule.transition_time < utc_now()

    def test_transition_time_in_future(self):
        """Can create schedule with transition_time in the future."""
        future_time = utc_now() + timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=future_time,
        )

        assert schedule.transition_time > utc_now()

    def test_target_status_values(self):
        """Can set various target status values."""
        statuses = ["IN_PROGRESS", "COMPLETED", "CANCELLED"]

        for status in statuses:
            schedule = GameStatusSchedule(
                game_id="game-123",
                target_status=status,
                transition_time=utc_now(),
            )
            assert schedule.target_status == status
