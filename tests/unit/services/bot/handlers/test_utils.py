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


"""Unit tests for bot handler utilities."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.handlers.utils import (
    get_participant_count,
    send_deferred_response,
    send_error_message,
    send_success_message,
)
from shared.models.participant import GameParticipant


class TestGetParticipantCount:
    """Tests for get_participant_count function."""

    @pytest.mark.asyncio
    async def test_counts_non_placeholder_participants(self):
        """Test that function counts only participants with user IDs."""
        game_id = str(uuid4())
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock participants: 2 with users, 1 placeholder
        mock_participant1 = MagicMock(spec=GameParticipant)
        mock_participant1.user_id = user_id1

        mock_participant2 = MagicMock(spec=GameParticipant)
        mock_participant2.user_id = user_id2

        mock_result.scalars.return_value.all.return_value = [
            mock_participant1,
            mock_participant2,
        ]
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_game(self):
        """Test that function returns 0 for game with no participants."""
        game_id = str(uuid4())

        # Mock database session with empty result
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_excludes_all_placeholders(self):
        """Test that query filters out placeholder participants correctly."""
        game_id = str(uuid4())

        # Mock database session - empty result after filtering placeholders
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_counts_only_specified_game(self):
        """Test that query filters by game_id correctly."""
        game_id = str(uuid4())
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock 2 participants for the specified game
        mock_participant1 = MagicMock(spec=GameParticipant)
        mock_participant1.user_id = user_id1

        mock_participant2 = MagicMock(spec=GameParticipant)
        mock_participant2.user_id = user_id2

        mock_result.scalars.return_value.all.return_value = [
            mock_participant1,
            mock_participant2,
        ]
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_non_existent_game_returns_zero(self):
        """Test that function returns 0 for non-existent game ID."""
        non_existent_game_id = str(uuid4())

        # Mock database session with empty result
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, non_existent_game_id)
        assert count == 0


class TestSendDeferredResponse:
    """Tests for send_deferred_response function."""

    @pytest.mark.asyncio
    async def test_logs_warning_when_defer_raises_http_exception(self):
        """Test that an HTTPException from defer is logged as a warning."""
        mock_interaction = MagicMock()
        mock_interaction.response.is_done.return_value = False
        mock_interaction.user.id = 123456789
        mock_interaction.response.defer = AsyncMock(
            side_effect=discord.HTTPException(MagicMock(status=400), "Unknown interaction")
        )

        with patch("services.bot.handlers.utils.logger") as mock_logger:
            await send_deferred_response(mock_interaction)
            mock_logger.warning.assert_called_once()
            args = mock_logger.warning.call_args[0]
            assert "123456789" in str(args)


class TestSendErrorMessage:
    """Tests for send_error_message function."""

    @pytest.mark.asyncio
    async def test_sends_error_dm(self):
        """Test that error message is sent as DM to user."""
        mock_interaction = MagicMock()
        mock_interaction.user.send = AsyncMock()
        mock_interaction.user.id = 123456789

        await send_error_message(mock_interaction, "Something went wrong")

        mock_interaction.user.send.assert_called_once_with(content="\u274c Something went wrong")

    @pytest.mark.asyncio
    async def test_logs_warning_when_dm_raises_forbidden(self):
        """Test that Forbidden exception from DM is logged as warning."""
        mock_interaction = MagicMock()
        mock_interaction.user.id = 123456789
        mock_interaction.user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), ""))

        with patch("services.bot.handlers.utils.logger") as mock_logger:
            await send_error_message(mock_interaction, "error message")
            mock_logger.warning.assert_called_once_with(ANY, ANY, ANY)


class TestSendSuccessMessage:
    """Tests for send_success_message function."""

    @pytest.mark.asyncio
    async def test_sends_success_dm(self):
        """Test that success message is sent as DM to user."""
        mock_interaction = MagicMock()
        mock_interaction.user.send = AsyncMock()
        mock_interaction.user.id = 123456789

        await send_success_message(mock_interaction, "Game joined!")

        mock_interaction.user.send.assert_called_once_with(content="Game joined!")

    @pytest.mark.asyncio
    async def test_logs_warning_when_dm_raises_forbidden(self):
        """Test that Forbidden exception from success DM is logged as warning."""
        mock_interaction = MagicMock()
        mock_interaction.user.id = 123456789
        mock_interaction.user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), ""))

        with patch("services.bot.handlers.utils.logger") as mock_logger:
            await send_success_message(mock_interaction, "success message")
            mock_logger.warning.assert_called_once_with(ANY, ANY, ANY)
