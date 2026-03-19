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


"""Unit tests for MessageRefreshListener."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.message_refresh_listener import MessageRefreshListener

_CHANNEL_ID = "111222333444555666"
_DB_URL = "postgresql+asyncpg://user:pass@localhost:5432/game_scheduler"


@pytest.fixture
def spawn_cb() -> MagicMock:
    """Returns a mock that records calls and returns a distinct MagicMock Task each time."""
    mock = MagicMock()
    # Return a fresh mock that pretends to be a running asyncio.Task (not done)
    mock.side_effect = lambda cid: _make_mock_task(done=False)
    return mock


def _make_mock_task(*, done: bool) -> MagicMock:
    task = MagicMock(spec=asyncio.Task)
    task.done.return_value = done
    return task


@pytest.fixture
def listener(spawn_cb: MagicMock) -> MessageRefreshListener:
    return MessageRefreshListener(_DB_URL, spawn_cb)


class TestMessageRefreshListenerStart:
    """Verify start() establishes the asyncpg LISTEN connection."""

    @pytest.mark.asyncio
    async def test_start_opens_asyncpg_connection(self, listener: MessageRefreshListener) -> None:
        """start() calls asyncpg.connect with the provided database URL."""
        mock_conn = AsyncMock()
        mock_conn.add_listener = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "services.bot.message_refresh_listener.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ) as mock_connect:
            task = asyncio.create_task(listener.start())
            # Give the coroutine a chance to call connect before we cancel
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_connect.assert_awaited_once()
            call_url = mock_connect.call_args[0][0]
            # SQLAlchemy driver prefix is stripped; plain postgresql:// URL is used
            assert "postgresql+asyncpg" not in call_url
            assert call_url.startswith("postgresql://")

    @pytest.mark.asyncio
    async def test_start_registers_listener(self, listener: MessageRefreshListener) -> None:
        """start() calls add_listener with the correct channel name and callback."""
        mock_conn = AsyncMock()
        mock_conn.add_listener = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "services.bot.message_refresh_listener.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            task = asyncio.create_task(listener.start())
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_conn.add_listener.assert_awaited_once_with(
                "message_refresh_queue_changed",
                listener._on_notify,
            )


class TestMessageRefreshListenerOnNotify:
    """Verify _on_notify dispatches workers correctly."""

    def test_new_channel_spawns_worker(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """_on_notify with a new channel_id invokes spawn_worker_cb once."""
        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)

        spawn_cb.assert_called_once_with(_CHANNEL_ID)

    def test_repeated_notify_does_not_spawn_again(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """A second _on_notify for the same running channel does NOT call spawn_worker_cb."""
        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)
        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)

        spawn_cb.assert_called_once_with(_CHANNEL_ID)

    def test_worker_task_stored_in_channel_workers(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """After _on_notify, the new task is stored in _channel_workers."""
        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)

        assert _CHANNEL_ID in listener._channel_workers
        # The stored value is the asyncio.Task returned by spawn_worker_cb
        assert listener._channel_workers[_CHANNEL_ID] is not None


class TestMessageRefreshListenerStartEdgeCases:
    """Edge cases for start() failure handling."""

    @pytest.mark.asyncio
    async def test_start_logs_and_returns_on_connection_error(
        self, listener: MessageRefreshListener
    ) -> None:
        """start() logs the error and returns cleanly when asyncpg.connect raises."""
        with (
            patch(
                "services.bot.message_refresh_listener.asyncpg.connect",
                new_callable=AsyncMock,
                side_effect=OSError("connection refused"),
            ),
            patch("services.bot.message_refresh_listener.logger") as mock_logger,
        ):
            await listener.start()

        mock_logger.exception.assert_called_once()


class TestMessageRefreshListenerOnNotifyEdgeCases:
    """Edge cases for _on_notify payload handling and worker lifecycle."""

    def test_empty_payload_is_ignored(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """_on_notify with an empty payload does nothing and does not raise."""
        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", "")

        spawn_cb.assert_not_called()

    def test_completed_worker_is_removed_and_new_one_spawned(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """When the previous worker task is done, _on_notify spawns a fresh one."""
        done_task = _make_mock_task(done=True)
        listener._channel_workers[_CHANNEL_ID] = done_task

        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)

        spawn_cb.assert_called_once_with(_CHANNEL_ID)
        assert _CHANNEL_ID in listener._channel_workers
        assert listener._channel_workers[_CHANNEL_ID] is not done_task

    def test_channel_workers_dict_does_not_grow_unbounded(
        self, listener: MessageRefreshListener, spawn_cb: MagicMock
    ) -> None:
        """Completed tasks are pruned from _channel_workers on each notify."""
        other_id = "999888777666555444"

        # Seed a completed worker for another channel
        listener._channel_workers[other_id] = _make_mock_task(done=True)

        listener._on_notify(MagicMock(), 1, "message_refresh_queue_changed", _CHANNEL_ID)

        # The completed entry for other_id is gone
        assert other_id not in listener._channel_workers
        # The new worker for _CHANNEL_ID is present
        assert _CHANNEL_ID in listener._channel_workers
