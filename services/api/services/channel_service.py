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


"""Channel configuration service for create and update operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.channel import ChannelConfiguration


async def create_channel_config(
    db: AsyncSession, guild_id: str, channel_discord_id: str, **settings
) -> ChannelConfiguration:
    """
    Create new channel configuration.

    Args:
        db: Database session
        guild_id: Parent guild configuration ID (UUID)
        channel_discord_id: Discord channel snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created channel configuration
    """
    channel_config = ChannelConfiguration(
        guild_id=guild_id,
        channel_id=channel_discord_id,
        **settings,
    )
    db.add(channel_config)
    await db.commit()
    await db.refresh(channel_config)
    return channel_config


async def update_channel_config(
    db: AsyncSession, channel_config: ChannelConfiguration, **updates
) -> ChannelConfiguration:
    """
    Update channel configuration.

    Args:
        db: Database session
        channel_config: Existing channel configuration
        **updates: Fields to update (only non-None values are applied)

    Returns:
        Updated channel configuration
    """
    for key, value in updates.items():
        if value is not None:
            setattr(channel_config, key, value)

    await db.commit()
    await db.refresh(channel_config)
    return channel_config
