# Copyright 2026 Bret McKee
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


"""Unit tests for participant action event builder."""

from unittest.mock import MagicMock

from services.scheduler.participant_action_event_builder import (
    build_participant_action_event,
)
from shared.messaging.events import EventType


class TestBuildParticipantActionEvent:
    def test_returns_participant_drop_due_event_type(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        event, ttl = build_participant_action_event(record)

        assert event.event_type == EventType.PARTICIPANT_DROP_DUE

    def test_event_data_contains_game_and_participant_ids(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        event, _ = build_participant_action_event(record)

        assert event.data["game_id"] == "game-abc"
        assert event.data["participant_id"] == "participant-xyz"

    def test_ttl_is_none(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        _, ttl = build_participant_action_event(record)

        assert ttl is None
