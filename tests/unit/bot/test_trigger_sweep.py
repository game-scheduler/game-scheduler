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


"""Unit tests for GameSchedulerBot._trigger_sweep cancel-and-restart behaviour."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.bot import GameSchedulerBot


@pytest.fixture
def bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    with patch("services.bot.bot.discord.Intents") as mock_intents:
        mock_intents.return_value = MagicMock()
        instance = GameSchedulerBot.__new__(GameSchedulerBot)
        instance.config = cfg
        instance.button_handler = None
        instance.event_handlers = None
        instance.event_publisher = None
        instance.api_cache = None
        instance._sweep_task = None
    return instance


async def test_trigger_sweep_no_active_task_creates_new_task(bot: GameSchedulerBot) -> None:
    """When no sweep is running, _trigger_sweep launches a new asyncio.Task."""
    sweep_mock = AsyncMock()
    with (
        patch.object(bot, "_sweep_deleted_embeds", sweep_mock),
        patch("services.bot.bot.sweep_interrupted_counter", create=True),
    ):
        await bot._trigger_sweep()

    assert bot._sweep_task is not None
    assert not bot._sweep_task.done() or sweep_mock.called


async def test_trigger_sweep_active_task_is_cancelled_and_replaced(bot: GameSchedulerBot) -> None:
    """When a sweep is already running, _trigger_sweep cancels it and starts a new one."""
    old_task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(999))
    bot._sweep_task = old_task

    sweep_mock = AsyncMock()
    with (
        patch.object(bot, "_sweep_deleted_embeds", sweep_mock),
        patch("services.bot.bot.sweep_interrupted_counter", create=True),
    ):
        await bot._trigger_sweep()

    assert old_task.cancelled()
    assert bot._sweep_task is not old_task


async def test_trigger_sweep_increments_interrupted_counter_on_cancellation(
    bot: GameSchedulerBot,
) -> None:
    """The sweep_interrupted_counter is incremented when a running sweep is cancelled."""
    old_task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(999))
    bot._sweep_task = old_task

    mock_counter = MagicMock()
    sweep_mock = AsyncMock()
    with (
        patch.object(bot, "_sweep_deleted_embeds", sweep_mock),
        patch("services.bot.bot.sweep_interrupted_counter", mock_counter, create=True),
    ):
        await bot._trigger_sweep()

    mock_counter.add.assert_called_once_with(1)


async def test_trigger_sweep_does_not_increment_counter_when_no_active_task(
    bot: GameSchedulerBot,
) -> None:
    """The sweep_interrupted_counter is NOT incremented when no sweep is running."""
    assert bot._sweep_task is None

    mock_counter = MagicMock()
    sweep_mock = AsyncMock()
    with (
        patch.object(bot, "_sweep_deleted_embeds", sweep_mock),
        patch("services.bot.bot.sweep_interrupted_counter", mock_counter, create=True),
    ):
        await bot._trigger_sweep()

    mock_counter.add.assert_not_called()
