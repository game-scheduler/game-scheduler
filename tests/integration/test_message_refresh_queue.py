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


"""Integration tests for message_refresh_queue table, trigger, and listener.

Covers:
- Trigger fires pg_notify with the correct channel_id on upsert (Task 6.1 / Task 7.5)
- MessageRefreshListener receives channel_id via asyncpg LISTEN (Task 6.2)
- Startup recovery query returns all distinct pending channel_ids (Task 6.3)
"""

import asyncio

import asyncpg
import pytest
from sqlalchemy import text

from services.bot.message_refresh_listener import MessageRefreshListener
from services.scheduler.postgres_listener import PostgresNotificationListener

pytestmark = pytest.mark.integration


class TestMessageRefreshQueueTrigger:
    """Upsert on message_refresh_queue fires pg_notify with the correct channel_id."""

    def test_insert_notifies_correct_channel_id(
        self,
        admin_db_url_sync,
        admin_db_sync,
        test_game_environment,
    ):
        """Trigger sends pg_notify payload equal to the inserted channel_id."""
        listener = PostgresNotificationListener(admin_db_url_sync)
        try:
            listener.connect()
            listener.listen("message_refresh_queue_changed")

            env = test_game_environment()

            admin_db_sync.execute(
                text(
                    "INSERT INTO message_refresh_queue (game_id, channel_id) "
                    "VALUES (:game_id, :channel_id) "
                    "ON CONFLICT (channel_id, game_id) DO UPDATE SET enqueued_at = NOW()"
                ),
                {
                    "game_id": env["game"]["id"],
                    "channel_id": env["channel"]["channel_id"],
                },
            )
            admin_db_sync.commit()

            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            # PostgresNotificationListener wraps non-JSON payloads in {"raw": ...}
            # because the message_refresh_queue trigger sends a plain string, not JSON.
            assert isinstance(payload, dict)
            assert payload.get("raw") == env["channel"]["channel_id"]
        finally:
            listener.close()


class TestMessageRefreshListenerIntegration:
    """MessageRefreshListener receives the correct channel_id via asyncpg LISTEN."""

    async def test_listener_receives_channel_id(
        self,
        bot_db_url,
        admin_db_url,
        admin_db_sync,
        test_game_environment,
    ):
        """Listener spawn_cb fires with correct channel_id after INSERT."""
        env = test_game_environment()

        received_payloads: list[str] = []
        received_event = asyncio.Event()

        def spawn_cb(channel_id: str) -> asyncio.Task:
            received_payloads.append(channel_id)
            received_event.set()
            return asyncio.create_task(asyncio.sleep(0))

        listener = MessageRefreshListener(bot_db_url, spawn_cb)
        task = asyncio.create_task(listener.start())

        # Allow asyncpg LISTEN connection to establish before inserting.
        await asyncio.sleep(0.3)

        raw_url = admin_db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(raw_url)
        try:
            await conn.execute(
                "INSERT INTO message_refresh_queue (game_id, channel_id) VALUES ($1, $2)"
                " ON CONFLICT (channel_id, game_id) DO UPDATE SET enqueued_at = NOW()",
                env["game"]["id"],
                env["channel"]["channel_id"],
            )
        finally:
            await conn.close()

        await asyncio.wait_for(received_event.wait(), timeout=2.0)

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        assert received_payloads == [env["channel"]["channel_id"]]


class TestMessageRefreshQueueRecovery:
    """Startup recovery query returns all distinct pending channel_ids."""

    def test_recovery_query_returns_pending_channels(
        self,
        admin_db_sync,
        test_game_environment,
    ):
        """SELECT DISTINCT channel_id returns both pending channels after INSERT."""
        admin_db_sync.execute(text("DELETE FROM message_refresh_queue"))
        admin_db_sync.commit()

        env = test_game_environment()
        channel_id_1 = "111111111111111111"
        channel_id_2 = "222222222222222222"

        for channel_id in (channel_id_1, channel_id_2):
            admin_db_sync.execute(
                text(
                    "INSERT INTO message_refresh_queue (game_id, channel_id) "
                    "VALUES (:game_id, :channel_id) "
                    "ON CONFLICT (channel_id, game_id) DO UPDATE SET enqueued_at = NOW()"
                ),
                {"game_id": env["game"]["id"], "channel_id": channel_id},
            )
        admin_db_sync.commit()

        result = admin_db_sync.execute(
            text("SELECT DISTINCT channel_id FROM message_refresh_queue")
        )
        returned_channel_ids = {row[0] for row in result.fetchall()}

        assert channel_id_1 in returned_channel_ids
        assert channel_id_2 in returned_channel_ids
