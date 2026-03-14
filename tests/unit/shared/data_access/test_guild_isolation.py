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


"""Unit tests for guild isolation ContextVar management."""

import asyncio
from unittest.mock import MagicMock

import pytest

from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
    get_current_guild_ids,
    set_current_guild_ids,
    set_rls_context_on_transaction_begin,
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


def test_event_listener_with_guild_ids():
    """Event listener executes SQL when guild_ids are set."""
    set_current_guild_ids(["123", "456"])
    mock_connection = MagicMock()

    set_rls_context_on_transaction_begin(None, None, mock_connection)

    # Event listener now uses execute(text()) instead of exec_driver_sql()
    mock_connection.execute.assert_called_once()
    call_args = mock_connection.execute.call_args[0][0]
    assert str(call_args) == "SET LOCAL app.current_guild_ids = '123,456'"


def test_event_listener_with_none():
    """Event listener skips SQL when guild_ids is None."""
    clear_current_guild_ids()
    mock_connection = MagicMock()

    set_rls_context_on_transaction_begin(None, None, mock_connection)

    mock_connection.exec_driver_sql.assert_not_called()


def test_event_listener_with_empty_list():
    """Event listener skips SQL when guild_ids is empty list."""
    set_current_guild_ids([])
    mock_connection = MagicMock()

    set_rls_context_on_transaction_begin(None, None, mock_connection)

    mock_connection.exec_driver_sql.assert_not_called()
