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


"""Unit tests for OTel metric increments in _sweep_deleted_embeds and _run_sweep_worker."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
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
        instance.event_publisher = AsyncMock()
        instance.api_cache = None
        instance._sweep_task = None
    return instance


def _db_ctx_empty_games():
    """Return an async context manager whose DB execute yields an empty games list."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _db_ctx_one_game():
    """Return an async context manager whose DB execute yields one game."""
    mock_game = MagicMock()
    mock_game.scheduled_at = datetime(2025, 1, 1)
    mock_game.id = "game-uuid-1"
    mock_game.channel.channel_id = "111222333"
    mock_game.message_id = "444555666"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_game]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


async def test_sweep_deleted_embeds_increments_started_counter(bot: GameSchedulerBot) -> None:
    """sweep_started_counter.add(1) is called once when _sweep_deleted_embeds is entered."""
    mock_started = MagicMock()

    with (
        patch("services.bot.bot.get_bypass_db_session", return_value=_db_ctx_empty_games()),
        patch("services.bot.bot.sweep_started_counter", mock_started),
    ):
        await bot._sweep_deleted_embeds()

    mock_started.add.assert_called_once_with(1)


async def test_sweep_interrupted_counter_incremented_when_sweep_cancelled(
    bot: GameSchedulerBot,
) -> None:
    """sweep_interrupted_counter.add(1) is called when an active sweep is cancelled.

    This metric was implemented as part of Phase 2 out-of-plan work; no xfail needed.
    """
    old_task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(999))
    bot._sweep_task = old_task

    mock_counter = MagicMock()
    sweep_mock = AsyncMock()
    with (
        patch.object(bot, "_sweep_deleted_embeds", sweep_mock),
        patch("services.bot.bot.sweep_interrupted_counter", mock_counter),
    ):
        await bot._trigger_sweep()

    mock_counter.add.assert_called_once_with(1)


async def test_sweep_deleted_embeds_records_duration_histogram(bot: GameSchedulerBot) -> None:
    """sweep_duration_histogram.record(elapsed) is called with a positive float when sweep
    completes."""
    mock_histogram = MagicMock()

    with (
        patch("services.bot.bot.get_bypass_db_session", return_value=_db_ctx_one_game()),
        patch("services.bot.bot.get_redis_client", AsyncMock(return_value=MagicMock())),
        patch.object(bot, "_run_sweep_worker", new=AsyncMock()),
        patch("services.bot.bot.sweep_duration_histogram", mock_histogram),
        patch("services.bot.bot.sweep_started_counter"),
    ):
        await bot._sweep_deleted_embeds()

    mock_histogram.record.assert_called_once()
    elapsed = mock_histogram.record.call_args[0][0]
    assert elapsed >= 0.0


async def test_run_sweep_worker_increments_messages_checked_counter(
    bot: GameSchedulerBot,
) -> None:
    """sweep_messages_checked_counter.add(1) is called once per successfully fetched message."""
    queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    await queue.put((datetime(2025, 1, 1), "game-1", "123", "456"))

    mock_redis = AsyncMock()
    mock_redis.claim_global_and_channel_slot.return_value = 0

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.fetch_message = AsyncMock(return_value=MagicMock())

    mock_publisher = AsyncMock()
    mock_checked = MagicMock()

    with (
        patch.object(bot, "get_channel", return_value=mock_channel),
        patch("services.bot.bot.sweep_messages_checked_counter", mock_checked),
    ):
        await bot._run_sweep_worker(queue, mock_redis, mock_publisher)

    mock_checked.add.assert_called_once_with(1)


async def test_run_sweep_worker_increments_deletions_detected_counter(
    bot: GameSchedulerBot,
) -> None:
    """sweep_deletions_detected_counter.add(1) is called when a message returns 404."""
    queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    await queue.put((datetime(2025, 1, 1), "game-2", "123", "789"))

    mock_redis = AsyncMock()
    mock_redis.claim_global_and_channel_slot.return_value = 0

    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.reason = "Not Found"
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.fetch_message = AsyncMock(
        side_effect=discord.NotFound(mock_response, "Unknown Message")
    )

    mock_publisher = AsyncMock()
    mock_deletions = MagicMock()

    with (
        patch.object(bot, "get_channel", return_value=mock_channel),
        patch("services.bot.bot.sweep_deletions_detected_counter", mock_deletions),
    ):
        await bot._run_sweep_worker(queue, mock_redis, mock_publisher)

    mock_deletions.add.assert_called_once_with(1)
