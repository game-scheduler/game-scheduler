# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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
Guild isolation middleware using ContextVars and SQLAlchemy event listeners.

Provides transparent guild-level data filtering for multi-tenant security.
"""

from contextvars import ContextVar

_current_guild_ids: ContextVar[list[str] | None] = ContextVar("current_guild_ids", default=None)


def set_current_guild_ids(guild_ids: list[str]) -> None:
    """
    Set guild IDs for current request context.

    Args:
        guild_ids: List of Discord guild IDs (snowflakes)
    """
    _current_guild_ids.set(guild_ids)


def get_current_guild_ids() -> list[str] | None:
    """
    Get guild IDs for current request context.

    Returns:
        List of guild IDs or None if not set
    """
    return _current_guild_ids.get(None)


def clear_current_guild_ids() -> None:
    """Clear guild IDs from current request context."""
    _current_guild_ids.set(None)
