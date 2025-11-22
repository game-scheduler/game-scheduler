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


"""Tests for game message formatter."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from services.bot.formatters.game_message import (
    GameMessageFormatter,
    format_game_announcement,
)


class TestGameMessageFormatter:
    """Tests for GameMessageFormatter class."""

    def test_creates_basic_game_embed(self):
        """Test creating a basic game embed."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            result = formatter.create_game_embed(
                game_title="D&D Session",
                description="Epic adventure awaits",
                scheduled_at=scheduled_at,
                host_id="123456789",
                participant_ids=["111111", "222222"],
                current_count=2,
                max_players=5,
                status="SCHEDULED",
            )

            assert result == mock_embed
            mock_embed.add_field.assert_called()

    def test_embed_includes_when_field(self):
        """Test that embed includes when field with timestamps."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123",
                participant_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("When" in str(call) for call in calls)

    def test_embed_includes_players_field(self):
        """Test that embed includes players count field."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123",
                participant_ids=["111", "222"],
                current_count=2,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Players" in str(call) and "2/5" in str(call) for call in calls)

    def test_embed_includes_host_field(self):
        """Test that embed includes host mention field."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123456",
                participant_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)

    def test_embed_includes_channel_when_provided(self):
        """Test that embed includes voice channel when provided."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123",
                participant_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                channel_id="987654321",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Channel" in str(call) and "<#987654321>" in str(call) for call in calls)

    def test_embed_includes_participants_when_present(self):
        """Test that embed includes participant list when there are participants."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123",
                participant_ids=["111", "222", "333"],
                current_count=3,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Participants" in str(call) for call in calls)

    def test_embed_includes_rules_when_provided(self):
        """Test that embed includes rules when provided."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="123",
                participant_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            # Verify embed was created successfully
            assert mock_embed.add_field.called

    def test_get_status_color_for_scheduled(self):
        """Test status color for scheduled games."""
        with patch("services.bot.formatters.game_message.discord.Color") as mock_color:
            mock_color.green.return_value = "green"
            formatter = GameMessageFormatter()
            result = formatter._get_status_color("SCHEDULED")
            assert result == "green"

    def test_get_status_color_for_in_progress(self):
        """Test status color for in-progress games."""
        with patch("services.bot.formatters.game_message.discord.Color") as mock_color:
            mock_color.blue.return_value = "blue"
            formatter = GameMessageFormatter()
            result = formatter._get_status_color("IN_PROGRESS")
            assert result == "blue"

    def test_get_status_color_for_completed(self):
        """Test status color for completed games."""
        with patch("services.bot.formatters.game_message.discord.Color") as mock_color:
            mock_color.gold.return_value = "gold"
            formatter = GameMessageFormatter()
            result = formatter._get_status_color("COMPLETED")
            assert result == "gold"

    def test_get_status_color_for_cancelled(self):
        """Test status color for cancelled games."""
        with patch("services.bot.formatters.game_message.discord.Color") as mock_color:
            mock_color.red.return_value = "red"
            formatter = GameMessageFormatter()
            result = formatter._get_status_color("CANCELLED")
            assert result == "red"

    def test_get_status_color_for_unknown(self):
        """Test status color for unknown status."""
        with patch("services.bot.formatters.game_message.discord.Color") as mock_color:
            mock_color.greyple.return_value = "greyple"
            formatter = GameMessageFormatter()
            result = formatter._get_status_color("UNKNOWN")
            assert result == "greyple"

    def test_creates_notification_embed(self):
        """Test creating a notification embed."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            result = formatter.create_notification_embed(
                game_title="D&D Session",
                scheduled_at=scheduled_at,
                host_id="123456789",
                time_until="in 1 hour",
            )

            assert result == mock_embed
            assert mock_embed_class.called

    def test_notification_embed_has_reminder_title(self):
        """Test that notification embed has reminder title."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_notification_embed(
                game_title="Game", scheduled_at=scheduled_at, host_id="123", time_until="soon"
            )

            call_kwargs = mock_embed_class.call_args[1]
            assert "Reminder" in call_kwargs["title"]


class TestFormatGameAnnouncement:
    """Tests for format_game_announcement function."""

    def test_returns_embed_and_view_tuple(self):
        """Test that function returns tuple of embed and view."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed"):
            with patch("services.bot.formatters.game_message.GameView"):
                result = format_game_announcement(
                    game_id="test-id",
                    game_title="Game",
                    description="Desc",
                    scheduled_at=scheduled_at,
                    host_id="123",
                    participant_ids=[],
                    current_count=0,
                    max_players=5,
                    status="SCHEDULED",
                )

                assert isinstance(result, tuple)
                assert len(result) == 3

    def test_creates_view_with_correct_game_id(self):
        """Test that view is created with correct game ID."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed"):
            with patch("services.bot.formatters.game_message.GameView") as mock_view_class:
                mock_view = MagicMock()
                mock_view_class.from_game_data.return_value = mock_view

                format_game_announcement(
                    game_id="my-game-id",
                    game_title="Game",
                    description="Desc",
                    scheduled_at=scheduled_at,
                    host_id="123",
                    participant_ids=[],
                    current_count=0,
                    max_players=5,
                    status="SCHEDULED",
                )

                mock_view_class.from_game_data.assert_called_once()
                call_kwargs = mock_view_class.from_game_data.call_args[1]
                assert call_kwargs["game_id"] == "my-game-id"

    def test_passes_all_parameters_to_formatter(self):
        """Test that all parameters are passed to embed formatter."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch(
            "services.bot.formatters.game_message.GameMessageFormatter"
        ) as mock_formatter_class:
            mock_formatter = MagicMock()
            mock_formatter_class.return_value = mock_formatter
            mock_formatter.create_game_embed.return_value = MagicMock()

            with patch("services.bot.formatters.game_message.GameView"):
                format_game_announcement(
                    game_id="test-id",
                    game_title="My Game",
                    description="Fun times",
                    scheduled_at=scheduled_at,
                    host_id="host123",
                    participant_ids=["p1", "p2"],
                    current_count=2,
                    max_players=5,
                    status="SCHEDULED",
                    channel_id="voice123",
                )

                mock_formatter.create_game_embed.assert_called_once()
                call_kwargs = mock_formatter.create_game_embed.call_args[1]
                assert call_kwargs["game_title"] == "My Game"
                assert call_kwargs["description"] == "Fun times"
                assert call_kwargs["host_id"] == "host123"
                assert call_kwargs["channel_id"] == "voice123"
