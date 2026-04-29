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


"""Unit tests for GameSchedulerBot._member_event_worker and related on_ready changes."""

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from services.bot.bot import GameSchedulerBot


def _make_bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    instance = GameSchedulerBot.__new__(GameSchedulerBot)
    instance.config = cfg
    instance.button_handler = None
    instance.event_handlers = None
    instance.event_publisher = None
    instance.api_cache = None
    instance._sweep_task = None
    instance._refresh_listener_started = True
    return instance


class TestMemberEventWorkerCoalescing:
    """Worker coalesces N event.set() calls into a single repopulate_all call."""

    async def test_burst_of_n_events_produces_single_rebuild(self) -> None:
        """N event.set() calls before worker wakes yield exactly one repopulate_all."""
        bot = _make_bot()
        bot._member_event = asyncio.Event()

        for _ in range(5):
            bot._member_event.set()

        with (
            patch(
                "services.bot.bot.guild_projection.repopulate_all",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ) as mock_repopulate,
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await bot._member_event_worker()

        mock_repopulate.assert_awaited_once()


class TestMemberEventWorkerDebounce:
    """Worker sleeps 60 seconds before clearing, forming the debounce window."""

    async def test_worker_sleeps_60_seconds_before_repopulation(self) -> None:
        """Worker calls asyncio.sleep(60) between wait() and repopulate_all."""
        bot = _make_bot()
        bot._member_event = asyncio.Event()
        bot._member_event.set()

        with (
            patch(
                "services.bot.bot.guild_projection.repopulate_all",
                new_callable=AsyncMock,
            ),
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch(
                "asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError
            ) as mock_sleep,
        ):
            await bot._member_event_worker()

        mock_sleep.assert_awaited_once_with(60)

    async def test_event_set_during_debounce_window_does_not_trigger_extra_rebuild(self) -> None:
        """Events arriving during the 60s sleep are absorbed by clear() and do not cause
        a second repopulate_all — the paired-gateway-event case."""
        bot = _make_bot()
        bot._member_event = asyncio.Event()
        bot._member_event.set()

        async def sleep_and_set(seconds: int) -> None:
            bot._member_event.set()  # simulate second event of a Discord-paired dispatch

        with (
            patch(
                "services.bot.bot.guild_projection.repopulate_all",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ) as mock_repopulate,
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("asyncio.sleep", side_effect=sleep_and_set),
        ):
            await bot._member_event_worker()

        mock_repopulate.assert_awaited_once()
        assert not bot._member_event.is_set()


class TestOnReadyUnaffected:
    """on_ready still runs repopulate_all immediately and emits the counter itself."""

    async def test_on_ready_emits_started_counter_before_repopulate(self) -> None:
        """on_ready emits started{reason="on_ready"} and calls repopulate_all without reason=."""
        bot = _make_bot()
        mock_redis = AsyncMock()
        mock_redis.set_json = AsyncMock(return_value=True)
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.delete = AsyncMock()
        mock_redis._client = mock_client

        guild = MagicMock()
        guild.id = 111
        guild.name = "Test Guild"
        guild.owner_id = 9999
        mock_user = MagicMock()
        mock_user.id = 999

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(type(bot), "guilds", new_callable=PropertyMock, return_value=[guild])
            )
            stack.enter_context(
                patch.object(type(bot), "user", new_callable=PropertyMock, return_value=mock_user)
            )
            stack.enter_context(
                patch(
                    "services.bot.bot.get_redis_client",
                    new_callable=AsyncMock,
                    return_value=mock_redis,
                )
            )
            stack.enter_context(
                patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock)
            )
            stack.enter_context(patch.object(bot, "_trigger_sweep", new_callable=AsyncMock))
            stack.enter_context(patch.object(bot, "_sweep_orphaned_embeds", new_callable=AsyncMock))
            stack.enter_context(
                patch.object(bot, "_rebuild_redis_from_gateway", new_callable=AsyncMock)
            )
            stack.enter_context(patch("services.bot.bot.tracer"))
            stack.enter_context(patch("services.bot.bot.os.getenv", return_value=None))
            stack.enter_context(
                patch(
                    "services.bot.bot.sync_guilds_from_gateway",
                    new_callable=AsyncMock,
                    return_value={"new_guilds": 0, "new_channels": 0},
                )
            )
            stack.enter_context(
                patch(
                    "services.bot.bot.get_db_session",
                    return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=AsyncMock()),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                )
            )
            mock_repopulate = stack.enter_context(
                patch(
                    "services.bot.bot.guild_projection.repopulate_all",
                    new_callable=AsyncMock,
                )
            )
            mock_started_counter = stack.enter_context(
                patch("services.bot.bot.guild_projection.repopulation_started_counter")
            )
            stack.enter_context(patch("services.bot.bot.Path"))

            await bot.on_ready()

        mock_started_counter.add.assert_called_once_with(1, {"reason": "on_ready"})
        mock_repopulate.assert_awaited_once_with(bot=bot, redis=mock_redis)


class TestMemberEventHandlers:
    """on_member_* handlers emit the started counter and signal the coalescing event."""

    def _make_bot_with_event(self) -> GameSchedulerBot:
        bot = _make_bot()
        bot._member_event = asyncio.Event()
        return bot

    async def test_on_member_add_emits_counter_and_sets_event(self) -> None:
        """on_member_add emits started{reason="member_add"} and sets the member event."""
        bot = self._make_bot_with_event()
        member = MagicMock()

        with patch(
            "services.bot.bot.guild_projection.repopulation_started_counter"
        ) as mock_counter:
            await bot.on_member_add(member)

        mock_counter.add.assert_called_once_with(1, {"reason": "member_add"})
        assert bot._member_event.is_set()

    async def test_on_member_update_emits_counter_and_sets_event(self) -> None:
        """on_member_update emits started{reason="member_update"} and sets the member event."""
        bot = self._make_bot_with_event()
        before = MagicMock()
        after = MagicMock()

        with patch(
            "services.bot.bot.guild_projection.repopulation_started_counter"
        ) as mock_counter:
            await bot.on_member_update(before, after)

        mock_counter.add.assert_called_once_with(1, {"reason": "member_update"})
        assert bot._member_event.is_set()

    async def test_on_member_remove_emits_counter_and_sets_event(self) -> None:
        """on_member_remove emits started{reason="member_remove"} and sets the member event."""
        bot = self._make_bot_with_event()
        member = MagicMock()

        with patch(
            "services.bot.bot.guild_projection.repopulation_started_counter"
        ) as mock_counter:
            await bot.on_member_remove(member)

        mock_counter.add.assert_called_once_with(1, {"reason": "member_remove"})
        assert bot._member_event.is_set()


class TestSignalRepopulation:
    """_signal_repopulation centralises counter, log, and event-set logic."""

    def _make_bot_with_event(self) -> GameSchedulerBot:
        bot = _make_bot()
        bot._member_event = asyncio.Event()
        return bot

    def test_when_event_not_set_emits_started_counter_and_sets_event(self) -> None:
        """First trigger increments started counter and sets the event."""
        bot = self._make_bot_with_event()

        with (
            patch("services.bot.bot.guild_projection.repopulation_started_counter") as mock_started,
            patch(
                "services.bot.bot.guild_projection.repopulation_coalesced_counter"
            ) as mock_coalesced,
        ):
            bot._signal_repopulation("member_add")

        mock_started.add.assert_called_once_with(1, {"reason": "member_add"})
        mock_coalesced.add.assert_not_called()
        assert bot._member_event.is_set()

    def test_when_event_already_set_emits_both_counters(self) -> None:
        """Subsequent trigger increments both started and coalesced counters."""
        bot = self._make_bot_with_event()
        bot._member_event.set()

        with (
            patch("services.bot.bot.guild_projection.repopulation_started_counter") as mock_started,
            patch(
                "services.bot.bot.guild_projection.repopulation_coalesced_counter"
            ) as mock_coalesced,
        ):
            bot._signal_repopulation("member_update")

        mock_started.add.assert_called_once_with(1, {"reason": "member_update"})
        mock_coalesced.add.assert_called_once_with(1, {"reason": "member_update"})
        assert bot._member_event.is_set()
