# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


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
        mock_session.execute.assert_called_once()

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
