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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.database import queries
from services.api.dependencies.discord import get_discord_client
from services.api.services import channel_service
from services.api.services import template_service as template_service_module
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
        **updates: Fields to update

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        setattr(guild_config, key, value)

    await db.commit()
    await db.refresh(guild_config)
    return guild_config


async def sync_user_guilds(db: AsyncSession, access_token: str, user_id: str) -> dict[str, int]:
    """
    Sync user's Discord guilds with database.

    Fetches user's guilds with MANAGE_GUILD permission and bot's guilds,
    then creates GuildConfiguration and ChannelConfiguration for new guilds.
    Creates default template for each new guild.

    Args:
        db: Database session
        access_token: User's OAuth2 access token
        user_id: Discord user ID

    Returns:
        Dictionary with counts: {
            "new_guilds": number of new guilds created,
            "new_channels": number of new channels created
        }
    """
    discord_client = get_discord_client()

    # Fetch user's guilds with MANAGE_GUILD permission
    user_guilds = await discord_client.get_guilds(access_token, user_id)
    manage_guild = 0x00000020  # Permission bit for MANAGE_GUILD
    admin_guild_ids = {
        guild["id"] for guild in user_guilds if int(guild.get("permissions", 0)) & manage_guild
    }

    # Fetch bot's current guilds
    bot_guilds = await discord_client.get_guilds()
    bot_guild_ids = {guild["id"] for guild in bot_guilds}

    # Compute new guilds: (bot guilds ∩ user admin guilds) - existing guilds
    candidate_guild_ids = admin_guild_ids & bot_guild_ids

    # Get existing guild configs
    result = await db.execute(select(GuildConfiguration))
    existing_guilds = result.scalars().all()
    existing_guild_ids = {guild.guild_id for guild in existing_guilds}

    new_guild_ids = candidate_guild_ids - existing_guild_ids

    if not new_guild_ids:
        return {"new_guilds": 0, "new_channels": 0}

    # Create guild and channel configs for new guilds
    new_guilds_count = 0
    new_channels_count = 0

    for guild_discord_id in new_guild_ids:
        # Create guild config
        guild_config = await create_guild_config(db, guild_discord_id)
        new_guilds_count += 1

        # Fetch guild channels using bot token
        guild_channels = await discord_client.get_guild_channels(guild_discord_id)

        # Create channel configs for text channels
        text_channel = 0
        for channel in guild_channels:
            if channel.get("type") == text_channel:
                await channel_service.create_channel_config(
                    db, guild_config.id, channel["id"], is_active=True
                )
                new_channels_count += 1

        # Create default template for the guild using first text channel
        if guild_channels:
            first_channel = next(
                (ch for ch in guild_channels if ch.get("type") == text_channel), None
            )
            if first_channel:
                # Get the created channel config UUID
                channel_config = await queries.get_channel_by_discord_id(db, first_channel["id"])
                if channel_config:
                    template_svc = template_service_module.TemplateService(db)
                    await template_svc.create_default_template(guild_config.id, channel_config.id)

    return {"new_guilds": new_guilds_count, "new_channels": new_channels_count}
