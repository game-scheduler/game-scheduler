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
Role verification service for Discord users.

Provides role checking with Discord API integration and Redis caching.
"""

import logging
from typing import TYPE_CHECKING

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot import guild_projection
from services.bot.auth import cache

if TYPE_CHECKING:
    from discord import Client

logger = logging.getLogger(__name__)


class RoleChecker:
    """Service for checking user roles and permissions."""

    def __init__(self, bot: "Client", db_session: AsyncSession) -> None:
        """
        Initialize role checker.

        Args:
            bot: Discord bot client
            db_session: Database session for configuration queries
        """
        self.bot = bot
        self.db = db_session
        self.cache = cache.RoleCache()
        self.api_cache = None

    async def get_user_role_ids(
        self, user_id: str, guild_id: str, force_refresh: bool = False
    ) -> list[str]:
        """
        Get user's role IDs with caching.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            force_refresh: Skip cache and fetch from Discord API

        Returns:
            List of role IDs user has in guild
        """
        if not force_refresh:
            cached_roles = await self.cache.get_user_roles(user_id, guild_id)
            if cached_roles is not None:
                return cached_roles

        try:
            redis = await self.cache.get_redis()
            role_ids = await guild_projection.get_user_roles(guild_id, user_id, redis=redis)
            await self.cache.set_user_roles(user_id, guild_id, role_ids)
            return role_ids

        except Exception as e:
            logger.error("Error fetching user roles: %s", e)
            return []

    async def get_guild_roles(self, guild_id: str) -> list[discord.Role]:
        """
        Get all roles in guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            List of Discord role objects
        """
        try:
            guild = self.bot.get_guild(int(guild_id))

            if guild is None:
                logger.warning("Guild %s not found", guild_id)
                return []

            return list(guild.roles)

        except Exception as e:
            logger.error("Error fetching guild roles: %s", e)
            return []

    async def seed_user_roles(self, user_id: str, guild_id: str, role_ids: list[str]) -> None:
        """Populate the role cache with caller-supplied role IDs.

        Used by the bot path to warm the cache from the interaction payload,
        avoiding an extra Discord API call.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            role_ids: Role IDs to store for the user
        """
        await self.cache.set_user_roles(user_id, guild_id, role_ids)

    async def check_manage_guild_permission(self, user_id: str, guild_id: str) -> bool:
        """
        Check if user has MANAGE_GUILD permission.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            True if user has MANAGE_GUILD permission
        """
        try:
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return False

            member = guild.get_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.manage_guild

        except Exception as e:
            logger.error("Error checking MANAGE_GUILD permission: %s", e)
            return False

    async def check_manage_channels_permission(self, user_id: str, guild_id: str) -> bool:
        """
        Check if user has MANAGE_CHANNELS permission.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            True if user has MANAGE_CHANNELS permission
        """
        try:
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return False

            member = guild.get_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.manage_channels

        except Exception as e:
            logger.error("Error checking MANAGE_CHANNELS permission: %s", e)
            return False

    async def check_administrator_permission(self, user_id: str, guild_id: str) -> bool:
        """
        Check if user has ADMINISTRATOR permission.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            True if user has ADMINISTRATOR permission
        """
        try:
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return False

            member = guild.get_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.administrator

        except Exception as e:
            logger.error("Error checking ADMINISTRATOR permission: %s", e)
            return False

    async def check_game_host_permission(
        self,
        user_id: str,
        guild_id: str,
        _channel_id: str | None = None,
    ) -> bool:
        """
        Check if user can host games.

        Currently checks MANAGE_GUILD permission only.
        Template-based role restrictions will be added in Phase 2.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            channel_id: Discord channel ID (unused, kept for compatibility)

        Returns:
            True if user can host games
        """
        return await self.check_manage_guild_permission(user_id, guild_id)

    async def invalidate_user_roles(self, user_id: str, guild_id: str) -> None:
        """
        Invalidate cached user roles.

        Call this after operations that may change user permissions.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
        """
        await self.cache.invalidate_user_roles(user_id, guild_id)
