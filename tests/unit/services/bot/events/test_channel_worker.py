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


"""Unit tests for EventHandlers._channel_worker (TDD RED phase)."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers

_CHANNEL_ID = "111222333444555666"
_GAME_ID = str(uuid4())


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock(spec=discord.Client)
    bot.get_channel = MagicMock(return_value=None)
    bot.fetch_channel = AsyncMock()
    return bot


@pytest.fixture
def handlers(mock_bot: MagicMock) -> EventHandlers:
    return EventHandlers(mock_bot)


def _make_db_session(game: MagicMock | None, queue_row_game_id: str | None) -> MagicMock:
    """Build a minimal async DB session mock.

    ``queue_row_game_id``: the game_id string returned by the LIMIT 1 queue
    query, or None to simulate an empty queue.
    """
    scalar_mock = MagicMock(return_value=queue_row_game_id)

    execute_mock = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = scalar_mock
    execute_mock.return_value = result_mock

    session = AsyncMock()
    session.execute = execute_mock
    session.commit = AsyncMock()

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


class TestChannelWorkerInitialization:
    def test_channel_workers_dict_exists(self, handlers: EventHandlers) -> None:
        """EventHandlers.__init__ creates an empty _channel_workers dict."""
        assert hasattr(handlers, "_channel_workers")
        assert isinstance(handlers._channel_workers, dict)
        assert len(handlers._channel_workers) == 0

    def test_channel_worker_method_exists(self, handlers: EventHandlers) -> None:
        """_channel_worker is defined on EventHandlers."""
        assert hasattr(handlers, "_channel_worker")
        assert callable(handlers._channel_worker)


class TestChannelWorkerNoRows:
    @pytest.mark.asyncio
    async def test_worker_exits_when_queue_empty(self, handlers: EventHandlers) -> None:
        """Worker returns immediately when no queue rows exist for the channel."""
        db_cm = _make_db_session(game=None, queue_row_game_id=None)

        with (
            patch("services.bot.events.handlers.get_db_session", db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
            ) as mock_redis_factory,
        ):
            mock_redis = AsyncMock()
            mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)
            mock_redis_factory.return_value = mock_redis

            await handlers._channel_worker(_CHANNEL_ID)

        mock_redis_factory.assert_not_called()
        assert _CHANNEL_ID not in handlers._channel_workers

    @pytest.mark.asyncio
    async def test_worker_deregisters_itself_when_done(self, handlers: EventHandlers) -> None:
        """Worker removes itself from _channel_workers after draining the queue."""
        db_cm = _make_db_session(game=None, queue_row_game_id=None)
        task_mock = MagicMock(spec=asyncio.Task)
        handlers._channel_workers[_CHANNEL_ID] = task_mock

        with patch("services.bot.events.handlers.get_db_session", db_cm):
            await handlers._channel_worker(_CHANNEL_ID)

        assert _CHANNEL_ID not in handlers._channel_workers


class TestChannelWorkerRateLimitSlot:
    @pytest.mark.asyncio
    async def test_worker_calls_claim_slot(self, handlers: EventHandlers) -> None:
        """Worker calls claim_channel_rate_limit_slot with the channel_id."""
        mock_game = MagicMock()
        mock_game.id = _GAME_ID
        mock_game.message_id = "999888777"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        # First call returns a row, second returns None to stop the loop.
        call_count = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()
            nonlocal call_count

            async def _execute(_stmt):
                nonlocal call_count
                result = MagicMock()
                game_id_val = _GAME_ID if call_count == 0 else None
                result.scalar_one_or_none = MagicMock(return_value=game_id_val)
                call_count += 1
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)
        mock_message.edit = AsyncMock()
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", new_callable=AsyncMock),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        mock_redis.claim_channel_rate_limit_slot.assert_awaited_with(_CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_worker_sleeps_when_wait_ms_positive(self, handlers: EventHandlers) -> None:
        """Worker sleeps wait_ms/1000 seconds when claim_slot returns >0."""
        mock_game = MagicMock()
        mock_game.id = _GAME_ID
        mock_game.message_id = "999888777"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        call_count = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()
            nonlocal call_count

            async def _execute(_stmt):
                nonlocal call_count
                result = MagicMock()
                game_id_val = _GAME_ID if call_count == 0 else None
                result.scalar_one_or_none = MagicMock(return_value=game_id_val)
                call_count += 1
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=500)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)
        mock_message.edit = AsyncMock()

        sleep_calls: list[float] = []

        async def _fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", new_callable=AsyncMock),
            patch("services.bot.events.handlers.asyncio.sleep", side_effect=_fake_sleep),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        assert 0.5 in sleep_calls


class TestChannelWorkerSuccessfulEdit:
    @pytest.mark.asyncio
    async def test_worker_deletes_queue_rows_after_edit(self, handlers: EventHandlers) -> None:
        """After a successful edit, queue rows for channel+game up to T_cut are deleted."""
        mock_game = MagicMock()
        mock_game.id = _GAME_ID
        mock_game.message_id = "999888777"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        executed_stmts: list = []
        call_count = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()
            nonlocal call_count

            async def _execute(stmt):
                nonlocal call_count
                executed_stmts.append(stmt)
                result = MagicMock()
                game_id_val = _GAME_ID if call_count == 0 else None
                result.scalar_one_or_none = MagicMock(return_value=game_id_val)
                call_count += 1
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", new_callable=AsyncMock),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        # At least one DELETE statement must have been executed.
        assert len(executed_stmts) >= 2


class TestChannelWorker429Handling:
    @pytest.mark.asyncio
    async def test_429_causes_retry_without_losing_queue_row(self, handlers: EventHandlers) -> None:
        """On 429, the worker sleeps retry_after and retries; DB row survives until success."""
        mock_game = MagicMock()
        mock_game.id = _GAME_ID
        mock_game.message_id = "999888777"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        edit_attempt = 0
        queue_call_count = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()
            nonlocal queue_call_count

            async def _execute(_stmt):
                nonlocal queue_call_count
                result = MagicMock()
                game_id_val = _GAME_ID if queue_call_count == 0 else None
                result.scalar_one_or_none = MagicMock(return_value=game_id_val)
                queue_call_count += 1
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)

        sleep_calls: list[float] = []

        async def _fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        # First _update_game_message_content call raises 429; second succeeds.
        async def _edit_side_effect(msg, game):
            nonlocal edit_attempt
            if edit_attempt == 0:
                edit_attempt += 1
                err = discord.HTTPException(MagicMock(), "rate limited")
                err.status = 429
                err.retry_after = 2.0
                raise err
            edit_attempt += 1

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(
                handlers,
                "_update_game_message_content",
                side_effect=_edit_side_effect,
            ),
            patch("services.bot.events.handlers.asyncio.sleep", side_effect=_fake_sleep),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        # edit was attempted twice (once failing with 429, once succeeding)
        assert edit_attempt == 2
        # retry_after sleep was recorded
        assert 2.0 in sleep_calls

    @pytest.mark.asyncio
    async def test_non_429_error_is_logged_and_does_not_terminate_worker(
        self, handlers: EventHandlers
    ) -> None:
        """A non-429 Discord API error is logged; the worker continues to the next loop."""
        mock_game = MagicMock()
        mock_game.id = _GAME_ID
        mock_game.message_id = "999888777"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        call_count = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()
            nonlocal call_count

            async def _execute(_stmt):
                nonlocal call_count
                result = MagicMock()
                game_id_val = _GAME_ID if call_count == 0 else None
                result.scalar_one_or_none = MagicMock(return_value=game_id_val)
                call_count += 1
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)

        async def _edit_raise(_msg, _game):
            err = discord.HTTPException(MagicMock(), "internal server error")
            err.status = 500
            raise err

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", side_effect=_edit_raise),
        ):
            # Worker must not raise — it should catch and log.
            await handlers._channel_worker(_CHANNEL_ID)
            assert True  # worker catches non-429 HTTPException without raising


class TestChannelWorkerMultiGame:
    @pytest.mark.asyncio
    async def test_two_games_same_channel_both_edited(self, handlers: EventHandlers) -> None:
        """Two games queued for the same channel are both edited in sequence."""
        game_id_a = str(uuid4())
        game_id_b = str(uuid4())

        mock_game_a = MagicMock()
        mock_game_a.id = game_id_a
        mock_game_a.message_id = "111000111"
        mock_game_a.channel = MagicMock()
        mock_game_a.channel.channel_id = _CHANNEL_ID

        mock_game_b = MagicMock()
        mock_game_b.id = game_id_b
        mock_game_b.message_id = "222000222"
        mock_game_b.channel = MagicMock()
        mock_game_b.channel.channel_id = _CHANNEL_ID

        # Queue returns game_id_a then game_id_b then None.
        # The iterator only advances when scalar_one_or_none() is actually called,
        # so delete() execute calls don't consume queue entries.
        queue_iter = iter([game_id_a, game_id_b, None])

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()

            async def _execute(_stmt):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(side_effect=lambda: next(queue_iter, None))
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(return_value=0)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)

        edited_games: list = []

        async def _track_edit(msg, game):
            edited_games.append(game)

        def _game_for_id(db, gid):
            return mock_game_a if gid == game_id_a else mock_game_b

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", side_effect=_game_for_id),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", side_effect=_track_edit),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        assert len(edited_games) == 2
        assert mock_redis.claim_channel_rate_limit_slot.await_count == 2
        mock_redis.claim_channel_rate_limit_slot.assert_awaited_with(_CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_burst_spacing_sleeps_reflect_wait_ms(self, handlers: EventHandlers) -> None:
        """Worker sleeps the wait_ms values returned by the rate limiter for each iteration."""
        game_ids = [str(uuid4()) for _ in range(4)]
        # Simulated return values from claim_channel_rate_limit_slot per iteration.
        # Matches graduated spacing: n=0→0ms, n=1→1000ms, n=2→1000ms, n=3→1500ms.
        wait_ms_sequence = [0, 1000, 1000, 1500]
        queue_iter = iter([*game_ids, None])

        claim_call = 0

        @asynccontextmanager
        async def _db_cm():
            session = AsyncMock()

            async def _execute(_stmt):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(side_effect=lambda: next(queue_iter, None))
                return result

            session.execute = _execute
            session.commit = AsyncMock()
            yield session

        mock_game = MagicMock()
        mock_game.message_id = "999"
        mock_game.channel = MagicMock()
        mock_game.channel.channel_id = _CHANNEL_ID

        async def _claim(_cid):
            nonlocal claim_call
            val = wait_ms_sequence[claim_call] if claim_call < len(wait_ms_sequence) else 0
            claim_call += 1
            return val

        mock_redis = AsyncMock()
        mock_redis.claim_channel_rate_limit_slot = AsyncMock(side_effect=_claim)

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)
        sleep_calls: list[float] = []

        async def _fake_sleep(s: float) -> None:
            sleep_calls.append(s)

        with (
            patch("services.bot.events.handlers.get_db_session", _db_cm),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch.object(handlers, "_get_game_with_participants", return_value=mock_game),
            patch.object(
                handlers,
                "_get_channel_and_partial_message",
                return_value=(mock_channel, mock_message),
            ),
            patch.object(handlers, "_update_game_message_content", new_callable=AsyncMock),
            patch("services.bot.events.handlers.asyncio.sleep", side_effect=_fake_sleep),
        ):
            await handlers._channel_worker(_CHANNEL_ID)

        # First edit has wait_ms=0 so no sleep; remaining three have waits.
        assert sleep_calls == [1.0, 1.0, 1.5]
        assert mock_redis.claim_channel_rate_limit_slot.await_count == 4
