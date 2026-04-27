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


"""Unit tests for EventHandlers refresh game message methods."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest


class TestRefreshGameMessageHelpers:
    """Tests for _refresh_game_message extracted helper methods."""

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_success(self, event_handlers, sample_game):
        """Test successful game fetch with message_id."""
        mock_db = MagicMock()
        sample_game.message_id = "123456789"

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=sample_game),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, sample_game.id)

        assert result is sample_game

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_no_game(self, event_handlers):
        """Test game fetch when game not found."""
        mock_db = MagicMock()
        game_id = str(uuid4())

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=None),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, game_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_game_for_refresh_no_message_id(self, event_handlers, sample_game):
        """Test game fetch when game has no message_id."""
        mock_db = MagicMock()
        sample_game.message_id = None

        with patch.object(
            event_handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=sample_game),
        ):
            result = await event_handlers._fetch_game_for_refresh(mock_db, sample_game.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_success(self, event_handlers, mock_bot):
        """Test successful channel validation using gateway cache only."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is mock_channel
        mock_bot.fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_not_in_cache(self, event_handlers, mock_bot):
        """Test channel validation returns None when channel absent from gateway cache."""
        channel_id = "123456789"
        mock_bot.get_channel.return_value = None

        result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is None
        mock_bot.fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_does_not_call_discord_api(
        self, event_handlers, mock_bot
    ):
        """Test that channel validation never calls the REST Discord API."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is mock_channel
        mock_bot.fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_channel_for_refresh_invalid_type(self, event_handlers, mock_bot):
        """Test channel validation returns None when channel is not a TextChannel."""
        channel_id = "123456789"
        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_bot.get_channel.return_value = mock_channel

        result = await event_handlers._validate_channel_for_refresh(channel_id)

        assert result is None
        mock_bot.fetch_channel.assert_not_called()

    def test_get_channel_and_partial_message_success(self, event_handlers, mock_bot):
        """Test _get_channel_and_partial_message returns (channel, partial_message) from cache."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_partial_message = MagicMock(spec=discord.PartialMessage)
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.get_partial_message = MagicMock(return_value=mock_partial_message)
        mock_bot.get_channel.return_value = mock_channel

        result = event_handlers._get_channel_and_partial_message(channel_id, message_id)

        assert result == (mock_channel, mock_partial_message)
        mock_channel.get_partial_message.assert_called_once_with(int(message_id))
        mock_bot.fetch_channel.assert_not_called()

    def test_get_channel_and_partial_message_channel_not_in_cache(self, event_handlers, mock_bot):
        """Test that a missing cache channel returns None without REST fallback."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_bot.get_channel.return_value = None

        result = event_handlers._get_channel_and_partial_message(channel_id, message_id)

        assert result is None
        mock_bot.fetch_channel.assert_not_called()

    def test_get_channel_and_partial_message_wrong_channel_type(self, event_handlers, mock_bot):
        """Test that a non-TextChannel cache hit returns None."""
        channel_id = "123456789"
        message_id = "987654321"
        mock_voice_channel = MagicMock(spec=discord.VoiceChannel)
        mock_bot.get_channel.return_value = mock_voice_channel

        result = event_handlers._get_channel_and_partial_message(channel_id, message_id)

        assert result is None
        mock_bot.get_channel.assert_called_once_with(int(channel_id))

    @pytest.mark.asyncio
    async def test_update_game_message_content(self, event_handlers, sample_game):
        """Test message content update."""
        mock_message = AsyncMock(spec=discord.Message)
        mock_content = "Test content"
        mock_embed = MagicMock(spec=discord.Embed)
        mock_view = MagicMock()

        with patch.object(
            event_handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=(mock_content, mock_embed, mock_view)),
        ):
            await event_handlers._update_game_message_content(mock_message, sample_game)

        mock_message.edit.assert_called_once_with(
            content=mock_content, embed=mock_embed, view=mock_view
        )


@pytest.mark.asyncio
async def test_refresh_game_message_success(event_handlers, sample_game, mock_bot):
    """Test successful game message refresh through all steps."""
    sample_game.message_id = "123456789"

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_message = MagicMock(spec=discord.PartialMessage)
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.get_partial_message = MagicMock(return_value=mock_message)
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=mock_channel
        ) as mock_validate,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_db.assert_called_once_with()
        mock_fetch.assert_called_once_with(mock_db_instance, sample_game.id)
        mock_validate.assert_called_once_with(str(sample_game.channel.channel_id))
        mock_channel.get_partial_message.assert_called_once_with(int(sample_game.message_id))
        mock_update.assert_called_once_with(mock_message, sample_game)


@pytest.mark.asyncio
async def test_refresh_game_message_game_not_found(event_handlers, mock_bot):
    """Test refresh when game not found or has no message_id."""
    game_id = str(uuid4())
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(event_handlers, "_fetch_game_for_refresh", return_value=None) as mock_fetch,
        patch.object(event_handlers, "_validate_channel_for_refresh") as mock_validate,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(game_id)

        mock_db.assert_called_once_with()
        mock_fetch.assert_called_once_with(mock_db_instance, game_id)
        mock_validate.assert_not_called()
        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_game_message_channel_validation_fails(event_handlers, sample_game, mock_bot):
    """Test refresh when channel validation fails."""
    sample_game.message_id = "123456789"

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=None
        ) as mock_validate,
        patch.object(event_handlers, "_update_game_message_content") as mock_update,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_db.assert_called_once_with()
        mock_fetch.assert_called_once_with(mock_db_instance, sample_game.id)
        mock_validate.assert_called_once_with(str(sample_game.channel.channel_id))
        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_game_message_message_not_found(event_handlers, sample_game, mock_bot):
    """Test refresh propagates NotFound from edit through the outer exception handler."""
    sample_game.message_id = "123456789"

    mock_channel_config = MagicMock()
    mock_channel_config.channel_id = "123456789"
    sample_game.channel = mock_channel_config

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers, "_fetch_game_for_refresh", return_value=sample_game
        ) as mock_fetch,
        patch.object(
            event_handlers, "_validate_channel_for_refresh", return_value=mock_channel
        ) as mock_validate,
        patch.object(
            event_handlers,
            "_update_game_message_content",
            side_effect=discord.NotFound(MagicMock(), "Not found"),
        ) as mock_update,
        patch("services.bot.events.handlers.logger") as mock_logger,
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_db.assert_called_once_with()
        mock_fetch.assert_called_once_with(mock_db_instance, sample_game.id)
        mock_validate.assert_called_once_with(str(sample_game.channel.channel_id))
        mock_update.assert_called_once_with(
            mock_channel.get_partial_message.return_value, sample_game
        )
        mock_logger.exception.assert_called_once()
        exception_args = mock_logger.exception.call_args.args
        assert exception_args[0] == "Failed to refresh game message: %s"
        assert isinstance(exception_args[1], discord.NotFound)


@pytest.mark.asyncio
async def test_refresh_game_message_handles_exception(event_handlers, sample_game, mock_bot):
    """Test refresh handles exceptions gracefully."""
    mock_db_instance = MagicMock()

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db,
        patch.object(
            event_handlers,
            "_fetch_game_for_refresh",
            side_effect=Exception("Database error"),
        ),
    ):
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        mock_db.return_value.__aexit__.return_value = None

        await event_handlers._refresh_game_message(sample_game.id)

        mock_db.assert_called_once_with()
        assert True  # exception handled gracefully; function returns without raising
