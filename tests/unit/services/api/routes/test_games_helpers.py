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


"""
Unit tests for games route helper functions.

Tests the extracted helper functions from update_game and _build_game_response refactoring.
"""

import json
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from services.api.routes.games import (
    _build_host_response,
    _build_participant_responses,
    _fetch_discord_names,
    _parse_update_form_data,
    _process_image_upload,
    _resolve_display_data,
)
from shared.models.participant import ParticipantType


class TestParseUpdateFormData:
    """Tests for _parse_update_form_data helper function."""

    def test_parse_all_fields_provided(self):
        """Parse all fields when provided."""
        scheduled_at = "2026-01-20T18:00:00Z"
        reminder_minutes = json.dumps([60, 15])
        notify_role_ids = json.dumps(["role1", "role2"])
        participants = json.dumps([{"type": "discord", "id": "user1"}])
        removed_participant_ids = json.dumps(["part1", "part2"])

        (
            scheduled_at_dt,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(
            scheduled_at,
            reminder_minutes,
            notify_role_ids,
            participants,
            removed_participant_ids,
        )

        assert scheduled_at_dt == datetime(2026, 1, 20, 18, 0, 0, tzinfo=UTC)
        assert reminder_list == [60, 15]
        assert role_ids_list == ["role1", "role2"]
        assert participants_list == [{"type": "discord", "id": "user1"}]
        assert removed_list == ["part1", "part2"]

    def test_parse_all_fields_none(self):
        """Parse returns None for all fields when None provided."""
        (
            scheduled_at_dt,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(None, None, None, None, None)

        assert scheduled_at_dt is None
        assert reminder_list is None
        assert role_ids_list is None
        assert participants_list is None
        assert removed_list is None

    def test_parse_scheduled_at_with_z_suffix(self):
        """Parse ISO datetime with Z suffix correctly."""
        scheduled_at = "2026-02-14T12:30:00Z"

        (scheduled_at_dt, _, _, _, _) = _parse_update_form_data(
            scheduled_at, None, None, None, None
        )

        assert scheduled_at_dt == datetime(2026, 2, 14, 12, 30, 0, tzinfo=UTC)

    def test_parse_scheduled_at_with_timezone_offset(self):
        """Parse ISO datetime with timezone offset."""
        scheduled_at = "2026-02-14T12:30:00+05:00"

        (scheduled_at_dt, _, _, _, _) = _parse_update_form_data(
            scheduled_at, None, None, None, None
        )

        # Should parse the timezone offset correctly
        assert scheduled_at_dt.hour == 12
        assert scheduled_at_dt.tzinfo is not None

    def test_parse_empty_json_arrays(self):
        """Parse empty JSON arrays correctly."""
        (
            _,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(None, "[]", "[]", "[]", "[]")

        assert reminder_list == []
        assert role_ids_list == []
        assert participants_list == []
        assert removed_list == []

    def test_parse_complex_participants(self):
        """Parse complex participant JSON structures."""
        participants = json.dumps([
            {"type": "discord", "id": "123456"},
            {"type": "placeholder", "display_name": "Guest Player"},
        ])

        (_, _, _, participants_list, _) = _parse_update_form_data(
            None, None, None, participants, None
        )

        assert len(participants_list) == 2
        assert participants_list[0]["type"] == "discord"
        assert participants_list[1]["display_name"] == "Guest Player"


class TestProcessImageUpload:
    """Tests for _process_image_upload helper function."""

    async def test_process_remove_flag_returns_empty_bytes(self):
        """Returns empty bytes and empty string when remove flag is True."""
        image_data, mime_type = await _process_image_upload(None, True, "thumbnail", "game123")

        assert image_data == b""
        assert mime_type == ""

    async def test_process_no_file_returns_none(self):
        """Returns None tuple when no file and remove flag False."""
        image_data, mime_type = await _process_image_upload(None, False, "thumbnail", "game123")

        assert image_data is None
        assert mime_type is None

    async def test_process_valid_image_upload(self):
        """Process valid image upload successfully."""
        # Create mock UploadFile
        file_content = b"fake image data"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.png"
        mock_file.content_type = "image/png"
        mock_file.size = len(file_content)
        mock_file.file = BytesIO(file_content)
        mock_file.read = AsyncMock(return_value=file_content)

        # Mock the file operations
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=len(file_content))

        image_data, mime_type = await _process_image_upload(
            mock_file, False, "thumbnail", "game123"
        )

        assert image_data == file_content
        assert mime_type == "image/png"
        mock_file.read.assert_called_once()

    async def test_process_different_image_types(self):
        """Process different image MIME types correctly."""
        for content_type in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
            file_content = b"image data"
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = content_type
            mock_file.size = len(file_content)
            mock_file.file = BytesIO(file_content)
            mock_file.read = AsyncMock(return_value=file_content)
            mock_file.file.seek = MagicMock()
            mock_file.file.tell = MagicMock(return_value=len(file_content))

            _, mime_type = await _process_image_upload(mock_file, False, "image", "game123")

            assert mime_type == content_type

    async def test_process_remove_flag_takes_precedence_over_file(self):
        """Remove flag takes precedence even when file provided."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock()

        image_data, mime_type = await _process_image_upload(mock_file, True, "thumbnail", "game123")

        assert image_data == b""
        assert mime_type == ""
        mock_file.read.assert_not_called()

    async def test_process_invalid_file_type_raises_exception(self):
        """Invalid file type raises HTTPException."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 100
        mock_file.file = BytesIO(b"text content")
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=100)

        with pytest.raises(HTTPException) as exc_info:
            await _process_image_upload(mock_file, False, "thumbnail", "game123")

        assert exc_info.value.status_code == 400
        assert "PNG, JPEG, GIF, or WebP" in exc_info.value.detail

    async def test_process_file_too_large_raises_exception(self):
        """File larger than 5MB raises HTTPException."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.png"
        mock_file.content_type = "image/png"
        mock_file.size = 6 * 1024 * 1024  # 6MB
        mock_file.file = BytesIO(b"x" * (6 * 1024 * 1024))
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=6 * 1024 * 1024)

        with pytest.raises(HTTPException) as exc_info:
            await _process_image_upload(mock_file, False, "image", "game123")

        assert exc_info.value.status_code == 400
        assert "less than 5MB" in exc_info.value.detail


class TestBuildGameResponseHelpers:
    """Tests for _build_game_response helper functions."""

    @patch("services.api.routes.games.display_names_module.get_display_name_resolver")
    async def test_resolve_display_data_with_participants_and_host(
        self, mock_get_resolver, sample_game, sample_partitioned_participants
    ):
        """Resolve display data for participants and host."""
        mock_resolver = AsyncMock()
        mock_resolver.resolve_display_names_and_avatars = AsyncMock(
            return_value={
                "discord123": {
                    "display_name": "User1",
                    "avatar_url": "http://avatar1.com",
                },
                "discord456": {
                    "display_name": "User2",
                    "avatar_url": "http://avatar2.com",
                },
                "host_discord": {
                    "display_name": "Host",
                    "avatar_url": "http://host.com",
                },
            }
        )
        mock_get_resolver.return_value = mock_resolver

        sample_game.host = MagicMock()
        sample_game.host.discord_id = "host_discord"
        sample_game.guild_id = "guild123"
        sample_game.guild = MagicMock()
        sample_game.guild.guild_id = "guild123"

        display_data_map, host_discord_id = await _resolve_display_data(
            sample_game, sample_partitioned_participants
        )

        assert host_discord_id == "host_discord"
        assert "discord123" in display_data_map
        assert "host_discord" in display_data_map
        mock_resolver.resolve_display_names_and_avatars.assert_called_once()

    async def test_resolve_display_data_without_guild(
        self, sample_game, sample_partitioned_participants
    ):
        """Display data map empty when no guild."""
        sample_game.guild_id = None

        display_data_map, host_discord_id = await _resolve_display_data(
            sample_game, sample_partitioned_participants
        )

        assert display_data_map == {}
        assert host_discord_id is None

    @patch("services.api.routes.games.fetch_guild_name_safe")
    @patch("services.api.routes.games.fetch_channel_name_safe")
    async def test_fetch_discord_names_with_channel_and_guild(
        self, mock_fetch_channel, mock_fetch_guild, sample_game
    ):
        """Fetch both channel and guild names."""
        mock_fetch_channel.return_value = "general"
        mock_fetch_guild.return_value = "Test Guild"

        sample_game.channel = MagicMock()
        sample_game.channel.channel_id = "channel123"
        sample_game.guild = MagicMock()
        sample_game.guild.guild_id = "guild123"

        channel_name, guild_name = await _fetch_discord_names(sample_game)

        assert channel_name == "general"
        assert guild_name == "Test Guild"
        mock_fetch_channel.assert_called_once_with("channel123")
        mock_fetch_guild.assert_called_once_with("guild123")

    async def test_fetch_discord_names_without_channel_and_guild(self, sample_game):
        """Return None when no channel or guild."""
        sample_game.channel = None
        sample_game.guild = None

        channel_name, guild_name = await _fetch_discord_names(sample_game)

        assert channel_name is None
        assert guild_name is None

    def test_build_participant_responses(self, sample_partitioned_participants):
        """Build participant response list from partitioned data."""
        display_data_map = {
            "discord123": {"display_name": "User1", "avatar_url": "http://avatar1.com"},
            "discord456": {"display_name": "User2", "avatar_url": "http://avatar2.com"},
        }

        responses = _build_participant_responses(sample_partitioned_participants, display_data_map)

        assert len(responses) == 2
        assert responses[0].discord_id == "discord123"
        assert responses[0].display_name == "User1"
        assert responses[0].avatar_url == "http://avatar1.com"
        assert responses[1].discord_id == "discord456"
        assert responses[1].display_name == "User2"

    def test_build_participant_responses_with_placeholder(self, sample_partitioned_participants):
        """Build participant responses with placeholder participant."""
        sample_partitioned_participants.all_sorted[0].user = None
        sample_partitioned_participants.all_sorted[0].display_name = "Placeholder"

        responses = _build_participant_responses(sample_partitioned_participants, {})

        assert len(responses) == 2
        assert responses[0].discord_id is None
        assert responses[0].display_name == "Placeholder"
        assert responses[0].avatar_url is None

    def test_build_host_response_with_display_data(self, sample_game):
        """Build host response with display data."""
        display_data_map = {
            "host_discord": {"display_name": "Host", "avatar_url": "http://host.com"}
        }

        response = _build_host_response(sample_game, "host_discord", display_data_map)

        assert response.id == sample_game.host_id
        assert response.discord_id == "host_discord"
        assert response.display_name == "Host"
        assert response.avatar_url == "http://host.com"
        assert response.position_type == ParticipantType.SELF_ADDED
        assert response.position == 0

    def test_build_host_response_without_display_data(self, sample_game):
        """Build host response without display data."""
        response = _build_host_response(sample_game, "host_discord", {})

        assert response.id == sample_game.host_id
        assert response.discord_id == "host_discord"
        assert response.display_name is None
        assert response.avatar_url is None


@pytest.fixture
def sample_game():
    """Create sample game for testing."""
    game = MagicMock()
    game.id = "game123"
    game.host_id = "host123"
    game.host = MagicMock()
    game.host.discord_id = None
    game.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    game.participants = []
    game.guild_id = "guild123"
    game.channel = None
    game.guild = None
    return game


@pytest.fixture
def sample_partitioned_participants():
    """Create sample partitioned participants."""
    part1 = MagicMock()
    part1.id = "part1"
    part1.game_session_id = "game123"
    part1.user_id = "user1"
    part1.user = MagicMock()
    part1.user.discord_id = "discord123"
    part1.display_name = "OldName1"
    part1.joined_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    part1.position_type = ParticipantType.SELF_ADDED
    part1.position = 1

    part2 = MagicMock()
    part2.id = "part2"
    part2.game_session_id = "game123"
    part2.user_id = "user2"
    part2.user = MagicMock()
    part2.user.discord_id = "discord456"
    part2.display_name = "OldName2"
    part2.joined_at = datetime(2026, 1, 15, 10, 5, 0, tzinfo=UTC)
    part2.position_type = ParticipantType.SELF_ADDED
    part2.position = 2

    partitioned = MagicMock()
    partitioned.all_sorted = [part1, part2]
    return partitioned
