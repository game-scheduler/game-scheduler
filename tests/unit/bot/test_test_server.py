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


"""Unit tests for GameSchedulerBot test HTTP server (_handle_sweep_request)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp.web
import pytest

from services.bot.bot import GameSchedulerBot


@pytest.fixture
def bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    with patch("services.bot.bot.discord.Intents"):
        instance = GameSchedulerBot.__new__(GameSchedulerBot)
        instance.config = cfg
        instance.button_handler = None
        instance.event_handlers = None
        instance.event_publisher = None
        instance.api_cache = None
        instance._sweep_task = None
    return instance


async def test_handle_sweep_request_triggers_sweep_and_returns_200(
    bot: GameSchedulerBot,
) -> None:
    """_handle_sweep_request calls _trigger_sweep, awaits the task, and returns HTTP 200."""
    trigger_mock = AsyncMock()

    async def _noop() -> None:
        pass

    fake_task = asyncio.create_task(_noop())

    with patch.object(bot, "_trigger_sweep", trigger_mock):
        bot._sweep_task = fake_task
        request = MagicMock(spec=aiohttp.web.Request)
        response = await bot._handle_sweep_request(request)

    trigger_mock.assert_awaited_once()
    assert isinstance(response, aiohttp.web.Response)
    assert response.status == 200
