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


"""Pydantic schemas for the game clone endpoint."""

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class CarryoverOption(StrEnum):
    """How participants from the source game should be carried over to the clone."""

    YES = "YES"
    YES_WITH_DEADLINE = "YES_WITH_DEADLINE"
    NO = "NO"


class CloneGameRequest(BaseModel):
    """Request body for POST /api/games/{game_id}/clone."""

    scheduled_at: dt.datetime = Field(..., description="New game start time (ISO 8601 UTC)")
    player_carryover: CarryoverOption = Field(
        default=CarryoverOption.NO,
        description="Whether to carry over confirmed players from the source game",
    )
    player_deadline: dt.datetime | None = Field(
        None,
        description="Confirmation deadline for players; required for YES_WITH_DEADLINE",
    )
    waitlist_carryover: CarryoverOption = Field(
        default=CarryoverOption.NO,
        description="Whether to carry over waitlisted players from the source game",
    )
    waitlist_deadline: dt.datetime | None = Field(
        None,
        description="Confirmation deadline for waitlist; required for YES_WITH_DEADLINE",
    )

    @model_validator(mode="after")
    def validate_deadlines(self) -> "CloneGameRequest":
        """Validate that YES_WITH_DEADLINE carryover options include a future deadline."""
        now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        self._check_deadline("player", self.player_carryover, self.player_deadline, now)
        self._check_deadline("waitlist", self.waitlist_carryover, self.waitlist_deadline, now)
        return self

    @staticmethod
    def _check_deadline(
        field: str,
        carryover: CarryoverOption,
        deadline: dt.datetime | None,
        now: dt.datetime,
    ) -> None:
        if carryover != CarryoverOption.YES_WITH_DEADLINE:
            return
        if deadline is None:
            msg = f"{field}_deadline is required when {field}_carryover is YES_WITH_DEADLINE"
            raise ValueError(msg)
        deadline_naive = (
            deadline.astimezone(dt.UTC).replace(tzinfo=None) if deadline.tzinfo else deadline
        )
        if deadline_naive <= now:
            msg = f"{field}_deadline must be in the future"
            raise ValueError(msg)
