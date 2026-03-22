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

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.dependencies.discord import get_discord_client
from shared.data_access import guild_queries
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


async def create_guild_config(
    db: AsyncSession,
    guild_discord_id: str,
    **settings: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Create new guild configuration.

    TODO: Migrate to bot service (Phase 6).
    This function is being moved to services/bot/guild_sync.py.
    API route will publish RabbitMQ message for bot to handle guild creation.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    msg = "Guild creation moved to bot service. Use RabbitMQ message pattern."
    raise NotImplementedError(msg)


async def update_guild_config(
    guild_config: GuildConfiguration,
    **updates: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Update guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        guild_config: Existing guild configuration
        **updates: Fields to update

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        setattr(guild_config, key, value)

    return guild_config


async def refresh_guild_channels(
    db: AsyncSession,
    guild_id: str,
) -> list[dict[str, Any]]:
    """
    Refresh channels for a specific guild from Discord.

    Fetches channels from Discord API and updates database:
    - Creates new ChannelConfiguration records for new channels
    - Marks deleted channels as inactive
    - Reactivates previously inactive channels that reappear

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_id: Guild UUID in database

    Returns:
        List of updated channel dictionaries
    """
    # Get guild configuration to find Discord guild ID
    guild_result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.id == guild_id)
    )
    guild = guild_result.scalar_one_or_none()
    if not guild:
        return []

    # Fetch channels from Discord, bypassing cache so newly added channels are visible
    discord_client = get_discord_client()
    discord_channels = await discord_client.get_guild_channels(guild.guild_id, force_refresh=True)

    # Filter for text channels only (type 0)
    text_channel_type = 0
    discord_text_channel_ids = {
        ch["id"] for ch in discord_channels if ch.get("type") == text_channel_type
    }

    # Get existing channels from database
    channels_result = await db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild_id)
    )
    existing_channels = {ch.channel_id: ch for ch in channels_result.scalars().all()}

    # Add new channels or reactivate existing ones
    for channel_discord_id in discord_text_channel_ids:
        if channel_discord_id in existing_channels:
            channel = existing_channels[channel_discord_id]
            if not channel.is_active:
                channel.is_active = True
        else:
            await guild_queries.create_channel_config(
                db, guild_id, channel_discord_id, is_active=True
            )

    # Mark missing channels as inactive
    for channel_discord_id, channel in existing_channels.items():
        if channel_discord_id not in discord_text_channel_ids and channel.is_active:
            channel.is_active = False

    # Fetch final channel list after all updates
    all_channels_result = await db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild_id)
    )
    all_channels = all_channels_result.scalars().all()

    return [
        {
            "id": ch.id,
            "channel_id": ch.channel_id,
            "is_active": ch.is_active,
        }
        for ch in all_channels
    ]
