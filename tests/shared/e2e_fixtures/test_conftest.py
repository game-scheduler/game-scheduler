# Copyright 2025-2026 Bret McKee
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


"""Unit tests for E2E conftest polling utilities."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.conftest import wait_for_db_condition


class TestWaitForDbCondition:
    """Tests for wait_for_db_condition database polling utility."""

    @pytest.mark.asyncio
    async def test_immediate_success(self):
        """Should return immediately when predicate satisfied on first query."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_row = (123, "test_value")
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await wait_for_db_condition(
            mock_session,
            "SELECT id, value FROM table WHERE id = :id",
            {"id": 1},
            lambda row: row[0] is not None,
            timeout=5,
        )

        assert result == mock_row
        assert mock_session.execute.await_count == 1
        called_with = mock_session.execute.call_args
        assert str(called_with.args[0]) == "SELECT id, value FROM table WHERE id = :id"
        assert called_with.args[1] == {"id": 1}

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Should retry until predicate satisfied."""
        mock_session = AsyncMock(spec=AsyncSession)

        attempts = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            mock_result = Mock()
            if attempts >= 3:
                mock_result.fetchone.return_value = (123, "populated")
            else:
                mock_result.fetchone.return_value = (123, None)
            return mock_result

        mock_session.execute.side_effect = execute_side_effect

        result = await wait_for_db_condition(
            mock_session,
            "SELECT id, message_id FROM table WHERE id = :id",
            {"id": 1},
            lambda row: row[1] is not None,
            timeout=10,
            interval=0.1,
        )

        assert result[1] == "populated"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should raise AssertionError when timeout reached."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.fetchone.return_value = (123, None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(AssertionError, match="message_id population not met within 1s timeout"):
            await wait_for_db_condition(
                mock_session,
                "SELECT id, message_id FROM table WHERE id = :id",
                {"id": 1},
                lambda row: row[1] is not None,
                timeout=1,
                interval=0.1,
                description="message_id population",
            )

    @pytest.mark.asyncio
    async def test_no_row_returned(self):
        """Should handle case when query returns no rows."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(AssertionError, match="test query not met within"):
            await wait_for_db_condition(
                mock_session,
                "SELECT * FROM table WHERE id = :id",
                {"id": 999},
                lambda row: True,
                timeout=1,
                interval=0.1,
                description="test query",
            )

    @pytest.mark.asyncio
    async def test_query_with_parameters(self):
        """Should pass query parameters correctly."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.fetchone.return_value = (42, "test")
        mock_session.execute.return_value = mock_result

        await wait_for_db_condition(
            mock_session,
            "SELECT id, name FROM users WHERE id = :user_id AND guild_id = :guild_id",
            {"user_id": 100, "guild_id": 200},
            lambda row: row[0] == 42,
            timeout=5,
        )

        call_args = mock_session.execute.call_args
        assert isinstance(call_args[0][0], type(text("")))
        assert call_args[0][1] == {"user_id": 100, "guild_id": 200}

    @pytest.mark.asyncio
    async def test_custom_interval(self):
        """Should respect custom polling interval."""
        mock_session = AsyncMock(spec=AsyncSession)

        attempts = 0
        start_time = asyncio.get_event_loop().time()

        async def execute_side_effect(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            mock_result = Mock()
            if attempts >= 3:
                mock_result.fetchone.return_value = (1, "done")
            else:
                mock_result.fetchone.return_value = (1, None)
            return mock_result

        mock_session.execute.side_effect = execute_side_effect

        result = await wait_for_db_condition(
            mock_session,
            "SELECT id, status FROM table WHERE id = :id",
            {"id": 1},
            lambda row: row[1] is not None,
            timeout=10,
            interval=0.2,
        )

        elapsed = asyncio.get_event_loop().time() - start_time

        assert result[1] == "done"
        assert elapsed >= 0.4

    @pytest.mark.asyncio
    async def test_predicate_evaluation(self):
        """Should correctly evaluate complex predicates."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.fetchone.return_value = (1, "active", 5)
        mock_session.execute.return_value = mock_result

        result = await wait_for_db_condition(
            mock_session,
            "SELECT id, status, count FROM table WHERE id = :id",
            {"id": 1},
            lambda row: row[1] == "active" and row[2] > 3,
            timeout=5,
        )

        assert result == (1, "active", 5)
