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


"""Unit tests for EventHandlers._edit_with_backoff."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest


class TestEditWithBackoff:
    @pytest.mark.asyncio
    async def test_returns_t_cut_on_success(self, event_handlers):
        """Returns a datetime when _try_edit_game_message succeeds."""
        with patch.object(
            event_handlers, "_try_edit_game_message", new=AsyncMock(return_value=True)
        ):
            result = await event_handlers._edit_with_backoff("chan1", "game1", 0)

        assert result is not None
        assert isinstance(result, datetime)

    @pytest.mark.asyncio
    async def test_returns_none_when_try_edit_returns_false(self, event_handlers):
        """Returns None when _try_edit_game_message returns False (e.g. 404)."""
        with patch.object(
            event_handlers, "_try_edit_game_message", new=AsyncMock(return_value=False)
        ):
            result = await event_handlers._edit_with_backoff("chan1", "game1", 0)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_non_429_http_exception(self, event_handlers):
        """Returns None on non-retryable HTTP errors (e.g. 403, 500)."""
        resp = MagicMock()
        resp.status = 500
        resp.reason = "Internal Server Error"
        exc = discord.HTTPException(resp, "error")

        with patch.object(
            event_handlers,
            "_try_edit_game_message",
            new=AsyncMock(side_effect=exc),
        ):
            result = await event_handlers._edit_with_backoff("chan1", "game1", 0)

        assert result is None

    @pytest.mark.asyncio
    async def test_retries_on_429(self, event_handlers):
        """Retries after the retry_after delay on 429, then succeeds."""
        resp = MagicMock()
        resp.status = 429
        resp.reason = "Too Many Requests"
        rate_limit_exc = discord.HTTPException(resp, "rate limited")
        rate_limit_exc.retry_after = 0.01

        call_count = 0

        async def side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_exc
            return True

        with patch.object(event_handlers, "_try_edit_game_message", side_effect=side_effect):
            result = await event_handlers._edit_with_backoff("chan1", "game1", 0)

        assert result is not None
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_on_unexpected_exception(self, event_handlers):
        """Returns None on an unexpected non-Discord exception."""
        with patch.object(
            event_handlers,
            "_try_edit_game_message",
            new=AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            result = await event_handlers._edit_with_backoff("chan1", "game1", 0)

        assert result is None
