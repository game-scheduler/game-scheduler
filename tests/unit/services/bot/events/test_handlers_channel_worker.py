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


"""Unit tests for EventHandlers._channel_worker."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.bot.events.handlers import _MAX_EDIT_ATTEMPTS


class TestChannelWorker:
    def _make_db_ctx(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_db)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return mock_db, ctx

    @pytest.mark.asyncio
    async def test_deletes_queue_entry_on_success(self, event_handlers):
        """Queue row is deleted after a successful edit."""
        game_id = str(uuid4())
        mock_db, db_ctx = self._make_db_ctx()

        with (
            patch.object(
                event_handlers,
                "_fetch_next_queued_game",
                new=AsyncMock(side_effect=[game_id, None]),
            ),
            patch.object(
                event_handlers,
                "_edit_with_backoff",
                new=AsyncMock(return_value=datetime.now(tz=UTC)),
            ),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new=AsyncMock(
                    return_value=AsyncMock(claim_channel_rate_limit_slot=AsyncMock(return_value=0))
                ),
            ),
            patch("services.bot.events.handlers.get_db_session", return_value=db_ctx),
        ):
            await event_handlers._channel_worker("chan1")

        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_drops_queue_entry_after_max_attempts(self, event_handlers):
        """Queue row is deleted after _MAX_EDIT_ATTEMPTS failures."""
        game_id = str(uuid4())
        mock_db, db_ctx = self._make_db_ctx()

        fetch_side_effects = [game_id] * _MAX_EDIT_ATTEMPTS + [None]

        with (
            patch.object(
                event_handlers,
                "_fetch_next_queued_game",
                new=AsyncMock(side_effect=fetch_side_effects),
            ),
            patch.object(event_handlers, "_edit_with_backoff", new=AsyncMock(return_value=None)),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new=AsyncMock(
                    return_value=AsyncMock(claim_channel_rate_limit_slot=AsyncMock(return_value=0))
                ),
            ),
            patch("services.bot.events.handlers.get_db_session", return_value=db_ctx),
        ):
            await event_handlers._channel_worker("chan1")

        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_before_dropping(self, event_handlers):
        """Worker retries up to _MAX_EDIT_ATTEMPTS before dropping the entry."""
        game_id = str(uuid4())
        mock_db, db_ctx = self._make_db_ctx()

        fetch_side_effects = [game_id] * _MAX_EDIT_ATTEMPTS + [None]
        mock_fetch = AsyncMock(side_effect=fetch_side_effects)

        with (
            patch.object(event_handlers, "_fetch_next_queued_game", new=mock_fetch),
            patch.object(event_handlers, "_edit_with_backoff", new=AsyncMock(return_value=None)),
            patch(
                "services.bot.events.handlers.get_redis_client",
                new=AsyncMock(
                    return_value=AsyncMock(claim_channel_rate_limit_slot=AsyncMock(return_value=0))
                ),
            ),
            patch("services.bot.events.handlers.get_db_session", return_value=db_ctx),
        ):
            await event_handlers._channel_worker("chan1")

        assert mock_fetch.await_count == _MAX_EDIT_ATTEMPTS + 1

    @pytest.mark.asyncio
    async def test_removes_channel_from_workers_on_completion(self, event_handlers):
        """_channel_workers entry is cleaned up when the worker finishes."""
        event_handlers._channel_workers["chan1"] = MagicMock()
        mock_db, db_ctx = self._make_db_ctx()

        with (
            patch.object(
                event_handlers,
                "_fetch_next_queued_game",
                new=AsyncMock(return_value=None),
            ),
            patch("services.bot.events.handlers.get_db_session", return_value=db_ctx),
        ):
            await event_handlers._channel_worker("chan1")

        assert "chan1" not in event_handlers._channel_workers

    @pytest.mark.asyncio
    async def test_removes_channel_from_workers_on_exception(self, event_handlers):
        """_channel_workers entry is cleaned up even if the worker raises."""
        event_handlers._channel_workers["chan1"] = MagicMock()

        with patch.object(
            event_handlers,
            "_fetch_next_queued_game",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with pytest.raises(RuntimeError):
                await event_handlers._channel_worker("chan1")

        assert "chan1" not in event_handlers._channel_workers
