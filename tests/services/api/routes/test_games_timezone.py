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


"""Tests for timezone handling in game API responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.user import User


@pytest.mark.asyncio
@patch("services.api.services.display_names.get_display_name_resolver")
async def test_scheduled_at_has_utc_marker(mock_get_resolver):
    """Test that scheduled_at includes 'Z' suffix for UTC."""
    # Mock display name resolver to avoid Discord API calls
    mock_resolver = AsyncMock()
    mock_resolver.resolve_display_names = AsyncMock(return_value={})
    mock_get_resolver.return_value = mock_resolver

    # Create mock game objects
    guild = GuildConfiguration(guild_id="test-guild")
    guild.id = "1"

    channel = ChannelConfiguration(guild_id="1", channel_id="test-channel", is_active=True)
    channel.id = "1"
    channel.channel_name = "test"

    host = User(discord_id="host-123")
    host.id = "1"

    # Midnight UTC test case (the original bug)
    game = GameSession(
        title="Test Game",
        description="Test",
        scheduled_at=datetime(2025, 11, 27, 0, 15, 0),  # Naive UTC
        max_players=5,
        min_players=1,
        guild_id="1",
        channel_id="1",
        host_id="1",
        status="scheduled",
    )
    game.id = "1"
    game.guild = guild
    game.channel = channel
    game.host = host
    game.participants = []
    game.created_at = datetime(2025, 11, 26, 10, 0, 0)
    game.updated_at = datetime(2025, 11, 26, 10, 0, 0)

    from services.api.routes.games import _build_game_response

    response = await _build_game_response(game)

    # Verify ISO format has 'Z' suffix
    assert response.scheduled_at.endswith("Z")
    assert response.scheduled_at == "2025-11-27T00:15:00Z"

    # Verify the ISO timestamp can be correctly converted to Unix timestamp
    parsed_dt = datetime.fromisoformat(response.scheduled_at.replace("Z", "+00:00"))
    computed_unix = int(parsed_dt.timestamp())
    expected_unix = int(datetime(2025, 11, 27, 0, 15, 0, tzinfo=UTC).timestamp())
    assert computed_unix == expected_unix


@pytest.mark.asyncio
@patch("services.api.services.display_names.get_display_name_resolver")
async def test_created_updated_have_utc_marker(mock_get_resolver):
    """
    Test that created_at and updated_at include 'Z' suffix.
    """
    # Mock display name resolver to avoid Discord API calls
    mock_resolver = AsyncMock()
    mock_resolver.resolve_display_names = AsyncMock(return_value={})
    mock_get_resolver.return_value = mock_resolver

    guild = GuildConfiguration(guild_id="test-guild")
    guild.id = "1"

    channel = ChannelConfiguration(
        guild_id="1", channel_id="test-channel", channel_name="test", is_active=True
    )
    channel.id = "1"

    host = User(discord_id="host-123")
    host.id = "1"

    game = GameSession(
        title="Test Game",
        description="Test",
        scheduled_at=datetime(2025, 12, 1, 18, 0, 0),
        max_players=8,
        min_players=2,
        guild_id="1",
        channel_id="1",
        host_id="1",
        status="scheduled",
    )
    game.id = "1"
    game.guild = guild
    game.channel = channel
    game.host = host
    game.participants = []
    game.created_at = datetime(2025, 11, 26, 10, 0, 0)
    game.updated_at = datetime(2025, 11, 26, 11, 0, 0)

    from services.api.routes.games import _build_game_response

    response = await _build_game_response(game)

    assert response.created_at.endswith("Z")
    assert response.updated_at.endswith("Z")


@pytest.mark.asyncio
@patch("services.api.services.display_names.get_display_name_resolver")
async def test_midnight_utc_not_offset(mock_get_resolver):
    """

    Critical test: Verify midnight UTC is not incorrectly offset.

    Bug: Naive datetime at 00:15 UTC was being interpreted as local time,
    resulting in 8-hour offset (displayed as 08:15 instead of 00:15).

    """
    # Mock display name resolver to avoid Discord API calls
    mock_resolver = AsyncMock()
    mock_resolver.resolve_display_names = AsyncMock(return_value={})
    mock_get_resolver.return_value = mock_resolver

    guild = GuildConfiguration(guild_id="test-guild")
    guild.id = "1"

    channel = ChannelConfiguration(
        guild_id="1", channel_id="test-channel", channel_name="test", is_active=True
    )
    channel.id = "1"

    host = User(discord_id="host-123")
    host.id = "1"

    midnight_utc = datetime(2025, 11, 27, 0, 15, 0)
    game = GameSession(
        title="Midnight Game",
        description="Test at midnight",
        scheduled_at=midnight_utc,
        max_players=4,
        min_players=1,
        guild_id="1",
        channel_id="1",
        host_id="1",
        status="scheduled",
    )
    game.id = "1"
    game.guild = guild
    game.channel = channel
    game.host = host
    game.participants = []
    game.created_at = datetime(2025, 11, 26, 10, 0, 0)
    game.updated_at = datetime(2025, 11, 26, 10, 0, 0)

    from services.api.routes.games import _build_game_response

    response = await _build_game_response(game)

    # Verify ISO format
    assert response.scheduled_at == "2025-11-27T00:15:00Z"

    # Verify the ISO timestamp represents correct UTC time
    parsed_dt = datetime.fromisoformat(response.scheduled_at.replace("Z", "+00:00"))
    assert parsed_dt.hour == 0  # Should be midnight, not 8 AM
    assert parsed_dt.minute == 15

    # Verify Unix timestamp computation is correct
    computed_unix = int(parsed_dt.timestamp())
    expected_unix = int(datetime(2025, 11, 27, 0, 15, 0, tzinfo=UTC).timestamp())
    assert computed_unix == expected_unix


@pytest.mark.asyncio
@patch("services.api.services.display_names.get_display_name_resolver")
async def test_various_times_consistent(mock_get_resolver):
    """
    Test that various times are serialized consistently.
    """
    # Mock display name resolver to avoid Discord API calls
    mock_resolver = AsyncMock()
    mock_resolver.resolve_display_names = AsyncMock(return_value={})
    mock_get_resolver.return_value = mock_resolver

    guild = GuildConfiguration(guild_id="test-guild")
    guild.id = "1"

    channel = ChannelConfiguration(
        guild_id="1", channel_id="test-channel", channel_name="test", is_active=True
    )
    channel.id = "1"

    host = User(discord_id="host-123")
    host.id = "1"

    test_times = [
        (0, 0, 0, "00:00:00"),  # Midnight
        (6, 30, 0, "06:30:00"),  # Early morning
        (12, 0, 0, "12:00:00"),  # Noon
        (18, 45, 0, "18:45:00"),  # Evening
        (23, 59, 59, "23:59:59"),  # End of day
    ]

    from services.api.routes.games import _build_game_response

    for hour, minute, second, time_str in test_times:
        scheduled_time = datetime(2025, 11, 27, hour, minute, second)
        game = GameSession(
            title=f"Game at {time_str}",
            description=f"Test at {time_str}",
            scheduled_at=scheduled_time,
            max_players=5,
            min_players=1,
            guild_id="1",
            channel_id="1",
            host_id="1",
            status="scheduled",
        )
        game.id = "1"
        game.guild = guild
        game.channel = channel
        game.host = host
        game.participants = []
        game.created_at = datetime(2025, 11, 26, 10, 0, 0)
        game.updated_at = datetime(2025, 11, 26, 10, 0, 0)

        response = await _build_game_response(game)

        # Verify ISO format
        expected_iso = f"2025-11-27T{time_str}Z"
        assert response.scheduled_at == expected_iso

        # Verify 'Z' suffix
        assert response.scheduled_at.endswith("Z")

        # Verify ISO timestamp can be converted to correct Unix timestamp
        parsed_dt = datetime.fromisoformat(response.scheduled_at.replace("Z", "+00:00"))
        computed_unix = int(parsed_dt.timestamp())
        expected_unix = int(datetime(2025, 11, 27, hour, minute, second, tzinfo=UTC).timestamp())
        assert computed_unix == expected_unix
