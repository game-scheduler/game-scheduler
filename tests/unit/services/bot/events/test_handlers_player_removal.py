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


"""Unit tests for EventHandlers player removal methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest


@pytest.mark.asyncio
async def test_update_message_for_player_removal_success(
    event_handlers, mock_bot, sample_game, sample_user
):
    """Test successful message update after player removal."""
    channel_id = "123456789"
    message_id = "987654321"

    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_message = AsyncMock()
    mock_channel.get_partial_message = MagicMock(return_value=mock_message)
    mock_bot.get_channel.return_value = mock_channel

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=sample_game),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            return_value=("content", "embed", "view"),
        ),
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            sample_game.id, message_id, channel_id
        )

        mock_channel.get_partial_message.assert_called_once_with(int(message_id))
        mock_message.edit.assert_awaited_once()
        mock_get_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_update_message_for_player_removal_game_not_found(event_handlers, mock_bot):
    """Test message update when game is not found."""
    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=None),
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            "invalid_game_id", "msg123", "channel123"
        )

        mock_logger.error.assert_called()
        assert any("Game not found" in str(call) for call in mock_logger.error.call_args_list)
        mock_get_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_update_message_for_player_removal_message_not_found(
    event_handlers, mock_bot, sample_game
):
    """Test message update when Discord message is not found during edit."""
    channel_id = "123456789"
    message_id = "987654321"

    mock_message = AsyncMock()
    mock_message.edit = AsyncMock(side_effect=discord.NotFound(MagicMock(), MagicMock()))
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.get_partial_message = MagicMock(return_value=mock_message)
    mock_bot.get_channel.return_value = mock_channel

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_get_db_session,
        patch.object(event_handlers, "_get_game_with_participants", return_value=sample_game),
        patch.object(
            event_handlers,
            "_create_game_announcement",
            return_value=("content", "embed", "view"),
        ),
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        mock_db = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db

        await event_handlers._update_message_for_player_removal(
            sample_game.id, message_id, channel_id
        )

        mock_logger.warning.assert_called()
        assert any(
            "Game message not found" in str(call) for call in mock_logger.warning.call_args_list
        )
        mock_get_db_session.assert_called_once_with()


def test_build_removal_dm_message_without_schedule(event_handlers):
    """Test building removal DM message without scheduled time."""
    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", None)

        assert message == "You have been removed from Test Game"
        mock_removal.assert_called_once_with("Test Game")


def test_build_removal_dm_message_with_schedule(event_handlers):
    """Test building removal DM message with scheduled time."""
    scheduled_at = "2026-01-20T15:00:00+00:00"

    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", scheduled_at)

        assert "You have been removed from Test Game" in message
        assert " scheduled for <t:" in message
        assert ":F>" in message
        mock_removal.assert_called_once_with("Test Game")


def test_build_removal_dm_message_with_invalid_schedule(event_handlers):
    """Test building removal DM message with invalid scheduled time."""
    with patch("services.bot.events.handlers.DMFormats.removal") as mock_removal:
        mock_removal.return_value = "You have been removed from Test Game"

        message = event_handlers._build_removal_dm_message("Test Game", "invalid-date")

        assert message == "You have been removed from Test Game"
        mock_removal.assert_called_once_with("Test Game")


@pytest.mark.asyncio
async def test_notify_removed_player_success(event_handlers):
    """Test successful notification to removed player."""
    with patch.object(event_handlers, "_send_dm", return_value=True) as mock_send_dm:
        await event_handlers._notify_removed_player(
            "123456789", "Test Game", "2026-01-20T15:00:00+00:00"
        )

        mock_send_dm.assert_awaited_once()
        assert mock_send_dm.call_args[0][0] == "123456789"


@pytest.mark.asyncio
async def test_notify_removed_player_no_discord_id(event_handlers):
    """Test notification attempt with no Discord ID."""
    with (
        patch.object(event_handlers, "_send_dm") as mock_send_dm,
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        await event_handlers._notify_removed_player(None, "Test Game", None)

        mock_send_dm.assert_not_awaited()
        mock_logger.warning.assert_called()
        assert any(
            "No discord_id provided" in str(call) for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_notify_removed_player_dm_failure(event_handlers):
    """Test handling of DM send failure."""
    with (
        patch.object(event_handlers, "_send_dm", return_value=False) as mock_send_dm,
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        await event_handlers._notify_removed_player("123456789", "Test Game", None)

        mock_send_dm.assert_awaited_once()
        mock_logger.warning.assert_called()
        assert any(
            "Failed to send removal DM" in str(call) for call in mock_logger.warning.call_args_list
        )
