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


"""Database query functions for guild and channel configurations."""

import logging

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from shared.data_access.guild_isolation import (
    get_current_guild_ids,
    set_current_guild_ids,
)
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration

logger = logging.getLogger(__name__)


async def setup_rls_and_convert_guild_ids(
    db: AsyncSession, discord_guild_ids: list[str]
) -> list[str]:
    """
    Set up RLS context and convert Discord guild IDs to database UUIDs.

    This function handles the chicken-and-egg problem with RLS:
    1. Explicitly sets RLS context at SQL level (ContextVar doesn't propagate reliably)
    2. Queries guild_configurations to convert Discord IDs to UUIDs
    3. Updates ContextVar with UUIDs for subsequent queries

    Args:
        db: Database session
        discord_guild_ids: List of Discord guild IDs (snowflakes)

    Returns:
        List of database UUIDs (GuildConfiguration.id) for guilds that exist
    """
    # Set ContextVar first (for any other code that checks it)
    set_current_guild_ids(discord_guild_ids)

    # Explicitly set RLS context at SQL level
    # ContextVar doesn't propagate reliably to sync session event listeners
    discord_ids_csv = ",".join(discord_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{discord_ids_csv}'"))
    logger.debug("Set RLS context to Discord IDs: %s", discord_ids_csv)

    # Convert Discord IDs to database UUIDs
    guild_uuids = await convert_discord_guild_ids_to_uuids(db, discord_guild_ids)
    logger.debug("Converted to %s UUIDs: %s", len(guild_uuids), guild_uuids)

    # Update ContextVar with UUIDs for remaining queries
    set_current_guild_ids(guild_uuids)

    return guild_uuids


async def convert_discord_guild_ids_to_uuids(
    db: AsyncSession, discord_guild_ids: list[str]
) -> list[str]:
    """
    Convert Discord guild IDs (snowflakes) to database UUIDs for RLS context.

    Requires RLS context to be set with Discord snowflakes before calling.
    The RLS policy on guild_configurations checks both id and guild_id fields.

    Args:
        db: Database session
        discord_guild_ids: List of Discord guild IDs (snowflakes)

    Returns:
        List of database UUIDs (GuildConfiguration.id) for guilds that exist
    """
    logger.debug("Converting %s Discord IDs: %s", len(discord_guild_ids), discord_guild_ids)
    result = await db.execute(
        select(GuildConfiguration.id).where(GuildConfiguration.guild_id.in_(discord_guild_ids))
    )
    guild_uuids = [row[0] for row in result]
    logger.debug("Converted to %s UUIDs: %s", len(guild_uuids), guild_uuids)
    return guild_uuids


async def get_guild_by_id(db: AsyncSession, guild_id: str) -> GuildConfiguration | None:
    """
    Fetch guild configuration by database UUID.

    Args:
        db: Database session
        guild_id: Database UUID

    Returns:
        Guild configuration or None if not found
    """
    result = await db.execute(select(GuildConfiguration).where(GuildConfiguration.id == guild_id))
    return result.scalar_one_or_none()


async def require_guild_by_id(
    db: AsyncSession,
    guild_id: str,
    access_token: str,
    user_discord_id: str,
    not_found_detail: str = "Guild configuration not found",
) -> GuildConfiguration:
    """
    Fetch guild configuration by UUID with automatic RLS context setup.

    Sets RLS context if not already set (idempotent). Returns 404 for both
    "not found" and "unauthorized" to prevent information disclosure.

    Args:
        db: Database session
        guild_id: Database UUID (GuildConfiguration.id)
        access_token: User's OAuth2 access token
        user_discord_id: User's Discord ID
        not_found_detail: Custom error message for 404 response

    Returns:
        Guild configuration (verified user has access)

    Raises:
        HTTPException(404): If guild not found OR user not authorized
    """
    from services.api.auth import oauth2  # noqa: PLC0415 - avoid circular dependency

    # Ensure RLS context is set (idempotent - only fetches if not already set)
    if get_current_guild_ids() is None:
        user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
        discord_guild_ids = [g["id"] for g in user_guilds]
        await setup_rls_and_convert_guild_ids(db, discord_guild_ids)

    guild_config = await get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    # Defense in depth: Manual authorization check (RLS also enforces at DB level)
    # Check guild UUID OR Discord guild ID is in user's authorized guild list
    # (Context can contain either UUIDs or Discord IDs depending on setup path)
    authorized_guild_ids = get_current_guild_ids()
    if authorized_guild_ids is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    # Check if either UUID or Discord ID is in the authorized list
    if (
        guild_config.id not in authorized_guild_ids
        and guild_config.guild_id not in authorized_guild_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    return guild_config


async def get_guild_by_discord_id(
    db: AsyncSession, guild_discord_id: str
) -> GuildConfiguration | None:
    """
    Fetch guild configuration by Discord guild ID.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID

    Returns:
        Guild configuration or None if not found
    """
    result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.guild_id == guild_discord_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_id(db: AsyncSession, channel_id: str) -> ChannelConfiguration | None:
    """
    Fetch channel configuration by database UUID with guild relationship.

    Args:
        db: Database session
        channel_id: Database UUID

    Returns:
        Channel configuration or None if not found
    """
    result = await db.execute(
        select(ChannelConfiguration)
        .options(selectinload(ChannelConfiguration.guild))
        .where(ChannelConfiguration.id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_discord_id(
    db: AsyncSession, channel_discord_id: str
) -> ChannelConfiguration | None:
    """
    Fetch channel configuration by Discord channel ID with guild relationship.

    Args:
        db: Database session
        channel_discord_id: Discord channel snowflake ID

    Returns:
        Channel configuration or None if not found
    """
    result = await db.execute(
        select(ChannelConfiguration)
        .options(selectinload(ChannelConfiguration.guild))
        .where(ChannelConfiguration.channel_id == channel_discord_id)
    )
    return result.scalar_one_or_none()


async def get_channels_by_guild(db: AsyncSession, guild_id: str) -> list[ChannelConfiguration]:
    """
    Fetch all active channels for a guild.

    Only returns channels where is_active=True, hiding deleted Discord channels
    from channel selection dropdowns.

    Args:
        db: Database session
        guild_id: Guild configuration ID (UUID)

    Returns:
        List of active channel configurations
    """
    result = await db.execute(
        select(ChannelConfiguration).where(
            ChannelConfiguration.guild_id == guild_id, ChannelConfiguration.is_active
        )
    )
    return list(result.scalars().all())
