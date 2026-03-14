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
    mock_db.flush = AsyncMock()

    guild_id = "guild-uuid-123"
    channel_discord_id = "987654321098765432"
    settings = {
        "is_active": True,
    }

    await channel_service.create_channel_config(mock_db, guild_id, channel_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()

    added_channel = mock_db.add.call_args[0][0]
    assert isinstance(added_channel, ChannelConfiguration)
    assert added_channel.guild_id == guild_id
    assert added_channel.channel_id == channel_discord_id
    assert added_channel.is_active is True


@pytest.mark.asyncio
async def test_update_channel_config():
    """Test updating a channel configuration."""
    channel_config = ChannelConfiguration(
        guild_id="guild-uuid-123",
        channel_id="987654321098765432",
        is_active=False,
    )

    updates = {
        "is_active": True,
    }

    await channel_service.update_channel_config(channel_config, **updates)

    assert channel_config.is_active is True


@pytest.mark.asyncio
async def test_update_channel_config_ignores_none_values():
    """Test that update ignores None values."""
    channel_config = ChannelConfiguration(
        guild_id="guild-uuid-123",
        channel_id="987654321098765432",
        is_active=True,
    )

    updates = {
        "is_active": False,
    }

    await channel_service.update_channel_config(channel_config, **updates)

    assert channel_config.is_active is False
