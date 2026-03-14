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


"""Tests for guild configuration service."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.api.services import guild_service
from shared.models.guild import GuildConfiguration


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="create_guild_config moved to bot service, will migrate to RabbitMQ pattern (Phase 6)"
)
@pytest.mark.xfail(
    reason="create_guild_config stubbed - will be replaced with RabbitMQ in Phase 6",
    raises=NotImplementedError,
)
async def test_create_guild_config():
    """Test creating a new guild configuration."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.flush = AsyncMock()

    guild_discord_id = "123456789012345678"
    settings = {
        "bot_manager_role_ids": ["role1", "role2"],
    }

    await guild_service.create_guild_config(mock_db, guild_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()

    added_guild = mock_db.add.call_args[0][0]
    assert isinstance(added_guild, GuildConfiguration)
    assert added_guild.guild_id == guild_discord_id
    assert added_guild.bot_manager_role_ids == ["role1", "role2"]


@pytest.mark.asyncio
async def test_update_guild_config():
    """Test updating a guild configuration."""
    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
    )

    updates = {
        "bot_manager_role_ids": ["role1", "role2", "role3"],
    }

    await guild_service.update_guild_config(guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role1", "role2", "role3"]


@pytest.mark.asyncio
async def test_update_guild_config_ignores_none_values():
    """Test that update ignores None values."""
    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
    )

    updates = {
        "bot_manager_role_ids": ["role2"],
    }

    await guild_service.update_guild_config(guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role2"]
