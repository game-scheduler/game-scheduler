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


"""Unit tests for CloneGameRequest schema validation rules."""

import datetime

import pytest
from pydantic import ValidationError

from services.api.schemas.clone_game import CarryoverOption, CloneGameRequest

FUTURE = datetime.datetime(2027, 1, 1, 12, 0, 0)
PAST = datetime.datetime(2020, 1, 1, 12, 0, 0)
SCHEDULED_AT = datetime.datetime(2026, 9, 1, 18, 0, 0)


def test_clone_request_no_carryover_is_valid():
    """NO carryover with no deadlines should be accepted."""
    req = CloneGameRequest(
        scheduled_at=SCHEDULED_AT,
        player_carryover=CarryoverOption.NO,
        waitlist_carryover=CarryoverOption.NO,
    )
    assert req.player_carryover == CarryoverOption.NO
    assert req.waitlist_carryover == CarryoverOption.NO


def test_clone_request_yes_carryover_is_valid():
    """YES carryover without deadlines should be accepted."""
    req = CloneGameRequest(
        scheduled_at=SCHEDULED_AT,
        player_carryover=CarryoverOption.YES,
        waitlist_carryover=CarryoverOption.YES,
    )
    assert req.player_carryover == CarryoverOption.YES


def test_clone_request_yes_with_deadline_and_future_deadline_is_valid():
    """YES_WITH_DEADLINE with a future deadline should be accepted."""
    req = CloneGameRequest(
        scheduled_at=SCHEDULED_AT,
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=FUTURE,
        waitlist_carryover=CarryoverOption.NO,
    )
    assert req.player_deadline == FUTURE


def test_clone_request_yes_with_deadline_missing_deadline_is_rejected():
    """YES_WITH_DEADLINE without player_deadline must be rejected."""
    with pytest.raises(ValidationError):
        CloneGameRequest(
            scheduled_at=SCHEDULED_AT,
            player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        )


def test_clone_request_yes_with_deadline_past_deadline_is_rejected():
    """YES_WITH_DEADLINE with a past player_deadline must be rejected."""
    with pytest.raises(ValidationError):
        CloneGameRequest(
            scheduled_at=SCHEDULED_AT,
            player_carryover=CarryoverOption.YES_WITH_DEADLINE,
            player_deadline=PAST,
        )


def test_clone_request_waitlist_yes_with_deadline_missing_deadline_is_rejected():
    """YES_WITH_DEADLINE on waitlist without waitlist_deadline must be rejected."""
    with pytest.raises(ValidationError):
        CloneGameRequest(
            scheduled_at=SCHEDULED_AT,
            player_carryover=CarryoverOption.NO,
            waitlist_carryover=CarryoverOption.YES_WITH_DEADLINE,
        )


def test_clone_request_waitlist_yes_with_deadline_past_deadline_is_rejected():
    """YES_WITH_DEADLINE on waitlist with a past deadline must be rejected."""
    with pytest.raises(ValidationError):
        CloneGameRequest(
            scheduled_at=SCHEDULED_AT,
            player_carryover=CarryoverOption.NO,
            waitlist_carryover=CarryoverOption.YES_WITH_DEADLINE,
            waitlist_deadline=PAST,
        )
