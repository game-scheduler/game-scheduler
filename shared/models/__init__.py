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


"""SQLAlchemy models for game scheduling system."""

from .base import Base
from .channel import ChannelConfiguration
from .game import GameSession, GameStatus
from .guild import GuildConfiguration
from .participant import GameParticipant, ParticipantStatus
from .user import User

__all__ = [
    "Base",
    "User",
    "GuildConfiguration",
    "ChannelConfiguration",
    "GameSession",
    "GameStatus",
    "GameParticipant",
    "ParticipantStatus",
]
