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


"""
Role verification service for Discord users.

Provides role checking with Discord API integration and Redis caching.
"""

import logging
from typing import TYPE_CHECKING

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.auth import cache
from shared.models import channel, guild

if TYPE_CHECKING:
    from discord import Client

logger = logging.getLogger(__name__)


class RoleChecker:
    """Service for checking user roles and permissions."""

    def __init__(self, bot: "Client", db_session: AsyncSession):
        """
        Initialize role checker.

        Args:
            bot: Discord bot client
            db_session: Database session for configuration queries
        """
        self.bot = bot
        self.db = db_session
        self.cache = cache.RoleCache()

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
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                logger.warning(f"Guild {guild_id} not found")
                return []

            member = await guild.fetch_member(int(user_id))
            if member is None:
                logger.warning(f"Member {user_id} not found in guild {guild_id}")
                return []

            role_ids = [str(role.id) for role in member.roles if role.id != guild.id]

            await self.cache.set_user_roles(user_id, guild_id, role_ids)
            return role_ids

        except discord.NotFound:
            logger.warning(f"Member {user_id} not found in guild {guild_id}")
            return []
        except discord.Forbidden:
            logger.error(f"Bot lacks permission to fetch member {user_id} in guild {guild_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching user roles: {e}")
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
                logger.warning(f"Guild {guild_id} not found")
                return []

            return list(guild.roles)

        except Exception as e:
            logger.error(f"Error fetching guild roles: {e}")
            return []

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

            member = await guild.fetch_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.manage_guild

        except Exception as e:
            logger.error(f"Error checking MANAGE_GUILD permission: {e}")
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

            member = await guild.fetch_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.manage_channels

        except Exception as e:
            logger.error(f"Error checking MANAGE_CHANNELS permission: {e}")
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

            member = await guild.fetch_member(int(user_id))
            if member is None:
                return False

            return member.guild_permissions.administrator

        except Exception as e:
            logger.error(f"Error checking ADMINISTRATOR permission: {e}")
            return False

    async def check_game_host_permission(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str | None = None,
    ) -> bool:
        """
        Check if user can host games with inheritance resolution.

        Checks channel-specific allowed roles first, then guild allowed roles,
        then falls back to MANAGE_GUILD permission.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            channel_id: Discord channel ID (optional)

        Returns:
            True if user can host games
        """
        user_role_ids = await self.get_user_role_ids(user_id, guild_id)

        if channel_id:
            result = await self.db.execute(
                select(channel.ChannelConfiguration).where(
                    channel.ChannelConfiguration.channel_id == channel_id
                )
            )
            channel_config = result.scalar_one_or_none()

            if channel_config and channel_config.allowed_host_role_ids:
                return any(
                    role_id in channel_config.allowed_host_role_ids for role_id in user_role_ids
                )

        result = await self.db.execute(
            select(guild.GuildConfiguration).where(guild.GuildConfiguration.guild_id == guild_id)
        )
        guild_config = result.scalar_one_or_none()

        if guild_config and guild_config.allowed_host_role_ids:
            return any(role_id in guild_config.allowed_host_role_ids for role_id in user_role_ids)

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
