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


"""Guild configuration endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.auth import oauth2
from services.api.database import queries
from services.api.dependencies import permissions
from services.api.dependencies.discord import get_discord_client
from services.api.services import guild_service
from shared import database
from shared.discord.client import DiscordAPIClient, fetch_channel_name_safe
from shared.models.guild import GuildConfiguration
from shared.schemas import auth as auth_schemas
from shared.schemas import channel as channel_schemas
from shared.schemas import guild as guild_schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/guilds", tags=["guilds"])


async def _build_guild_config_response(
    guild_config: GuildConfiguration,
    current_user: auth_schemas.CurrentUser,
    db: AsyncSession,
) -> guild_schemas.GuildConfigResponse:
    """Build guild configuration response with guild name."""
    guild_name = await permissions.get_guild_name(guild_config.guild_id, current_user, db)
    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_name=guild_name,
        bot_manager_role_ids=guild_config.bot_manager_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.get("", response_model=guild_schemas.GuildListResponse)
async def list_guilds(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
) -> guild_schemas.GuildListResponse:
    """
    List all guilds where the bot is present and user is a member.

    Returns guild configurations with current settings.
    """
    # Get guilds with automatic caching from discord client
    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    guild_configs = []
    for guild_id, discord_guild_data in user_guilds_dict.items():
        guild_config = await queries.get_guild_by_discord_id(db, guild_id)
        if guild_config:
            guild_name = discord_guild_data.get("name", "Unknown Guild")

            guild_configs.append(
                guild_schemas.GuildBasicInfoResponse(
                    id=guild_config.id,
                    guild_name=guild_name,
                    created_at=guild_config.created_at.isoformat(),
                    updated_at=guild_config.updated_at.isoformat(),
                )
            )

    return guild_schemas.GuildListResponse(guilds=guild_configs)


@router.get("/{guild_id}", response_model=guild_schemas.GuildBasicInfoResponse)
async def get_guild(
    guild_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildBasicInfoResponse:
    """
    Get basic guild information by database UUID.

    Returns guild name and metadata without sensitive configuration data.
    Requires user to be member of the guild.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    user_guilds = await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)
    user_guilds_dict = {g["id"]: g for g in user_guilds}

    guild_name = user_guilds_dict[guild_config.guild_id].get("name", "Unknown Guild")

    return guild_schemas.GuildBasicInfoResponse(
        id=guild_config.id,
        guild_name=guild_name,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )


@router.get("/{guild_id}/config", response_model=guild_schemas.GuildConfigResponse)
async def get_guild_config(
    guild_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(permissions.require_manage_guild)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildConfigResponse:
    """
    Get guild configuration including sensitive settings.

    Requires MANAGE_GUILD permission in the guild.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    return await _build_guild_config_response(guild_config, current_user, db)


@router.post(
    "",
    response_model=guild_schemas.GuildConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_guild_config(
    request: guild_schemas.GuildConfigCreateRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(permissions.require_manage_guild)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildConfigResponse:
    """
    Create guild configuration.

    Requires MANAGE_GUILD permission in the guild.
    """
    existing = await queries.get_guild_by_discord_id(db, request.guild_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Guild configuration already exists",
        )

    guild_config = await guild_service.create_guild_config(
        db,
        guild_discord_id=request.guild_id,
        require_host_role=request.require_host_role,
    )

    return await _build_guild_config_response(guild_config, current_user, db)


@router.put("/{guild_id}", response_model=guild_schemas.GuildConfigResponse)
async def update_guild_config(
    guild_id: str,
    request: guild_schemas.GuildConfigUpdateRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(permissions.require_manage_guild)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildConfigResponse:
    """
    Update guild configuration.

    Requires MANAGE_GUILD permission in the guild.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    updates = request.model_dump(exclude_unset=True)
    guild_config = await guild_service.update_guild_config(guild_config, **updates)

    return await _build_guild_config_response(guild_config, current_user, db)


@router.get(
    "/{guild_id}/channels",
    response_model=list[channel_schemas.ChannelConfigResponse],
)
async def list_guild_channels(
    guild_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> list[channel_schemas.ChannelConfigResponse]:
    """
    List active channels for a guild by UUID.

    Only returns channels with is_active=True to hide deleted Discord channels.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)

    channels = await queries.get_channels_by_guild(db, guild_config.id)

    channel_responses = []
    for channel in channels:
        if not channel.is_active:
            continue

        channel_name = await fetch_channel_name_safe(channel.channel_id)

        channel_responses.append(
            channel_schemas.ChannelConfigResponse(
                id=channel.id,
                guild_id=channel.guild_id,
                guild_discord_id=guild_config.guild_id,
                channel_id=channel.channel_id,
                channel_name=channel_name,
                is_active=channel.is_active,
                created_at=channel.created_at.isoformat(),
                updated_at=channel.updated_at.isoformat(),
            )
        )

    return channel_responses


@router.get("/{guild_id}/roles")
async def list_guild_roles(
    guild_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> list[dict]:
    """
    List all roles for a guild, excluding @everyone and managed roles.

    Returns roles suitable for notification mentions.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)

    discord_guild_id = guild_config.guild_id
    roles = await discord_client.fetch_guild_roles(discord_guild_id)
    logger.info("Fetched %s roles for guild %s", len(roles), discord_guild_id)

    # Filter out managed roles but allow @everyone
    filtered_roles = [
        {
            "id": role["id"],
            "name": (role["name"] if role["name"].startswith("@") else f"@{role['name']}"),
            "color": role["color"],
            "position": role["position"],
            "managed": role.get("managed", False),
        }
        for role in roles
        if not role.get("managed", False)
    ]

    # Sort by position (highest first)
    filtered_roles.sort(key=lambda r: r["position"], reverse=True)
    logger.info(
        "Returning %s filtered roles for guild %s",
        len(filtered_roles),
        discord_guild_id,
    )

    return filtered_roles


@router.post("/sync", response_model=guild_schemas.GuildSyncResponse)
async def sync_guilds(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildSyncResponse:
    """
    Sync user's Discord guilds and channels with database.

    - Creates new guilds with channels and default template
    - Refreshes channels for existing guilds
    - Marks deleted Discord channels as inactive

    Returns count of new guilds, new channels, and updated channels.

    TODO: Migrate to RabbitMQ message pattern (Phase 6, Task 6.1).
    This endpoint will publish GUILD_SYNC_REQUESTED event instead of calling
    guild_service.sync_user_guilds() directly. Bot service will handle sync.
    """
    access_token = current_user.access_token
    user_discord_id = current_user.user.discord_id

    result = await guild_service.sync_user_guilds(db, access_token, user_discord_id)

    return guild_schemas.GuildSyncResponse(
        new_guilds=result["new_guilds"],
        new_channels=result["new_channels"],
        updated_channels=result["updated_channels"],
    )


@router.post("/{guild_id}/validate-mention")
async def validate_mention(
    guild_id: str,
    request: guild_schemas.ValidateMentionRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.ValidateMentionResponse:
    """
    Validate a Discord mention for a guild.

    Checks if the mention can be resolved to a valid guild member.
    Does not return user details, only validation status.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)

    discord_guild_id = guild_config.guild_id
    access_token = current_user.access_token
    mention = request.mention.strip()
    if not mention:
        return guild_schemas.ValidateMentionResponse(valid=False, error="Mention cannot be empty")

    # If it doesn't start with @, it's a placeholder - always valid
    if not mention.startswith("@"):
        return guild_schemas.ValidateMentionResponse(valid=True, error=None)

    # Query Discord API to validate @mention
    from services.api.services.participant_resolver import (  # noqa: PLC0415
        ParticipantResolver,
    )

    discord_client_instance = get_discord_client()
    resolver = ParticipantResolver(discord_client_instance)

    try:
        valid_participants, validation_errors = await resolver.resolve_initial_participants(
            discord_guild_id, [mention], access_token
        )

        if validation_errors:
            error_info = validation_errors[0]
            return guild_schemas.ValidateMentionResponse(
                valid=False, error=error_info.get("reason", "Invalid mention")
            )

        if valid_participants:
            return guild_schemas.ValidateMentionResponse(valid=True, error=None)

        return guild_schemas.ValidateMentionResponse(valid=False, error="User not found in guild")

    except Exception as e:
        logger.exception("Error validating mention: %s", e)
        return guild_schemas.ValidateMentionResponse(
            valid=False, error="Failed to validate mention. Please try again."
        )
