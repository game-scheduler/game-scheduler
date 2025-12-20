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


"""Integration tests for avatar data flow.

Tests verify the complete flow from Discord API through backend to frontend/bot:
1. Discord API returns avatar data
2. DisplayNameResolver extracts and constructs URLs correctly
3. API responses include avatar URLs
4. Cache stores and retrieves avatar data
5. Avatar URL priority (guild > user > null) works end-to-end
"""

import json
from unittest.mock import AsyncMock

import pytest

from services.api.services.display_names import DisplayNameResolver
from shared.cache.keys import CacheKeys


@pytest.fixture
def cache_keys():
    """Get cache keys instance."""
    return CacheKeys()


@pytest.fixture
def guild_id():
    """Get test guild ID."""
    return "123456789012345678"


@pytest.fixture
def user_id():
    """Get test user ID."""
    return "987654321098765432"


@pytest.fixture
def mock_discord_client():
    """Create mock Discord client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_cache_client():
    """Create mock cache client."""
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = None
    cache.setex.return_value = None
    return cache


class TestAvatarDataFlow:
    """Test complete avatar data flow from Discord API to frontend/bot."""

    @pytest.mark.asyncio
    async def test_discord_api_returns_avatar_data(self, mock_discord_client, guild_id, user_id):
        """Test that Discord API call returns avatar data."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "nick": "TestNick",
                "avatar": "guild_avatar_hash",
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        assert user_id in result
        assert "display_name" in result[user_id]
        assert "avatar_url" in result[user_id]
        assert result[user_id]["display_name"] == "TestNick"
        assert "guild_avatar_hash" in result[user_id]["avatar_url"]

    @pytest.mark.asyncio
    async def test_resolver_constructs_guild_avatar_url(
        self, mock_discord_client, guild_id, user_id
    ):
        """Test DisplayNameResolver constructs guild avatar URL with priority."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "nick": "TestNick",
                "avatar": "guild_avatar_hash",
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        expected_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/guild_avatar_hash.png?size=64"
        assert result[user_id]["avatar_url"] == expected_url

    @pytest.mark.asyncio
    async def test_resolver_constructs_user_avatar_url(
        self, mock_discord_client, guild_id, user_id
    ):
        """Test DisplayNameResolver constructs user avatar URL when no guild avatar."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "nick": "TestNick",
                "avatar": None,
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        expected_url = f"https://cdn.discordapp.com/avatars/{user_id}/user_avatar_hash.png?size=64"
        assert result[user_id]["avatar_url"] == expected_url

    @pytest.mark.asyncio
    async def test_resolver_returns_none_when_no_avatar(
        self, mock_discord_client, guild_id, user_id
    ):
        """Test DisplayNameResolver returns None when user has no avatar."""
        mock_discord_client.get_guild_member.return_value = {
            "user": {"id": user_id, "username": "TestUser", "avatar": None},
            "nick": "TestNick",
            "avatar": None,
        }

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        assert result[user_id]["avatar_url"] is None

    @pytest.mark.asyncio
    async def test_cache_stores_avatar_data(
        self, mock_discord_client, mock_cache_client, cache_keys, guild_id, user_id
    ):
        """Test cache stores avatar URLs alongside display names."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "nick": "TestNick",
                "avatar": "guild_avatar_hash",
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, mock_cache_client)
        await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        cache_key = cache_keys.display_name_avatar(user_id, guild_id)
        mock_cache_client.set.assert_called_once()
        call_args = mock_cache_client.set.call_args

        assert call_args[0][0] == cache_key
        cached_data = json.loads(call_args[0][1])
        assert call_args[1]["ttl"] == 300
        assert cached_data["display_name"] == "TestNick"
        assert "guild_avatar_hash" in cached_data["avatar_url"]

    @pytest.mark.asyncio
    async def test_cache_retrieves_avatar_data(
        self, mock_discord_client, mock_cache_client, cache_keys, guild_id, user_id
    ):
        """Test cache retrieval returns avatar URLs."""
        cache_key = cache_keys.display_name_avatar(user_id, guild_id)
        cached_data = {
            "display_name": "CachedNick",
            "avatar_url": f"https://cdn.discordapp.com/avatars/{user_id}/cached_hash.png?size=64",
        }
        mock_cache_client.get.return_value = json.dumps(cached_data)

        resolver = DisplayNameResolver(mock_discord_client, mock_cache_client)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        mock_cache_client.get.assert_called_once_with(cache_key)
        mock_discord_client.get_guild_member.assert_not_called()
        assert result[user_id]["display_name"] == "CachedNick"
        assert result[user_id]["avatar_url"] == cached_data["avatar_url"]

    @pytest.mark.asyncio
    async def test_avatar_priority_guild_over_user(self, mock_discord_client, guild_id, user_id):
        """Test avatar URL priority: guild avatar takes precedence over user avatar."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "avatar": "guild_avatar_hash",
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        assert result[user_id]["avatar_url"] is not None
        assert "guild_avatar_hash" in result[user_id]["avatar_url"]
        assert "user_avatar_hash" not in result[user_id]["avatar_url"]

    @pytest.mark.asyncio
    async def test_avatar_priority_user_over_none(self, mock_discord_client, guild_id, user_id):
        """Test avatar URL priority: user avatar used when no guild avatar."""
        mock_discord_client.get_guild_members_batch.return_value = [
            {
                "user": {
                    "id": user_id,
                    "username": "TestUser",
                    "avatar": "user_avatar_hash",
                },
                "avatar": None,
            }
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        assert result[user_id]["avatar_url"] is not None
        assert "user_avatar_hash" in result[user_id]["avatar_url"]

    @pytest.mark.asyncio
    async def test_avatar_priority_none_when_both_missing(
        self, mock_discord_client, guild_id, user_id
    ):
        """Test avatar URL priority: None returned when both guild and user avatars missing."""
        mock_discord_client.get_guild_member.return_value = {
            "user": {"id": user_id, "username": "TestUser", "avatar": None},
            "avatar": None,
        }

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, [user_id])

        assert result[user_id]["avatar_url"] is None

    @pytest.mark.asyncio
    async def test_batch_resolution_all_priority_types(self, mock_discord_client, guild_id):
        """Test batch resolution handles all avatar priority types correctly."""
        user_ids = ["user1", "user2", "user3"]

        async def mock_get_member(guild_id_arg, user_id):
            members = {
                "user1": {
                    "user": {"id": "user1", "username": "User1", "avatar": "hash1"},
                    "avatar": "guild_hash1",
                },
                "user2": {
                    "user": {"id": "user2", "username": "User2", "avatar": "hash2"},
                    "avatar": None,
                },
                "user3": {
                    "user": {"id": "user3", "username": "User3", "avatar": None},
                    "avatar": None,
                },
            }
            return members[user_id]

        mock_discord_client.get_guild_members_batch.return_value = [
            await mock_get_member(guild_id, uid) for uid in user_ids
        ]

        resolver = DisplayNameResolver(mock_discord_client, None)
        result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

        assert "guild_hash1" in result["user1"]["avatar_url"]
        assert "hash2" in result["user2"]["avatar_url"]
        assert result["user3"]["avatar_url"] is None
