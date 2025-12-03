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


"""Guild configuration service for create and update operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.guild import GuildConfiguration


async def create_guild_config(
    db: AsyncSession, guild_discord_id: str, **settings
) -> GuildConfiguration:
    """
    Create new guild configuration.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.commit()
    await db.refresh(guild_config)
    return guild_config


async def update_guild_config(
    db: AsyncSession, guild_config: GuildConfiguration, **updates
) -> GuildConfiguration:
    """
    Update guild configuration.

    Args:
        db: Database session
        guild_config: Existing guild configuration
        **updates: Fields to update (only non-None values are applied)

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        if value is not None:
            setattr(guild_config, key, value)

    await db.commit()
    await db.refresh(guild_config)
    return guild_config
