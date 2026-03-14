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


"""Unit tests for display name resolution service."""

import json
from unittest.mock import AsyncMock

import pytest

from services.api.services import display_names
from shared.cache import client as cache_client
from shared.discord import client as discord_client


@pytest.fixture
def mock_discord_api():
    """Mock Discord API client."""
    return AsyncMock(spec=discord_client.DiscordAPIClient)


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    return AsyncMock(spec=cache_client.RedisClient)


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
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            },
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": "GlobalName2",
                },
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
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
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
            {
                "user": {"id": "user1", "username": "username1", "global_name": None},
                "nick": None,
            }
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
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
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
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": "GlobalName2",
                },
                "nick": None,
            },
            {
                "user": {"id": "user3", "username": "username3", "global_name": None},
                "nick": None,
            },
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {
        "user1": "CachedName1",
        "user2": "GlobalName2",
        "user3": "username3",
    }


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


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_cache(resolver, mock_cache):
    """Test resolving display names and avatars from cache."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache hits with JSON data
    mock_cache.get = AsyncMock(
        side_effect=[
            json.dumps({
                "display_name": "CachedName1",
                "avatar_url": "https://cdn.example.com/avatar1.png",
            }),
            json.dumps({"display_name": "CachedName2", "avatar_url": None}),
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {
        "user1": {
            "display_name": "CachedName1",
            "avatar_url": "https://cdn.example.com/avatar1.png",
        },
        "user2": {"display_name": "CachedName2", "avatar_url": None},
    }
    assert mock_cache.get.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_api_with_guild_avatar(
    resolver, mock_discord_api, mock_cache
):
    """Test resolving display names and avatars from Discord API with guild-specific avatar."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                    "avatar": "user_avatar_hash",
                },
                "nick": "GuildNick1",
                "avatar": "guild_avatar_hash",
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    # Guild avatar should take priority
    expected_url = "https://cdn.discordapp.com/guilds/123456789/users/user1/avatars/guild_avatar_hash.png?size=64"
    assert result == {"user1": {"display_name": "GuildNick1", "avatar_url": expected_url}}
    assert mock_cache.set.call_count == 1


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_api_with_user_avatar(
    resolver, mock_discord_api, mock_cache
):
    """Test resolving display names and avatars from Discord API with user avatar only."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                    "avatar": "user_avatar_hash",
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    # User avatar should be used when no guild avatar
    expected_url = "https://cdn.discordapp.com/avatars/user1/user_avatar_hash.png?size=64"
    assert result == {"user1": {"display_name": "GlobalName1", "avatar_url": expected_url}}


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_no_avatar(resolver, mock_discord_api, mock_cache):
    """Test resolving display names and avatars when user has no avatar."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": None,
                    "avatar": None,
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {"user1": {"display_name": "username1", "avatar_url": None}}


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_api_error(resolver, mock_discord_api, mock_cache):
    """Test fallback on Discord API error for avatar resolution."""
    guild_id = "123456789"
    user_ids = ["user1234"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        side_effect=discord_client.DiscordAPIError(500, "API Error")
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {"user1234": {"display_name": "User#1234", "avatar_url": None}}


@pytest.mark.asyncio
async def test_build_avatar_url_guild_priority(resolver):
    """Test avatar URL construction with guild avatar priority."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar="guild_hash",
        user_avatar="user_hash",
    )

    assert (
        url
        == "https://cdn.discordapp.com/guilds/guild456/users/user123/avatars/guild_hash.png?size=64"
    )


@pytest.mark.asyncio
async def test_build_avatar_url_user_fallback(resolver):
    """Test avatar URL construction with user avatar fallback."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar=None,
        user_avatar="user_hash",
    )

    assert url == "https://cdn.discordapp.com/avatars/user123/user_hash.png?size=64"


@pytest.mark.asyncio
async def test_build_avatar_url_no_avatar(resolver):
    """Test avatar URL construction with no avatar."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar=None,
        user_avatar=None,
    )

    assert url is None


@pytest.mark.asyncio
async def test_check_cache_for_users_all_cached(resolver, mock_cache):
    """Test checking cache when all users are cached."""
    guild_id = "guild123"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(
        side_effect=[
            json.dumps({"display_name": "Name1", "avatar_url": "url1"}),
            json.dumps({"display_name": "Name2", "avatar_url": "url2"}),
        ]
    )

    cached_results, uncached_ids = await resolver._check_cache_for_users(guild_id, user_ids)

    assert cached_results == {
        "user1": {"display_name": "Name1", "avatar_url": "url1"},
        "user2": {"display_name": "Name2", "avatar_url": "url2"},
    }
    assert uncached_ids == []


@pytest.mark.asyncio
async def test_check_cache_for_users_partial_cached(resolver, mock_cache):
    """Test checking cache with some users cached and some not."""
    guild_id = "guild123"
    user_ids = ["user1", "user2", "user3"]

    mock_cache.get = AsyncMock(
        side_effect=[
            json.dumps({"display_name": "Name1", "avatar_url": "url1"}),
            None,
            json.dumps({"display_name": "Name3", "avatar_url": "url3"}),
        ]
    )

    cached_results, uncached_ids = await resolver._check_cache_for_users(guild_id, user_ids)

    assert cached_results == {
        "user1": {"display_name": "Name1", "avatar_url": "url1"},
        "user3": {"display_name": "Name3", "avatar_url": "url3"},
    }
    assert uncached_ids == ["user2"]


@pytest.mark.asyncio
async def test_check_cache_for_users_none_cached(resolver, mock_cache):
    """Test checking cache when no users are cached."""
    guild_id = "guild123"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(return_value=None)

    cached_results, uncached_ids = await resolver._check_cache_for_users(guild_id, user_ids)

    assert cached_results == {}
    assert uncached_ids == ["user1", "user2"]


@pytest.mark.asyncio
async def test_check_cache_for_users_invalid_json(resolver, mock_cache):
    """Test checking cache handles invalid JSON gracefully."""
    guild_id = "guild123"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value="invalid json {")

    cached_results, uncached_ids = await resolver._check_cache_for_users(guild_id, user_ids)

    assert cached_results == {}
    assert uncached_ids == ["user1"]


@pytest.mark.asyncio
async def test_check_cache_for_users_no_cache_client(mock_discord_api):
    """Test checking cache when cache client is None."""
    resolver_no_cache = display_names.DisplayNameResolver(mock_discord_api, None)
    guild_id = "guild123"
    user_ids = ["user1", "user2"]

    cached_results, uncached_ids = await resolver_no_cache._check_cache_for_users(
        guild_id, user_ids
    )

    assert cached_results == {}
    assert uncached_ids == ["user1", "user2"]


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_avatars_success(
    resolver, mock_discord_api, mock_cache
):
    """Test fetching and caching display names and avatars from Discord API."""
    guild_id = "guild123"
    uncached_ids = ["user1", "user2"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "Global1",
                    "avatar": "user_avatar1",
                },
                "nick": "Nick1",
                "avatar": "member_avatar1",
            },
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": None,
                    "avatar": None,
                },
                "nick": None,
                "avatar": None,
            },
        ]
    )

    result = await resolver._fetch_and_cache_display_names_avatars(guild_id, uncached_ids)

    assert "user1" in result
    assert result["user1"]["display_name"] == "Nick1"
    assert "member_avatar1" in result["user1"]["avatar_url"]

    assert "user2" in result
    assert result["user2"]["display_name"] == "username2"
    assert result["user2"]["avatar_url"] is None

    assert mock_cache.set.call_count == 2


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_avatars_member_not_found(
    resolver, mock_discord_api, mock_cache
):
    """Test handling when some users are not found in guild."""
    guild_id = "guild123"
    uncached_ids = ["user1", "user2"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "Global1",
                    "avatar": None,
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver._fetch_and_cache_display_names_avatars(guild_id, uncached_ids)

    assert result["user1"]["display_name"] == "Global1"
    assert result["user2"]["display_name"] == "Unknown User"
    assert result["user2"]["avatar_url"] is None


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_avatars_no_cache_client(mock_discord_api):
    """Test fetching without cache client."""
    resolver_no_cache = display_names.DisplayNameResolver(mock_discord_api, None)
    guild_id = "guild123"
    uncached_ids = ["user1"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": None,
                    "avatar": None,
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver_no_cache._fetch_and_cache_display_names_avatars(guild_id, uncached_ids)

    assert result["user1"]["display_name"] == "username1"


def test_create_fallback_user_data():
    """Test creating fallback user data."""
    user_ids = ["user1234", "user5678"]

    result = display_names.DisplayNameResolver._create_fallback_user_data(user_ids)

    assert result == {
        "user1234": {"display_name": "User#1234", "avatar_url": None},
        "user5678": {"display_name": "User#5678", "avatar_url": None},
    }


def test_create_fallback_user_data_empty_list():
    """Test creating fallback user data with empty list."""
    result = display_names.DisplayNameResolver._create_fallback_user_data([])

    assert result == {}


@pytest.mark.asyncio
async def test_check_cache_for_display_names_all_cached(resolver, mock_cache):
    """Test checking cache when all user IDs are cached."""
    guild_id = "guild123"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(side_effect=["CachedName1", "CachedName2"])

    result, uncached_ids = await resolver._check_cache_for_display_names(guild_id, user_ids)

    assert result == {"user1": "CachedName1", "user2": "CachedName2"}
    assert uncached_ids == []


@pytest.mark.asyncio
async def test_check_cache_for_display_names_none_cached(resolver, mock_cache):
    """Test checking cache when no user IDs are cached."""
    guild_id = "guild123"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(return_value=None)

    result, uncached_ids = await resolver._check_cache_for_display_names(guild_id, user_ids)

    assert result == {}
    assert uncached_ids == ["user1", "user2"]


@pytest.mark.asyncio
async def test_check_cache_for_display_names_partially_cached(resolver, mock_cache):
    """Test checking cache when some user IDs are cached."""
    guild_id = "guild123"
    user_ids = ["user1", "user2", "user3"]

    async def cache_get(key):
        if "user1" in key:
            return "CachedName1"
        if "user3" in key:
            return "CachedName3"
        return None

    mock_cache.get = AsyncMock(side_effect=cache_get)

    result, uncached_ids = await resolver._check_cache_for_display_names(guild_id, user_ids)

    assert result == {"user1": "CachedName1", "user3": "CachedName3"}
    assert uncached_ids == ["user2"]


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_all_found(resolver, mock_discord_api, mock_cache):
    """Test fetching and caching when all users are found."""
    guild_id = "guild123"
    uncached_ids = ["user1", "user2"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            },
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": None,
                },
                "nick": None,
            },
        ]
    )

    result = await resolver._fetch_and_cache_display_names(guild_id, uncached_ids)

    assert result == {"user1": "GuildNick1", "user2": "username2"}
    assert mock_cache.set.call_count == 2


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_some_not_found(resolver, mock_discord_api, mock_cache):
    """Test fetching when some users are not found in guild."""
    guild_id = "guild123"
    uncached_ids = ["user1", "user2"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            }
        ]
    )

    result = await resolver._fetch_and_cache_display_names(guild_id, uncached_ids)

    assert result == {"user1": "GuildNick1", "user2": "Unknown User"}
    assert mock_cache.set.call_count == 1


@pytest.mark.asyncio
async def test_fetch_and_cache_display_names_username_priority(
    resolver, mock_discord_api, mock_cache
):
    """Test display name resolution priority: nick > global_name > username."""
    guild_id = "guild123"
    uncached_ids = ["user1", "user2", "user3"]

    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            },
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": "GlobalName2",
                },
                "nick": None,
            },
            {
                "user": {
                    "id": "user3",
                    "username": "username3",
                    "global_name": None,
                },
                "nick": None,
            },
        ]
    )

    result = await resolver._fetch_and_cache_display_names(guild_id, uncached_ids)

    assert result == {
        "user1": "GuildNick1",
        "user2": "GlobalName2",
        "user3": "username3",
    }


def test_create_fallback_display_names():
    """Test creating fallback display names."""
    uncached_ids = ["user1234", "user5678"]

    result = display_names.DisplayNameResolver._create_fallback_display_names(
        display_names.DisplayNameResolver(None, None), uncached_ids
    )

    assert result == {
        "user1234": "User#1234",
        "user5678": "User#5678",
    }


def test_create_fallback_display_names_empty_list():
    """Test creating fallback display names with empty list."""
    result = display_names.DisplayNameResolver._create_fallback_display_names(
        display_names.DisplayNameResolver(None, None), []
    )

    assert result == {}


def test_resolve_display_name_with_nickname():
    """Test resolving display name when nickname is present."""
    member = {
        "user": {
            "id": "user123",
            "username": "username",
            "global_name": "GlobalName",
        },
        "nick": "GuildNickname",
    }

    result = display_names.DisplayNameResolver._resolve_display_name(member)

    assert result == "GuildNickname"


def test_resolve_display_name_with_global_name():
    """Test resolving display name fallback to global_name."""
    member = {
        "user": {
            "id": "user123",
            "username": "username",
            "global_name": "GlobalName",
        },
        "nick": None,
    }

    result = display_names.DisplayNameResolver._resolve_display_name(member)

    assert result == "GlobalName"


def test_resolve_display_name_with_username_only():
    """Test resolving display name fallback to username."""
    member = {
        "user": {
            "id": "user123",
            "username": "username",
            "global_name": None,
        },
        "nick": None,
    }

    result = display_names.DisplayNameResolver._resolve_display_name(member)

    assert result == "username"


def test_resolve_display_name_missing_nick_field():
    """Test resolving display name when nick field is absent."""
    member = {
        "user": {
            "id": "user123",
            "username": "username",
            "global_name": "GlobalName",
        }
    }

    result = display_names.DisplayNameResolver._resolve_display_name(member)

    assert result == "GlobalName"
