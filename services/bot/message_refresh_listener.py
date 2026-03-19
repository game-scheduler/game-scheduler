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


"""asyncpg LISTEN-based listener that wakes per-channel workers on NOTIFY."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class MessageRefreshListener:
    """
    Holds a dedicated asyncpg connection that listens for
    ``message_refresh_queue_changed`` notifications from Postgres.

    When a NOTIFY arrives, it invokes ``spawn_worker_cb(discord_channel_id)``
    at most once per channel; subsequent NOTIFYs for the same channel are
    ignored while the worker is still running.

    Args:
        bot_db_url: PostgreSQL connection URL (``postgresql+asyncpg://…`` or
            ``postgresql://…`` are both accepted).
        spawn_worker_cb: Callable that accepts a ``discord_channel_id`` string
            and returns an :class:`asyncio.Task`.
    """

    def __init__(
        self,
        bot_db_url: str,
        spawn_worker_cb: Callable[[str], asyncio.Task[Any]],
    ) -> None:
        self._bot_db_url = bot_db_url
        self._spawn_worker_cb = spawn_worker_cb
        self._channel_workers: dict[str, asyncio.Task[Any]] = {}

    async def start(self) -> None:
        """Open the asyncpg LISTEN connection and block until cancelled.

        Strips the SQLAlchemy ``+asyncpg`` driver prefix so asyncpg receives
        a plain ``postgresql://`` URL it can handle directly.
        """
        db_url = self._bot_db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn: asyncpg.Connection | None = None
        try:
            conn = await asyncpg.connect(db_url)
            await conn.add_listener("message_refresh_queue_changed", self._on_notify)
            # Block here; asyncio delivers NOTIFYs via the event loop while we wait.
            await asyncio.get_event_loop().create_future()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("MessageRefreshListener failed to start")
        finally:
            if conn is not None:
                await conn.close()

    def _on_notify(
        self,
        _conn: asyncpg.Connection,
        _pid: int,
        _channel: str,
        payload: str,
    ) -> None:
        """Handle a single ``pg_notify`` delivery from Postgres.

        Spawns a worker task for ``payload`` (the discord_channel_id) if one
        is not already running. Cleans up completed tasks before checking so
        the dict stays bounded.
        """
        if not payload:
            return

        discord_channel_id = payload

        # Remove entries for tasks that have already finished.
        self._channel_workers = {
            cid: task for cid, task in self._channel_workers.items() if not task.done()
        }

        if discord_channel_id not in self._channel_workers:
            task = self._spawn_worker_cb(discord_channel_id)
            self._channel_workers[discord_channel_id] = task
