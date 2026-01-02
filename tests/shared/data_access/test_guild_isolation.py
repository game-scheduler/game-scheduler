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


"""Unit tests for guild isolation ContextVar management."""

import asyncio

import pytest

from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
    get_current_guild_ids,
    set_current_guild_ids,
)


def test_set_and_get_guild_ids():
    """ContextVar stores and retrieves guild_ids."""
    guild_ids = ["123456789", "987654321"]
    set_current_guild_ids(guild_ids)

    result = get_current_guild_ids()

    assert result == guild_ids


def test_get_guild_ids_returns_none_when_not_set():
    """ContextVar returns None when not initialized."""
    clear_current_guild_ids()

    result = get_current_guild_ids()

    assert result is None


def test_clear_guild_ids():
    """ContextVar cleared properly."""
    set_current_guild_ids(["123"])
    clear_current_guild_ids()

    result = get_current_guild_ids()

    assert result is None


@pytest.mark.asyncio
async def test_contextvars_isolated_between_async_tasks():
    """ContextVars maintain isolation between concurrent async tasks."""

    async def task1():
        set_current_guild_ids(["task1_guild"])
        await asyncio.sleep(0.01)
        return get_current_guild_ids()

    async def task2():
        set_current_guild_ids(["task2_guild"])
        await asyncio.sleep(0.01)
        return get_current_guild_ids()

    result1, result2 = await asyncio.gather(task1(), task2())

    assert result1 == ["task1_guild"]
    assert result2 == ["task2_guild"]
