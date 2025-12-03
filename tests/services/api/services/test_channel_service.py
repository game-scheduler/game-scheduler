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


"""Tests for channel configuration service."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.api.services import channel_service
from shared.models.channel import ChannelConfiguration


@pytest.mark.asyncio
async def test_create_channel_config():
    """Test creating a new channel configuration."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_id = "guild-uuid-123"
    channel_discord_id = "987654321098765432"
    settings = {
        "is_active": True,
    }

    await channel_service.create_channel_config(mock_db, guild_id, channel_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()

    added_channel = mock_db.add.call_args[0][0]
    assert isinstance(added_channel, ChannelConfiguration)
    assert added_channel.guild_id == guild_id
    assert added_channel.channel_id == channel_discord_id
    assert added_channel.is_active is True


@pytest.mark.asyncio
async def test_update_channel_config():
    """Test updating a channel configuration."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    channel_config = ChannelConfiguration(
        guild_id="guild-uuid-123",
        channel_id="987654321098765432",
        is_active=False,
    )

    updates = {
        "is_active": True,
    }

    await channel_service.update_channel_config(mock_db, channel_config, **updates)

    assert channel_config.is_active is True
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_channel_config_ignores_none_values():
    """Test that update ignores None values."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    channel_config = ChannelConfiguration(
        guild_id="guild-uuid-123",
        channel_id="987654321098765432",
        is_active=True,
    )

    updates = {
        "is_active": False,
    }

    await channel_service.update_channel_config(mock_db, channel_config, **updates)

    assert channel_config.is_active is False
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
