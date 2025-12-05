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


"""Tests for guild configuration service."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.api.services import guild_service
from shared.models.guild import GuildConfiguration


@pytest.mark.asyncio
async def test_create_guild_config():
    """Test creating a new guild configuration."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_discord_id = "123456789012345678"
    settings = {
        "bot_manager_role_ids": ["role1", "role2"],
        "require_host_role": True,
    }

    await guild_service.create_guild_config(mock_db, guild_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()

    added_guild = mock_db.add.call_args[0][0]
    assert isinstance(added_guild, GuildConfiguration)
    assert added_guild.guild_id == guild_discord_id
    assert added_guild.bot_manager_role_ids == ["role1", "role2"]
    assert added_guild.require_host_role is True


@pytest.mark.asyncio
async def test_update_guild_config():
    """Test updating a guild configuration."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role1", "role2", "role3"],
        "require_host_role": True,
    }

    await guild_service.update_guild_config(mock_db, guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role1", "role2", "role3"]
    assert guild_config.require_host_role is True
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_guild_config_ignores_none_values():
    """Test that update ignores None values."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role2"],
        "require_host_role": None,  # Will be set to None
    }

    await guild_service.update_guild_config(mock_db, guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role2"]
    assert guild_config.require_host_role is None  # Updated to None
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
