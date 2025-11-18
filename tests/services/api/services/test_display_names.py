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


"""Unit tests for display name resolution service."""

from unittest.mock import AsyncMock

import pytest

from services.api.auth import discord_client
from services.api.services import display_names
from shared.cache import client as cache_client


@pytest.fixture
def mock_discord_api():
    """Mock Discord API client."""
    mock = AsyncMock(spec=discord_client.DiscordAPIClient)
    return mock


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    mock = AsyncMock(spec=cache_client.RedisClient)
    return mock


@pytest.fixture
def resolver(mock_discord_api, mock_cache):
    """Display name resolver with mocked dependencies."""
    return display_names.DisplayNameResolver(mock_discord_api, mock_cache)


@pytest.mark.asyncio
async def test_resolve_display_names_from_cache(resolver, mock_cache):
    """Test resolving display names from cache."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache hits
    mock_cache.get = AsyncMock(side_effect=["CachedName1", "CachedName2"])

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "CachedName1", "user2": "CachedName2"}
    assert mock_cache.get.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_from_api(resolver, mock_discord_api, mock_cache):
    """Test resolving display names from Discord API when not cached."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache misses
    mock_cache.get = AsyncMock(return_value=None)

    # Mock Discord API response
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {"id": "user1", "username": "username1", "global_name": "GlobalName1"},
                "nick": "GuildNick1",
            },
            {
                "user": {"id": "user2", "username": "username2", "global_name": "GlobalName2"},
                "nick": None,
            },
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GuildNick1", "user2": "GlobalName2"}
    assert mock_cache.set.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_fallback_to_global_name(
    resolver, mock_discord_api, mock_cache
):
    """Test fallback to global_name when nick is not set."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {"id": "user1", "username": "username1", "global_name": "GlobalName1"},
                "nick": None,
            }
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GlobalName1"}


@pytest.mark.asyncio
async def test_resolve_display_names_fallback_to_username(resolver, mock_discord_api, mock_cache):
    """Test fallback to username when nick and global_name are not set."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {"user": {"id": "user1", "username": "username1", "global_name": None}, "nick": None}
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "username1"}


@pytest.mark.asyncio
async def test_resolve_display_names_user_not_found(resolver, mock_discord_api, mock_cache):
    """Test handling of users who left the guild."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(return_value=None)
    # Only user1 is returned (user2 left guild)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {"id": "user1", "username": "username1", "global_name": "GlobalName1"},
                "nick": "GuildNick1",
            }
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GuildNick1", "user2": "Unknown User"}


@pytest.mark.asyncio
async def test_resolve_display_names_api_error(resolver, mock_discord_api, mock_cache):
    """Test fallback on Discord API error."""
    guild_id = "123456789"
    user_ids = ["user1234"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        side_effect=discord_client.DiscordAPIError(500, "API Error")
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    # Should return fallback format: User#1234
    assert result == {"user1234": "User#1234"}


@pytest.mark.asyncio
async def test_resolve_display_names_mixed_cache_and_api(resolver, mock_discord_api, mock_cache):
    """Test resolving with some cached and some uncached names."""
    guild_id = "123456789"
    user_ids = ["user1", "user2", "user3"]

    # Mock cache: user1 cached, user2 and user3 not cached
    async def cache_get(key):
        if "user1" in key:
            return "CachedName1"
        return None

    mock_cache.get = AsyncMock(side_effect=cache_get)

    # Mock API response for uncached users
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {"id": "user2", "username": "username2", "global_name": "GlobalName2"},
                "nick": None,
            },
            {"user": {"id": "user3", "username": "username3", "global_name": None}, "nick": None},
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "CachedName1", "user2": "GlobalName2", "user3": "username3"}


@pytest.mark.asyncio
async def test_resolve_single(resolver, mock_cache):
    """Test resolving single user display name."""
    guild_id = "123456789"
    user_id = "user1"

    mock_cache.get = AsyncMock(return_value="CachedName1")

    result = await resolver.resolve_single(guild_id, user_id)

    assert result == "CachedName1"


@pytest.mark.asyncio
async def test_resolve_single_user_not_found(resolver, mock_discord_api, mock_cache):
    """Test resolving single user that doesn't exist."""
    guild_id = "123456789"
    user_id = "user1"

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(return_value=[])

    result = await resolver.resolve_single(guild_id, user_id)

    assert result == "Unknown User"
