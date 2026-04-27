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


"""Tests for guild_service.refresh_guild_channels function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.services.guild_service import refresh_guild_channels
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


@pytest.fixture
def mock_guild() -> GuildConfiguration:
    """Create mock guild configuration."""
    guild = MagicMock(spec=GuildConfiguration)
    guild.id = "test-guild-uuid"
    guild.guild_id = "123456789"
    guild.guild_name = "Test Guild"
    return guild


@pytest.fixture
def mock_channels() -> list[ChannelConfiguration]:
    """Create mock channel configurations."""
    channels = []

    channel1 = MagicMock(spec=ChannelConfiguration)
    channel1.id = "channel-uuid-1"
    channel1.channel_id = "111111111"
    channel1.guild_id = "test-guild-uuid"
    channel1.is_active = True
    channels.append(channel1)

    channel2 = MagicMock(spec=ChannelConfiguration)
    channel2.id = "channel-uuid-2"
    channel2.channel_id = "222222222"
    channel2.guild_id = "test-guild-uuid"
    channel2.is_active = True
    channels.append(channel2)

    channel3 = MagicMock(spec=ChannelConfiguration)
    channel3.id = "channel-uuid-3"
    channel3.channel_id = "333333333"
    channel3.guild_id = "test-guild-uuid"
    channel3.is_active = False
    channels.append(channel3)

    return channels


@pytest.mark.asyncio
async def test_refresh_creates_new_channels(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
    mock_channels: list[ChannelConfiguration],
) -> None:
    """Test that refresh creates new channels from Discord."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
        {"id": "222222222", "type": 0, "name": "announcements"},
        {"id": "444444444", "type": 0, "name": "new-channel"},
    ]

    # Mock guild query - Return a fully configured result
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_channels)
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query
    new_channel = MagicMock(spec=ChannelConfiguration)
    new_channel.id = "channel-uuid-4"
    new_channel.channel_id = "444444444"
    new_channel.is_active = True

    all_channels = [*mock_channels, new_channel]
    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=all_channels)
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    # Configure AsyncMock to return these results in sequence
    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with (
        patch("services.api.services.guild_service.get_discord_client") as mock_get_client,
        patch(
            "services.api.services.guild_service.guild_queries.create_channel_config"
        ) as mock_create,
    ):
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client
        mock_create.return_value = new_channel

        result = await refresh_guild_channels(mock_db_unit, mock_guild.id)

    # Verify Discord client was called
    mock_get_client.assert_called_once_with()
    mock_client.get_guild_channels.assert_called_once_with(mock_guild.guild_id)

    # Verify new channel was created
    mock_create.assert_called_once_with(mock_db_unit, mock_guild.id, "444444444", is_active=True)

    # Verify result includes channels
    assert isinstance(result, list)
    assert len(result) == 4


@pytest.mark.asyncio
async def test_refresh_marks_deleted_channels_inactive(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
    mock_channels: list[ChannelConfiguration],
) -> None:
    """Test that refresh marks deleted channels as inactive."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
    ]

    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_channels)
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query
    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=mock_channels)
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with patch("services.api.services.guild_service.get_discord_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client

        await refresh_guild_channels(mock_db_unit, mock_guild.id)

    # Verify channel 222222222 was marked inactive
    mock_get_client.assert_called_once_with()
    assert mock_channels[1].is_active is False


@pytest.mark.asyncio
async def test_refresh_reactivates_channels(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
    mock_channels: list[ChannelConfiguration],
) -> None:
    """Test that refresh reactivates previously inactive channels."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
        {"id": "222222222", "type": 0, "name": "announcements"},
        {"id": "333333333", "type": 0, "name": "reactivated"},
    ]

    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_channels)
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query
    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=mock_channels)
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with patch("services.api.services.guild_service.get_discord_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client

        await refresh_guild_channels(mock_db_unit, mock_guild.id)

    # Verify channel 333333333 was reactivated
    mock_get_client.assert_called_once_with()
    assert mock_channels[2].is_active is True


@pytest.mark.asyncio
async def test_refresh_filters_non_text_channels(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
    mock_channels: list[ChannelConfiguration],
) -> None:
    """Test that refresh only processes text channels (type 0)."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
        {"id": "555555555", "type": 2, "name": "voice-channel"},
        {"id": "666666666", "type": 4, "name": "category"},
    ]

    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_channels)
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query
    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=mock_channels)
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with (
        patch("services.api.services.guild_service.get_discord_client") as mock_get_client,
        patch(
            "services.api.services.guild_service.guild_queries.create_channel_config"
        ) as mock_create,
    ):
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client

        await refresh_guild_channels(mock_db_unit, mock_guild.id)

    # Verify only text channel 111111111 was in existing channels, no new channels created
    # Voice and category channels should not create new channels
    mock_get_client.assert_called_once_with()
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_returns_channel_list(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
    mock_channels: list[ChannelConfiguration],
) -> None:
    """Test that refresh returns updated channel list."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
        {"id": "222222222", "type": 0, "name": "announcements"},
    ]

    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_channels)
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query
    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=mock_channels[:2])
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with patch("services.api.services.guild_service.get_discord_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client

        result = await refresh_guild_channels(mock_db_unit, mock_guild.id)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ch, dict) for ch in result)
    assert all("id" in ch and "channel_id" in ch and "is_active" in ch for ch in result)
    mock_get_client.assert_called_once_with()


@pytest.mark.asyncio
async def test_refresh_handles_nonexistent_guild(
    mock_db_unit: AsyncMock,
) -> None:
    """Test that refresh returns empty list for nonexistent guild."""
    # Mock guild query returning None
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db_unit.execute = AsyncMock(return_value=guild_result)

    result = await refresh_guild_channels(mock_db_unit, "nonexistent-guild-id")

    assert result == []


@pytest.mark.asyncio
async def test_refresh_handles_discord_api_error(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
) -> None:
    """Test that refresh propagates Discord API errors."""
    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    mock_db_unit.execute = AsyncMock(return_value=guild_result)

    with patch("services.api.services.guild_service.get_discord_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_guild_channels.side_effect = Exception("Discord API error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="Discord API error"):
            await refresh_guild_channels(mock_db_unit, mock_guild.id)
        mock_get_client.assert_called_once_with()


@pytest.mark.asyncio
async def test_refresh_handles_guild_with_no_channels(
    mock_db_unit: AsyncMock,
    mock_guild: GuildConfiguration,
) -> None:
    """Test that refresh handles guild with no existing channels."""
    discord_channels = [
        {"id": "111111111", "type": 0, "name": "general"},
        {"id": "222222222", "type": 0, "name": "announcements"},
    ]

    # Mock guild query
    guild_result = MagicMock()
    guild_result.scalar_one_or_none = MagicMock(return_value=mock_guild)

    # Mock existing channels query - empty list
    existing_channels_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[])
    existing_channels_result.scalars = MagicMock(return_value=scalars_mock)

    # Mock final channels query - new channels created
    new_channel1 = MagicMock(spec=ChannelConfiguration)
    new_channel1.id = "ch-1"
    new_channel1.channel_id = "111111111"
    new_channel1.is_active = True

    new_channel2 = MagicMock(spec=ChannelConfiguration)
    new_channel2.id = "ch-2"
    new_channel2.channel_id = "222222222"
    new_channel2.is_active = True

    all_channels_result = MagicMock()
    all_channels_scalars_mock = MagicMock()
    all_channels_scalars_mock.all = MagicMock(return_value=[new_channel1, new_channel2])
    all_channels_result.scalars = MagicMock(return_value=all_channels_scalars_mock)

    mock_db_unit.execute = AsyncMock(
        side_effect=[guild_result, existing_channels_result, all_channels_result]
    )

    with (
        patch("services.api.services.guild_service.get_discord_client") as mock_get_client,
        patch(
            "services.api.services.guild_service.guild_queries.create_channel_config"
        ) as mock_create,
    ):
        mock_client = AsyncMock()
        mock_client.get_guild_channels.return_value = discord_channels
        mock_get_client.return_value = mock_client
        mock_create.side_effect = [new_channel1, new_channel2]

        result = await refresh_guild_channels(mock_db_unit, mock_guild.id)

    # Verify both channels were created
    mock_get_client.assert_called_once_with()
    assert mock_create.call_count == 2
    assert len(result) == 2
