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


"""Signup method types for game sessions."""

from enum import Enum


class SignupMethod(str, Enum):
    """Game signup method controlling participant addition."""

    SELF_SIGNUP = "SELF_SIGNUP"
    HOST_SELECTED = "HOST_SELECTED"

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        display_map = {
            "SELF_SIGNUP": "Self Signup",
            "HOST_SELECTED": "Host Selected",
        }
        return display_map[self.value]

    @property
    def description(self) -> str:
        """Description for UI tooltip/helper text."""
        description_map = {
            "SELF_SIGNUP": "Players can join the game by clicking the Discord button",
            "HOST_SELECTED": "Only the host can add players (Discord button disabled)",
        }
        return description_map[self.value]
