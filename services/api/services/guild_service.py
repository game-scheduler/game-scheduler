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


"""Guild configuration service for create and update operations."""

import asyncio
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.database import queries
from services.api.dependencies.discord import get_discord_client
from services.api.services import channel_service
from services.api.services import template_service as template_service_module
from shared.data_access.guild_isolation import (
    get_current_guild_ids,
    set_current_guild_ids,
)
from shared.discord.client import DiscordAPIClient
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


async def create_guild_config(
    db: AsyncSession,
    guild_discord_id: str,
    **settings: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Create new guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.flush()
    return guild_config


async def update_guild_config(
    guild_config: GuildConfiguration,
    **updates: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Update guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_config: Existing guild configuration
        **updates: Fields to update

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        setattr(guild_config, key, value)

    return guild_config


async def _compute_candidate_guild_ids(
    client: DiscordAPIClient,
    access_token: str,
    user_id: str,
) -> set[str]:
    """
    Compute candidate guild IDs: intersection of user admin guilds and bot guilds.

    Args:
        client: Discord API client
        access_token: User's OAuth2 access token
        user_id: Discord user ID

    Returns:
        Set of guild IDs where user has MANAGE_GUILD permission and bot is present
    """
    # Fetch user's guilds with MANAGE_GUILD permission
    user_guilds = await client.get_guilds(access_token, user_id)
    manage_guild = 0x00000020  # Permission bit for MANAGE_GUILD
    admin_guild_ids = {
        guild["id"] for guild in user_guilds if int(guild.get("permissions", 0)) & manage_guild
    }

    # Respect Discord rate limit (1 req/sec for /users/@me/guilds)
    await asyncio.sleep(1.1)

    # Fetch bot's current guilds
    bot_guilds = await client.get_guilds()
    bot_guild_ids = {guild["id"] for guild in bot_guilds}

    # Compute candidate guilds: (bot guilds ∩ user admin guilds)
    return admin_guild_ids & bot_guild_ids


async def _expand_rls_context_for_guilds(db: AsyncSession, candidate_guild_ids: set[str]) -> None:
    """
    Expand RLS context to include candidate guilds for query and insert operations.

    Args:
        db: Database session
        candidate_guild_ids: Set of guild IDs to include in RLS context
    """
    current_guild_ids = get_current_guild_ids() or []
    expanded_guild_ids = list(set(current_guild_ids) | candidate_guild_ids)
    expanded_ids_csv = ",".join(expanded_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{expanded_ids_csv}'"))
    set_current_guild_ids(expanded_guild_ids)


async def _get_existing_guild_ids(db: AsyncSession) -> set[str]:
    """
    Query existing guild IDs from database.

    Args:
        db: Database session

    Returns:
        Set of guild IDs that already exist in database
    """
    result = await db.execute(select(GuildConfiguration))
    existing_guilds = result.scalars().all()
    return {guild.guild_id for guild in existing_guilds}


async def _sync_guild_channels(
    db: AsyncSession,
    client: DiscordAPIClient,
    guild_config_id: str,
    guild_discord_id: str,
) -> int:
    """
    Sync channels from Discord to database for a guild.

    - Adds new text channels with is_active=True (get-or-create pattern)
    - Marks channels missing from Discord as is_active=False
    - Returns count of channels added/updated

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        client: Discord API client
        guild_config_id: Guild UUID in database
        guild_discord_id: Guild snowflake ID in Discord

    Returns:
        Number of channels added or updated
    """
    # Fetch current channels from Discord
    discord_channels = await client.get_guild_channels(guild_discord_id)
    text_channel_type = 0
    discord_text_channel_ids = {
        ch["id"] for ch in discord_channels if ch.get("type") == text_channel_type
    }

    # Get existing channels from database
    result = await db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild_config_id)
    )
    existing_channels = {ch.channel_id: ch for ch in result.scalars().all()}

    channels_updated = 0

    # Add new channels or reactivate existing ones
    for channel_discord_id in discord_text_channel_ids:
        if channel_discord_id in existing_channels:
            channel = existing_channels[channel_discord_id]
            if not channel.is_active:
                channel.is_active = True
                channels_updated += 1
        else:
            await channel_service.create_channel_config(
                db, guild_config_id, channel_discord_id, is_active=True
            )
            channels_updated += 1

    # Mark missing channels as inactive
    for channel_discord_id, channel in existing_channels.items():
        if channel_discord_id not in discord_text_channel_ids and channel.is_active:
            channel.is_active = False
            channels_updated += 1

    # SQLAlchemy ORM tracks changes to fetched objects; modifications will be
    # persisted when the transaction is committed by the caller
    return channels_updated


async def _create_guild_with_channels_and_template(
    db: AsyncSession,
    client: DiscordAPIClient,
    guild_discord_id: str,
) -> tuple[int, int]:
    """
    Create guild configuration, channel configurations, and default template.

    Args:
        db: Database session
        client: Discord API client
        guild_discord_id: Discord guild snowflake ID

    Returns:
        Tuple of (guilds_created, channels_created) counts
    """
    # Set RLS context to Discord snowflake ID for guild creation
    current_guild_ids = get_current_guild_ids() or []
    initial_guild_ids = list(set(current_guild_ids) | {guild_discord_id})
    initial_ids_csv = ",".join(initial_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{initial_ids_csv}'"))
    set_current_guild_ids(initial_guild_ids)

    # Create guild config
    guild_config = await create_guild_config(db, guild_discord_id)

    # Update RLS context to include the new guild UUID (for template creation)
    current_guild_ids = get_current_guild_ids() or []
    updated_guild_ids = list(set(current_guild_ids) | {str(guild_config.id)})
    updated_ids_csv = ",".join(updated_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{updated_ids_csv}'"))
    set_current_guild_ids(updated_guild_ids)

    # Fetch guild channels using bot token
    guild_channels = await client.get_guild_channels(guild_discord_id)

    # Create channel configs for text channels
    text_channel = 0
    channels_created = 0
    for channel in guild_channels:
        if channel.get("type") == text_channel:
            await channel_service.create_channel_config(
                db, guild_config.id, channel["id"], is_active=True
            )
            channels_created += 1

    # Create default template for the guild using first text channel
    if guild_channels:
        first_channel = next((ch for ch in guild_channels if ch.get("type") == text_channel), None)
        if first_channel:
            # Get the created channel config UUID
            channel_config = await queries.get_channel_by_discord_id(db, first_channel["id"])
            if channel_config:
                template_svc = template_service_module.TemplateService(db)
                await template_svc.create_default_template(guild_config.id, channel_config.id)

    return (1, channels_created)


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

    # Compute candidate guilds: (bot guilds ∩ user admin guilds)
    candidate_guild_ids = await _compute_candidate_guild_ids(discord_client, access_token, user_id)

    # Set RLS context to include ALL candidate guilds for query and insert
    await _expand_rls_context_for_guilds(db, candidate_guild_ids)

    # Query for existing guilds with proper RLS context set
    existing_guild_ids = await _get_existing_guild_ids(db)

    new_guild_ids = candidate_guild_ids - existing_guild_ids

    if not new_guild_ids:
        return {"new_guilds": 0, "new_channels": 0}

    # Create guild and channel configs for new guilds
    new_guilds_count = 0
    new_channels_count = 0

    for guild_discord_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(
            db, discord_client, guild_discord_id
        )
        new_guilds_count += guilds_created
        new_channels_count += channels_created

    return {"new_guilds": new_guilds_count, "new_channels": new_channels_count}
