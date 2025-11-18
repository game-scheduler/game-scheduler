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


"""Configuration management service with settings inheritance."""

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from shared.models import channel, game, guild


class SettingsResolver:
    """Resolve configuration settings using inheritance hierarchy."""

    def resolve_max_players(
        self,
        game: "game.GameSession | None",
        channel: "channel.ChannelConfiguration | None",
        guild: "guild.GuildConfiguration | None",
    ) -> int:
        """
        Resolve max players using inheritance: game > channel > guild > default.

        Args:
            game: Game session configuration
            channel: Channel configuration
            guild: Guild configuration

        Returns:
            Resolved max players value
        """
        if game and game.max_players is not None:
            return game.max_players
        if channel and channel.max_players is not None:
            return channel.max_players
        if guild and guild.default_max_players is not None:
            return guild.default_max_players
        return 10

    def resolve_reminder_minutes(
        self,
        game: "game.GameSession | None",
        channel: "channel.ChannelConfiguration | None",
        guild: "guild.GuildConfiguration | None",
    ) -> list[int]:
        """
        Resolve reminder times using inheritance: game > channel > guild > default.

        Args:
            game: Game session configuration
            channel: Channel configuration
            guild: Guild configuration

        Returns:
            Resolved reminder times in minutes
        """
        if game and game.reminder_minutes is not None:
            return game.reminder_minutes
        if channel and channel.reminder_minutes is not None:
            return channel.reminder_minutes
        if guild and guild.default_reminder_minutes is not None:
            return guild.default_reminder_minutes
        return [60, 15]

    def resolve_rules(
        self,
        game: "game.GameSession | None",
        channel: "channel.ChannelConfiguration | None",
        guild: "guild.GuildConfiguration | None",
    ) -> str:
        """
        Resolve rules text using inheritance: game > channel > guild > default.

        Args:
            game: Game session configuration
            channel: Channel configuration
            guild: Guild configuration

        Returns:
            Resolved rules text
        """
        if game and game.rules:
            return game.rules
        if channel and channel.default_rules:
            return channel.default_rules
        if guild and guild.default_rules:
            return guild.default_rules
        return ""

    def resolve_allowed_host_roles(
        self,
        channel: "channel.ChannelConfiguration | None",
        guild: "guild.GuildConfiguration | None",
    ) -> list[str]:
        """
        Resolve allowed host roles using inheritance: channel > guild > default.

        Args:
            channel: Channel configuration
            guild: Guild configuration

        Returns:
            Resolved list of role IDs allowed to host games
        """
        if channel and channel.allowed_host_role_ids is not None:
            return channel.allowed_host_role_ids
        if guild and guild.allowed_host_role_ids is not None:
            return guild.allowed_host_role_ids
        return []


class ConfigurationService:
    """Service for managing guild and channel configurations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.resolver = SettingsResolver()

    async def get_guild_by_discord_id(
        self, guild_discord_id: str
    ) -> "guild.GuildConfiguration | None":
        """
        Fetch guild configuration by Discord guild ID.

        Args:
            guild_discord_id: Discord guild snowflake ID

        Returns:
            Guild configuration or None if not found
        """
        from shared.models import guild as guild_module

        result = await self.db.execute(
            select(guild_module.GuildConfiguration).where(
                guild_module.GuildConfiguration.guild_id == guild_discord_id
            )
        )
        return result.scalar_one_or_none()

    async def get_channel_by_discord_id(
        self, channel_discord_id: str
    ) -> "channel.ChannelConfiguration | None":
        """
        Fetch channel configuration by Discord channel ID with guild relationship.

        Args:
            channel_discord_id: Discord channel snowflake ID

        Returns:
            Channel configuration or None if not found
        """
        from shared.models import channel as channel_module

        result = await self.db.execute(
            select(channel_module.ChannelConfiguration)
            .options(selectinload(channel_module.ChannelConfiguration.guild))
            .where(channel_module.ChannelConfiguration.channel_id == channel_discord_id)
        )
        return result.scalar_one_or_none()

    async def get_channels_by_guild(self, guild_id: str) -> list["channel.ChannelConfiguration"]:
        """
        Fetch all channels for a guild.

        Args:
            guild_id: Guild configuration ID (UUID)

        Returns:
            List of channel configurations
        """
        from shared.models import channel as channel_module

        result = await self.db.execute(
            select(channel_module.ChannelConfiguration).where(
                channel_module.ChannelConfiguration.guild_id == guild_id
            )
        )
        return list(result.scalars().all())

    async def create_guild_config(
        self, guild_discord_id: str, guild_name: str, **settings
    ) -> "guild.GuildConfiguration":
        """
        Create new guild configuration.

        Args:
            guild_discord_id: Discord guild snowflake ID
            guild_name: Discord guild name
            **settings: Additional configuration settings

        Returns:
            Created guild configuration
        """
        from shared.models import guild as guild_module

        guild_config = guild_module.GuildConfiguration(
            guild_id=guild_discord_id, guild_name=guild_name, **settings
        )
        self.db.add(guild_config)
        await self.db.commit()
        await self.db.refresh(guild_config)
        return guild_config

    async def update_guild_config(
        self, guild_config: "guild.GuildConfiguration", **updates
    ) -> "guild.GuildConfiguration":
        """
        Update guild configuration.

        Args:
            guild_config: Existing guild configuration
            **updates: Fields to update

        Returns:
            Updated guild configuration
        """
        for key, value in updates.items():
            if value is not None:
                setattr(guild_config, key, value)

        await self.db.commit()
        await self.db.refresh(guild_config)
        return guild_config

    async def create_channel_config(
        self, guild_id: str, channel_discord_id: str, channel_name: str, **settings
    ) -> "channel.ChannelConfiguration":
        """
        Create new channel configuration.

        Args:
            guild_id: Parent guild configuration ID (UUID)
            channel_discord_id: Discord channel snowflake ID
            channel_name: Discord channel name
            **settings: Additional configuration settings

        Returns:
            Created channel configuration
        """
        from shared.models import channel as channel_module

        channel_config = channel_module.ChannelConfiguration(
            guild_id=guild_id,
            channel_id=channel_discord_id,
            channel_name=channel_name,
            **settings,
        )
        self.db.add(channel_config)
        await self.db.commit()
        await self.db.refresh(channel_config)
        return channel_config

    async def update_channel_config(
        self, channel_config: "channel.ChannelConfiguration", **updates
    ) -> "channel.ChannelConfiguration":
        """
        Update channel configuration.

        Args:
            channel_config: Existing channel configuration
            **updates: Fields to update

        Returns:
            Updated channel configuration
        """
        for key, value in updates.items():
            if value is not None:
                setattr(channel_config, key, value)

        await self.db.commit()
        await self.db.refresh(channel_config)
        return channel_config
