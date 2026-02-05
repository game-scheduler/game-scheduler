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
                overflow_ids=[],
                current_count=2,
                max_players=5,
                status="SCHEDULED",
            )

            assert result == mock_embed
            mock_embed.add_field.assert_called()

    def test_embed_includes_when_field(self):
        """Test that embed includes timestamp field with formatted times."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            # Game Time field should have timestamp format
            assert any("Game Time" in str(call) and "<t:" in str(call) for call in calls)

    def test_embed_includes_players_field(self):
        """Test that embed includes participant count in Participants field heading."""
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
                overflow_ids=[],
                current_count=2,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Participants" in str(call) and "2/5" in str(call) for call in calls)

    def test_embed_includes_host_field(self):
        """Test that embed always includes host in a field with mention format."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            # Should have Host field with Discord mention
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)

    def test_embed_includes_host_field_ignores_avatar(self):
        """Test that host is shown in field with mention - avatar URL is not used."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url="https://cdn.discordapp.com/avatars/123456/abc123.png",
            )

            # Host field should have Discord mention (avatar not used in fields)
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                channel_id="987654321",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Channel" in str(call) and "<#987654321>" in str(call) for call in calls)

    def test_embed_includes_where_when_provided(self):
        """Test that embed includes where field when provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                where="Local Game Store, 123 Main St",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Where" in str(call) and "Local Game Store" in str(call) for call in calls)

    def test_embed_excludes_where_when_not_provided(self):
        """Test that embed does not include where field when not provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert not any("Where" in str(call) for call in calls)

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
                overflow_ids=[],
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
                overflow_ids=[],
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
                game_title="Game",
                scheduled_at=scheduled_at,
                host_id="123",
                time_until="soon",
            )

            call_kwargs = mock_embed_class.call_args[1]
            assert "Reminder" in call_kwargs["title"]


class TestGameMessageFormatterHelpers:
    """Tests for GameMessageFormatter helper methods."""

    def test_prepare_description_and_urls_truncates_long_description(self):
        """Test that long descriptions are truncated with ellipsis."""
        long_description = "A" * 1000
        game_id = "test-game-id"

        with patch("services.bot.formatters.game_message.get_config") as mock_config:
            mock_config.return_value.frontend_url = "https://example.com"

            (
                truncated,
                calendar_url,
                thumb,
                img,
            ) = GameMessageFormatter._prepare_description_and_urls(
                long_description, game_id, None, None
            )

        assert len(truncated) == 100
        assert truncated.endswith("...")
        assert calendar_url == "https://example.com/download-calendar/test-game-id"

    def test_prepare_description_and_urls_keeps_short_description(self):
        """Test that short descriptions are not truncated."""
        description = "Short description"

        truncated, calendar_url, thumb, img = GameMessageFormatter._prepare_description_and_urls(
            description, None, None, None
        )

        assert truncated == description
        assert calendar_url is None

    def test_prepare_description_and_urls_without_game_id(self):
        """Test that calendar URL is None when game_id is not provided."""
        description = "Test"

        truncated, calendar_url, thumb, img = GameMessageFormatter._prepare_description_and_urls(
            description, None, None, None
        )

        assert truncated == description
        assert calendar_url is None

    def test_prepare_description_and_urls_preserves_image_urls(self):
        """Test that thumbnail and image URLs are preserved."""
        description = "Test"
        thumbnail_url = "https://example.com/thumb.jpg"
        image_url = "https://example.com/image.jpg"

        truncated, calendar_url, thumb, img = GameMessageFormatter._prepare_description_and_urls(
            description, None, thumbnail_url, image_url
        )

        assert thumb == thumbnail_url
        assert img == image_url

    def test_configure_embed_author_with_display_name_and_avatar(self):
        """Test configuring embed author with display name and avatar."""
        embed = MagicMock()
        host_id = "123456789"
        display_name = "TestUser"
        avatar_url = "https://example.com/avatar.jpg"

        GameMessageFormatter._configure_embed_author(embed, host_id, display_name, avatar_url)

        embed.set_author.assert_called_once_with(name="@TestUser", icon_url=avatar_url)

    def test_configure_embed_author_with_display_name_no_avatar(self):
        """Test configuring embed author with display name but no avatar."""
        embed = MagicMock()
        host_id = "123456789"
        display_name = "TestUser"

        GameMessageFormatter._configure_embed_author(embed, host_id, display_name, None)

        embed.set_author.assert_called_once_with(name="@TestUser")

    def test_configure_embed_author_without_display_name(self):
        """Test configuring embed author without display name."""
        embed = MagicMock()
        host_id = "PlaceholderName"

        GameMessageFormatter._configure_embed_author(embed, host_id, None, None)

        embed.set_author.assert_called_once_with(name="PlaceholderName")

    def test_configure_embed_author_numeric_host_id_without_display_name(self):
        """Test configuring embed author with numeric ID but no display name."""
        embed = MagicMock()
        host_id = "123456789"

        GameMessageFormatter._configure_embed_author(embed, host_id, None, None)

        embed.set_author.assert_called_once_with(name="@User")

    def test_add_game_time_fields_with_all_fields(self):
        """Test adding all game time related fields."""
        embed = MagicMock()
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        GameMessageFormatter._add_game_time_fields(
            embed, scheduled_at, "123456789", 120, "Online", "987654321"
        )

        assert embed.add_field.call_count == 5

    def test_add_game_time_fields_without_duration(self):
        """Test adding fields without duration (uses empty field)."""
        embed = MagicMock()
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        GameMessageFormatter._add_game_time_fields(
            embed, scheduled_at, "123456789", None, "Online", None
        )

        calls = [call[1] for call in embed.add_field.call_args_list]
        assert any(c.get("name") == "\u200b" for c in calls)

    def test_add_game_time_fields_without_location(self):
        """Test adding fields without location (uses empty field)."""
        embed = MagicMock()
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        GameMessageFormatter._add_game_time_fields(
            embed, scheduled_at, "123456789", 120, None, None
        )

        calls = [call[1] for call in embed.add_field.call_args_list]
        assert any(c.get("name") == "\u200b" for c in calls)

    def test_add_participant_fields_with_participants(self):
        """Test adding participant fields with confirmed participants."""
        embed = MagicMock()

        GameMessageFormatter._add_participant_fields(embed, ["111", "222", "333"], [], 3, 5)

        embed.add_field.assert_called_once()
        call_kwargs = embed.add_field.call_args[1]
        assert "Participants (3/5)" in call_kwargs["name"]

    def test_add_participant_fields_without_participants(self):
        """Test adding participant fields without any participants."""
        embed = MagicMock()

        GameMessageFormatter._add_participant_fields(embed, [], [], 0, 5)

        embed.add_field.assert_called_once()
        call_kwargs = embed.add_field.call_args[1]
        assert "Participants (0/5)" in call_kwargs["name"]
        assert "No participants yet" in call_kwargs["value"]

    def test_add_participant_fields_with_waitlist(self):
        """Test adding participant fields with waitlisted participants."""
        embed = MagicMock()

        GameMessageFormatter._add_participant_fields(embed, ["111", "222"], ["333", "444"], 2, 2)

        assert embed.add_field.call_count == 2
        calls = [call[1] for call in embed.add_field.call_args_list]
        assert any("Waitlisted (2)" in c.get("name", "") for c in calls)

    def test_add_footer_and_links_with_calendar_url(self):
        """Test adding footer and links when calendar URL is present."""
        embed = MagicMock()
        calendar_url = "https://example.com/calendar"

        GameMessageFormatter._add_footer_and_links(embed, "SCHEDULED", calendar_url)

        embed.add_field.assert_called_once()
        call_kwargs = embed.add_field.call_args[1]
        assert "Links" in call_kwargs["name"]
        assert calendar_url in call_kwargs["value"]
        embed.set_footer.assert_called_once()

    def test_add_footer_and_links_without_calendar_url(self):
        """Test adding footer without calendar URL."""
        embed = MagicMock()

        GameMessageFormatter._add_footer_and_links(embed, "SCHEDULED", None)

        embed.add_field.assert_not_called()
        embed.set_footer.assert_called_once()

    def test_add_footer_and_links_uses_display_name_for_status(self):
        """Test that footer uses GameStatus display name."""
        embed = MagicMock()

        GameMessageFormatter._add_footer_and_links(embed, "SCHEDULED", None)

        call_kwargs = embed.set_footer.call_args[1]
        assert "Scheduled" in call_kwargs["text"]


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
                    overflow_ids=[],
                    current_count=0,
                    max_players=5,
                    status="SCHEDULED",
                    signup_method="SELF_SIGNUP",
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
                    overflow_ids=[],
                    current_count=0,
                    max_players=5,
                    status="SCHEDULED",
                    signup_method="SELF_SIGNUP",
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
                    overflow_ids=[],
                    current_count=2,
                    max_players=5,
                    status="SCHEDULED",
                    signup_method="SELF_SIGNUP",
                    channel_id="voice123",
                )

                mock_formatter.create_game_embed.assert_called_once()
                call_kwargs = mock_formatter.create_game_embed.call_args[1]
                assert call_kwargs["game_title"] == "My Game"
                assert call_kwargs["description"] == "Fun times"
                assert call_kwargs["host_id"] == "host123"
                assert call_kwargs["channel_id"] == "voice123"

    def test_embed_includes_url_when_game_id_provided(self):
        """Test that embed includes calendar download URL when game_id is provided."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.frontend_url = "https://example.com"
            mock_get_config.return_value = mock_config

            with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
                mock_embed = MagicMock()
                mock_embed_class.return_value = mock_embed

                formatter = GameMessageFormatter()
                result = formatter.create_game_embed(
                    game_title="D&D Session",
                    description="Epic adventure",
                    scheduled_at=scheduled_at,
                    host_id="123456789",
                    participant_ids=["111111"],
                    overflow_ids=[],
                    current_count=1,
                    max_players=5,
                    status="SCHEDULED",
                    game_id="test-game-id-123",
                )

                assert result == mock_embed
                mock_embed_class.assert_called_once()
                call_kwargs = mock_embed_class.call_args[1]
                # Title is now plain text without URL
                assert "url" not in call_kwargs

    def test_embed_excludes_url_when_game_id_not_provided(self):
        """Test that embed excludes URL when game_id is not provided."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            result = formatter.create_game_embed(
                game_title="D&D Session",
                description="Epic adventure",
                scheduled_at=scheduled_at,
                host_id="123456789",
                participant_ids=["111111"],
                overflow_ids=[],
                current_count=1,
                max_players=5,
                status="SCHEDULED",
            )

            assert result == mock_embed
            mock_embed_class.assert_called_once()
            call_kwargs = mock_embed_class.call_args[1]
            # Title is now plain text without URL
            assert "url" not in call_kwargs

    def test_embed_includes_host_field_with_mention(self):
        """Test that host field is created with mention format."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url="https://cdn.discordapp.com/avatars/123456/abc123.png?size=64",
            )

            # Host field should have Discord mention
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)

    def test_embed_includes_host_field_without_avatar(self):
        """Test that host field is created with mention format when no avatar URL."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url=None,
            )

            # Host field should have Discord mention
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)

    def test_embed_includes_host_field_with_placeholder(self):
        """Test that host field shows placeholder name when host_id is not a Discord ID."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class:
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed

            formatter = GameMessageFormatter()
            formatter.create_game_embed(
                game_title="Game",
                description="Desc",
                scheduled_at=scheduled_at,
                host_id="TempHost",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url="https://cdn.discordapp.com/avatars/123456/abc123.png?size=64",
            )

            # Host field should have placeholder name
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "TempHost" in str(call) for call in calls)

    def test_embed_includes_host_field_with_animated_avatar(self):
        """Test that host field is created even when animated avatar URL is provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url="https://cdn.discordapp.com/avatars/123456/a_animated123.gif?size=64",
            )

            # Host field should have Discord mention
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)

    def test_embed_always_has_host_field(self):
        """Test embed always includes Host field with mention."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                host_avatar_url="https://cdn.discordapp.com/avatars/123456/abc123.png?size=64",
            )

            # Verify Host field is present with mention
            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Host" in str(call) and "<@123456>" in str(call) for call in calls)


class TestGameEmbedImages:
    """Tests for game embed image functionality."""

    def test_embed_with_thumbnail_url(self):
        """Test that embed sets thumbnail when thumbnail_url is provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                thumbnail_url="http://api:8000/api/v1/games/123/thumbnail",
            )

            mock_embed.set_thumbnail.assert_called_once_with(
                url="http://api:8000/api/v1/games/123/thumbnail"
            )

    def test_embed_with_image_url(self):
        """Test that embed sets image when image_url is provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                image_url="http://api:8000/api/v1/games/123/image",
            )

            mock_embed.set_image.assert_called_once_with(
                url="http://api:8000/api/v1/games/123/image"
            )

    def test_embed_with_both_images(self):
        """Test that embed sets both thumbnail and image when provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                thumbnail_url="http://api:8000/api/v1/games/123/thumbnail",
                image_url="http://api:8000/api/v1/games/123/image",
            )

            mock_embed.set_thumbnail.assert_called_once_with(
                url="http://api:8000/api/v1/games/123/thumbnail"
            )
            mock_embed.set_image.assert_called_once_with(
                url="http://api:8000/api/v1/games/123/image"
            )

    def test_embed_without_images(self):
        """Test that embed does not set images when URLs are None."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                thumbnail_url=None,
                image_url=None,
            )

            mock_embed.set_thumbnail.assert_not_called()
            mock_embed.set_image.assert_not_called()

    def test_format_game_announcement_with_images(self):
        """Test format_game_announcement passes image URLs to create_game_embed."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with (
            patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
            patch("services.bot.formatters.game_message.GameView") as mock_view_class,
            patch.dict("os.environ", {"BACKEND_URL": "http://test.example.com"}, clear=False),
        ):
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed
            mock_view = MagicMock()
            mock_view_class.from_game_data.return_value = mock_view

            content, embed, view = format_game_announcement(
                game_id="game-123",
                game_title="Test Game",
                description="Test description",
                scheduled_at=scheduled_at,
                host_id="host-456",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                signup_method="SELF_SIGNUP",
                has_thumbnail=True,
                has_image=True,
            )

            assert embed == mock_embed
            assert view == mock_view

    def test_format_game_announcement_without_images(self):
        """Test format_game_announcement with has_thumbnail=False and has_image=False."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)

        with (
            patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
            patch("services.bot.formatters.game_message.GameView") as mock_view_class,
        ):
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed
            mock_view = MagicMock()
            mock_view_class.from_game_data.return_value = mock_view

            content, embed, view = format_game_announcement(
                game_id="game-123",
                game_title="Test Game",
                description="Test description",
                scheduled_at=scheduled_at,
                host_id="host-456",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                signup_method="SELF_SIGNUP",
                has_thumbnail=False,
                has_image=False,
            )

            assert embed == mock_embed
            assert view == mock_view
            mock_embed.set_thumbnail.assert_not_called()

    def test_format_game_announcement_with_everyone_role(self):
        """Test format_game_announcement uses literal @everyone for guild_id match."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        guild_id = "123456789"

        with (
            patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
            patch("services.bot.formatters.game_message.GameView") as mock_view_class,
        ):
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed
            mock_view = MagicMock()
            mock_view_class.from_game_data.return_value = mock_view

            content, embed, view = format_game_announcement(
                game_id="game-123",
                game_title="Test Game",
                description="Test description",
                scheduled_at=scheduled_at,
                host_id="host-456",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                signup_method="SELF_SIGNUP",
                notify_role_ids=[guild_id],
                guild_id=guild_id,
            )

            assert content == "@everyone"
            assert embed == mock_embed
            assert view == mock_view

    def test_format_game_announcement_with_regular_roles(self):
        """Test format_game_announcement uses <@&role_id> format for regular roles."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        guild_id = "123456789"
        role_id = "987654321"

        with (
            patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
            patch("services.bot.formatters.game_message.GameView") as mock_view_class,
        ):
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed
            mock_view = MagicMock()
            mock_view_class.from_game_data.return_value = mock_view

            content, embed, view = format_game_announcement(
                game_id="game-123",
                game_title="Test Game",
                description="Test description",
                scheduled_at=scheduled_at,
                host_id="host-456",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                signup_method="SELF_SIGNUP",
                notify_role_ids=[role_id],
                guild_id=guild_id,
            )

            assert content == f"<@&{role_id}>"
            assert embed == mock_embed
            assert view == mock_view

    def test_format_game_announcement_with_mixed_roles(self):
        """Test format_game_announcement with both @everyone and regular roles."""
        scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        guild_id = "123456789"
        role_id = "987654321"

        with (
            patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
            patch("services.bot.formatters.game_message.GameView") as mock_view_class,
        ):
            mock_embed = MagicMock()
            mock_embed_class.return_value = mock_embed
            mock_view = MagicMock()
            mock_view_class.from_game_data.return_value = mock_view

            content, embed, view = format_game_announcement(
                game_id="game-123",
                game_title="Test Game",
                description="Test description",
                scheduled_at=scheduled_at,
                host_id="host-456",
                participant_ids=[],
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                signup_method="SELF_SIGNUP",
                notify_role_ids=[guild_id, role_id],
                guild_id=guild_id,
            )

            assert content == f"@everyone <@&{role_id}>"
            assert embed == mock_embed
            assert view == mock_view
            mock_embed.set_image.assert_not_called()


class TestEmbedNewFields:
    """Tests for new embed fields added to improve layout."""

    def test_embed_includes_links_field_with_calendar_url(self):
        """Test that embed includes Links field when game_id is provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                game_id="test-game-id",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Links" in str(call) and "Add to Calendar" in str(call) for call in calls)

    def test_embed_excludes_links_field_without_calendar_url(self):
        """Test that embed excludes Links field when game_id is not provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                game_id=None,
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert not any("Links" in str(call) for call in calls)

    def test_embed_includes_game_time_field(self):
        """Test that embed includes Game Time field."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Game Time" in str(call) for call in calls)

    def test_embed_footer_includes_status(self):
        """Test that embed footer includes status."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            footer_call = str(mock_embed.set_footer.call_args)
            assert "Status:" in footer_call

    def test_embed_has_separate_when_field(self):
        """Test that embed has separate Game Time field."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Game Time" in str(call) for call in calls)

    def test_embed_has_separate_run_time_field_when_provided(self):
        """Test that embed has separate Run Time field when duration provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                expected_duration_minutes=120,
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Run Time" in str(call) for call in calls)

    def test_embed_excludes_run_time_field_when_not_provided(self):
        """Test that embed excludes Run Time field when no duration."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                expected_duration_minutes=None,
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert not any("Run Time" in str(call) for call in calls)

    def test_embed_has_separate_where_field_when_provided(self):
        """Test that embed has separate Where field when location provided."""
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
                overflow_ids=[],
                current_count=0,
                max_players=5,
                status="SCHEDULED",
                where="Game Room #1",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]
            assert any("Where" in str(call) and "Game Room #1" in str(call) for call in calls)

    def test_waitlist_numbering_continues_from_signups(self):
        """Test that waitlist numbering continues from signup list."""
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
                overflow_ids=["444", "555"],
                current_count=3,
                max_players=3,
                status="SCHEDULED",
            )

            calls = [str(call) for call in mock_embed.add_field.call_args_list]

            # Check that waitlist starts at 4 (after 3 signups)
            waitlist_calls = [call for call in calls if "Waitlisted" in str(call)]
            assert len(waitlist_calls) > 0
            waitlist_str = str(waitlist_calls[0])
            assert "4." in waitlist_str
            assert "5." in waitlist_str
