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
Game management REST API endpoints.

Provides CRUD operations for game sessions with validation and authorization.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status as http_status

from services.api.auth import roles as roles_module
from services.api.dependencies import auth as auth_deps
from services.api.dependencies import permissions as permissions_deps
from services.api.dependencies.discord import get_discord_client
from services.api.services import display_names as display_names_module
from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared import database
from shared.discord.client import fetch_channel_name_safe, fetch_guild_name_safe
from shared.messaging import deferred_publisher as messaging_deferred_publisher
from shared.messaging import publisher as messaging_publisher
from shared.models import game as game_model
from shared.models.participant import ParticipantType
from shared.schemas import auth as auth_schemas
from shared.schemas import game as game_schemas
from shared.schemas import participant as participant_schemas
from shared.utils import datetime_utils, participant_sorting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/games", tags=["games"])

# ruff: noqa: B008


async def _validate_image_upload(file: UploadFile, field_name: str) -> None:
    """
    Validate uploaded image file for type and size.

    Args:
        file: Uploaded file to validate
        field_name: Name of the field for error messages

    Raises:
        HTTPException: 400 if validation fails with descriptive message
    """
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be PNG, JPEG, GIF, or WebP",
        )

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    max_size = 5 * 1024 * 1024
    if size > max_size:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be less than 5MB",
        )


async def _get_game_service(
    _current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    db: AsyncSession = Depends(database.get_db_with_user_guilds()),
) -> games_service.GameService:
    """Get game service instance with dependencies (RLS context already set by db dependency)."""
    base_publisher = messaging_publisher.EventPublisher()
    deferred_publisher = messaging_deferred_publisher.DeferredEventPublisher(
        db=db,
        event_publisher=base_publisher,
    )
    discord_client = get_discord_client()
    participant_resolver = resolver_module.ParticipantResolver(discord_client)

    return games_service.GameService(
        db=db,
        event_publisher=deferred_publisher,
        discord_client=discord_client,
        participant_resolver=participant_resolver,
    )


def _parse_update_form_data(
    scheduled_at: str | None,
    reminder_minutes: str | None,
    notify_role_ids: str | None,
    participants: str | None,
    removed_participant_ids: str | None,
) -> tuple[
    datetime | None,
    list[int] | None,
    list[str] | None,
    list[dict] | None,
    list[str] | None,
]:
    """
    Parse JSON fields from form data for game update.

    Args:
        scheduled_at: ISO datetime string
        reminder_minutes: JSON array of reminder minutes
        notify_role_ids: JSON array of role IDs
        participants: JSON array of participant objects
        removed_participant_ids: JSON array of participant IDs to remove

    Returns:
        Tuple of (scheduled_at_datetime, reminder_minutes_list, notify_role_ids_list,
                  participants_list, removed_participant_ids_list)
    """
    scheduled_at_datetime = None
    if scheduled_at:
        scheduled_at_datetime = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

    reminder_minutes_list = None
    if reminder_minutes:
        reminder_minutes_list = json.loads(reminder_minutes)

    notify_role_ids_list = None
    if notify_role_ids:
        notify_role_ids_list = json.loads(notify_role_ids)

    participants_list = None
    if participants:
        participants_list = json.loads(participants)

    removed_participant_ids_list = None
    if removed_participant_ids:
        removed_participant_ids_list = json.loads(removed_participant_ids)

    return (
        scheduled_at_datetime,
        reminder_minutes_list,
        notify_role_ids_list,
        participants_list,
        removed_participant_ids_list,
    )


async def _process_image_upload(
    file: UploadFile | None,
    remove_flag: bool,
    field_name: str,
    game_id: str,
) -> tuple[bytes | None, str | None]:
    """
    Process image upload for game update.

    Args:
        file: Uploaded file or None
        remove_flag: Whether to remove existing image
        field_name: Name of field for logging ("thumbnail" or "image")
        game_id: Game ID for logging

    Returns:
        Tuple of (image_data, mime_type) where empty bytes means removal
    """
    if remove_flag:
        logger.info("Removing %s for game %s", field_name, game_id)
        return b"", ""

    if file:
        logger.info(
            "Received %s upload for game %s: filename=%s, content_type=%s, size=%s",
            field_name,
            game_id,
            file.filename,
            file.content_type,
            file.size,
        )
        await _validate_image_upload(file, field_name)
        image_data = await file.read()
        logger.info("%s read: %s bytes", field_name.capitalize(), len(image_data))
        return image_data, file.content_type

    return None, None


def _handle_game_operation_errors(
    e: Exception,
    form_data: game_schemas.GameCreateRequest | game_schemas.GameUpdateRequest,
) -> NoReturn:
    """
    Handle ValidationError and ValueError exceptions from game operations.

    Args:
        e: The exception to handle
        form_data: Game form data to include in error response

    Raises:
        HTTPException: Appropriate HTTP exception based on error type
    """
    if isinstance(e, resolver_module.ValidationError):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_mentions",
                "message": "Some @mentions could not be resolved",
                "invalid_mentions": e.invalid_mentions,
                "valid_participants": e.valid_participants,
                "form_data": form_data.model_dump(mode="json"),
            },
        ) from None

    if isinstance(e, ValueError):
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail=error_msg
            ) from None
        if "minimum players cannot be greater" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg
            ) from None
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=error_msg) from None

    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected error type: {type(e).__name__}",
    ) from e


@router.post(
    "",
    response_model=game_schemas.GameResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_game(
    template_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    scheduled_at: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
    max_players: Annotated[int | None, Form()] = None,
    expected_duration_minutes: Annotated[int | None, Form()] = None,
    reminder_minutes: Annotated[str | None, Form()] = None,
    where: Annotated[str | None, Form()] = None,
    signup_instructions: Annotated[str | None, Form()] = None,
    signup_method: Annotated[str | None, Form()] = None,
    initial_participants: Annotated[str | None, Form()] = None,
    host: Annotated[str | None, Form()] = None,
    thumbnail: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    *,  # Force remaining parameters to be keyword-only
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
) -> game_schemas.GameResponse:
    """
    Create new game session.

    Validates @mentions in initial_participants and creates GameParticipant records.
    Returns 422 if any @mentions cannot be resolved with disambiguation suggestions.
    Accepts multipart/form-data for file uploads.
    """
    try:
        # Parse JSON fields from form data
        reminder_minutes_list = None
        if reminder_minutes:
            reminder_minutes_list = json.loads(reminder_minutes)

        initial_participants_list = []
        if initial_participants:
            initial_participants_list = json.loads(initial_participants)

        scheduled_at_datetime = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

        # Build request object
        game_data = game_schemas.GameCreateRequest(
            template_id=template_id,
            title=title,
            scheduled_at=scheduled_at_datetime,
            description=description,
            max_players=max_players,
            expected_duration_minutes=expected_duration_minutes,
            reminder_minutes=reminder_minutes_list,
            where=where,
            signup_instructions=signup_instructions,
            signup_method=signup_method,
            initial_participants=initial_participants_list,
            host=host,
        )

        # Validate and read thumbnail
        thumbnail_data = None
        thumbnail_mime = None
        if thumbnail:
            logger.info(
                "Received thumbnail upload: filename=%s, content_type=%s, size=%s",
                thumbnail.filename,
                thumbnail.content_type,
                thumbnail.size,
            )
            await _validate_image_upload(thumbnail, "thumbnail")
            thumbnail_data = await thumbnail.read()
            thumbnail_mime = thumbnail.content_type
            logger.info("Thumbnail read: %s bytes", len(thumbnail_data))
        else:
            logger.debug("No thumbnail file provided")

        # Validate and read image
        image_data = None
        image_mime = None
        if image:
            logger.info(
                "Received image upload: filename=%s, content_type=%s, size=%s",
                image.filename,
                image.content_type,
                image.size,
            )
            await _validate_image_upload(image, "image")
            image_data = await image.read()
            image_mime = image.content_type
            logger.info("Banner image read: %s bytes", len(image_data))
        else:
            logger.debug("No banner image file provided")

        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=current_user.user.id,
            access_token=current_user.access_token,
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime,
            image_data=image_data,
            image_mime_type=image_mime,
        )

        return await _build_game_response(game)

    except (resolver_module.ValidationError, ValueError) as e:
        _handle_game_operation_errors(e, game_data)


@router.get("", response_model=game_schemas.GameListResponse)
async def list_games(
    guild_id: Annotated[str | None, Query(description="Filter by guild UUID")] = None,
    channel_id: Annotated[str | None, Query(description="Filter by channel UUID")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 50,
    offset: Annotated[int, Query(ge=0, description="Results offset")] = 0,
    *,  # Force remaining parameters to be keyword-only
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> game_schemas.GameListResponse:
    """
    List games with optional filters.

    Supports filtering by guild, channel, and status with pagination.
    Games are filtered by guild membership and template player role restrictions.
    """
    games, _total = await game_service.list_games(
        guild_id=guild_id,
        channel_id=channel_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    # Filter games by guild membership and player role restrictions
    authorized_games = []
    for game in games:
        try:
            # Use verify_game_access helper to check authorization
            await permissions_deps.verify_game_access(
                game=game,
                user_discord_id=current_user.user.discord_id,
                access_token=current_user.access_token,
                db=game_service.db,
                role_service=role_service,
            )
            authorized_games.append(game)
        except HTTPException:
            # User not authorized to see this game - skip it
            continue

    game_responses = [await _build_game_response(game) for game in authorized_games]

    return game_schemas.GameListResponse(
        games=game_responses,
        total=len(authorized_games),
    )


@router.get("/{game_id}", response_model=game_schemas.GameResponse)
async def get_game(
    game_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> game_schemas.GameResponse:
    """Get game session by ID with guild membership and role verification."""
    game = await game_service.get_game(game_id)

    if game is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Game not found"
        ) from None

    # Verify user has access (guild membership + player roles)
    await permissions_deps.verify_game_access(
        game=game,
        user_discord_id=current_user.user.discord_id,
        access_token=current_user.access_token,
        db=game_service.db,
        role_service=role_service,
    )

    return await _build_game_response(game)


@router.put("/{game_id}", response_model=game_schemas.GameResponse)
async def update_game(
    game_id: str,
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    signup_instructions: Annotated[str | None, Form()] = None,
    scheduled_at: Annotated[str | None, Form()] = None,
    where: Annotated[str | None, Form()] = None,
    max_players: Annotated[int | None, Form()] = None,
    reminder_minutes: Annotated[str | None, Form()] = None,
    expected_duration_minutes: Annotated[int | None, Form()] = None,
    status: Annotated[str | None, Form()] = None,
    notify_role_ids: Annotated[str | None, Form()] = None,
    participants: Annotated[str | None, Form()] = None,
    removed_participant_ids: Annotated[str | None, Form()] = None,
    signup_method: Annotated[str | None, Form()] = None,
    thumbnail: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    remove_thumbnail: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    *,  # Force remaining parameters to be keyword-only
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> game_schemas.GameResponse:
    """
    Update game session.

    Authorization:
    - Game host can update their own game
    - Bot Managers can update any game in the guild
    - Guild admins (MANAGE_GUILD) can update any game in the guild
    Accepts multipart/form-data for file uploads.
    """
    try:
        # Parse form data
        (
            scheduled_at_datetime,
            reminder_minutes_list,
            notify_role_ids_list,
            participants_list,
            removed_participant_ids_list,
        ) = _parse_update_form_data(
            scheduled_at,
            reminder_minutes,
            notify_role_ids,
            participants,
            removed_participant_ids,
        )

        # Build update request
        update_data = game_schemas.GameUpdateRequest(
            title=title,
            description=description,
            signup_instructions=signup_instructions,
            scheduled_at=scheduled_at_datetime,
            where=where,
            max_players=max_players,
            reminder_minutes=reminder_minutes_list,
            expected_duration_minutes=expected_duration_minutes,
            status=status,
            notify_role_ids=notify_role_ids_list,
            participants=participants_list,
            signup_method=signup_method,
            removed_participant_ids=removed_participant_ids_list,
        )

        # Process file uploads
        thumbnail_data, thumbnail_mime = await _process_image_upload(
            thumbnail, remove_thumbnail, "thumbnail", game_id
        )
        image_data, image_mime = await _process_image_upload(image, remove_image, "image", game_id)

        # Update game via service
        game = await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=current_user,
            role_service=role_service,
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime,
            image_data=image_data,
            image_mime_type=image_mime,
        )

        return await _build_game_response(game)

    except (resolver_module.ValidationError, ValueError) as e:
        _handle_game_operation_errors(e, update_data)


@router.delete("/{game_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> None:
    """
    Cancel game session.

    Authorization:
    - Game host can cancel their own game
    - Bot Managers can cancel any game in the guild
    - Guild admins (MANAGE_GUILD) can cancel any game in the guild

    Sets status to CANCELLED and publishes event.
    """
    try:
        await game_service.delete_game(
            game_id=game_id,
            current_user=current_user,
            role_service=role_service,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from None


@router.post("/{game_id}/join", response_model=participant_schemas.ParticipantResponse)
async def join_game(
    game_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> participant_schemas.ParticipantResponse:
    """
    Join game as participant.

    Validates game is open, user not already joined, and game not full.
    Verifies guild membership and required player roles before allowing join.
    """
    # Fetch game to verify authorization
    game = await game_service.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Game not found")

    # Verify user has access (guild membership + player roles)
    await permissions_deps.verify_game_access(
        game=game,
        user_discord_id=current_user.user.discord_id,
        access_token=current_user.access_token,
        db=game_service.db,
        role_service=role_service,
    )

    try:
        participant = await game_service.join_game(
            game_id=game_id,
            user_discord_id=current_user.user.discord_id,
        )

        # Resolve display name and avatar for the participant
        display_data_map = {}
        if participant.user and participant.user.discord_id and game.guild_id:
            display_name_resolver = await display_names_module.get_display_name_resolver()
            guild_discord_id = game.guild.guild_id
            display_data_map = await display_name_resolver.resolve_display_names_and_avatars(
                guild_discord_id, [participant.user.discord_id]
            )

        display_name = participant.display_name
        avatar_url = None
        if participant.user and participant.user.discord_id in display_data_map:
            display_name = display_data_map[participant.user.discord_id]["display_name"]
            avatar_url = display_data_map[participant.user.discord_id]["avatar_url"]

        return participant_schemas.ParticipantResponse(
            id=participant.id,
            game_session_id=participant.game_session_id,
            user_id=participant.user_id,
            discord_id=participant.user.discord_id if participant.user else None,
            display_name=display_name,
            avatar_url=avatar_url,
            joined_at=participant.joined_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            position_type=participant.position_type,
            position=participant.position,
        )

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/{game_id}/leave", status_code=http_status.HTTP_204_NO_CONTENT)
async def leave_game(
    game_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
) -> None:
    """
    Leave game as participant.

    Validates user is a participant and game not completed.
    """
    logger.info(
        "Leave game request: game_id=%s, user_discord_id=%s",
        game_id,
        current_user.user.discord_id,
    )
    try:
        await game_service.leave_game(
            game_id=game_id,
            user_discord_id=current_user.user.discord_id,
        )
        logger.info("User %s successfully left game %s", current_user.user.discord_id, game_id)
    except ValueError as e:
        logger.error("Leave game error: %s", e)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


async def _resolve_display_data(
    game: game_model.GameSession,
    partitioned: participant_sorting.PartitionedParticipants,
) -> tuple[dict[str, dict[str, str | None]], str | None]:
    """
    Resolve display names and avatars for participants and host.

    Args:
        game: Game session model with guild loaded
        partitioned: Partitioned participant data

    Returns:
        Tuple of (display_data_map, host_discord_id)
    """
    discord_user_ids = [p.user.discord_id for p in partitioned.all_sorted if p.user is not None]

    host_discord_id = game.host.discord_id if game.host else None
    if host_discord_id and host_discord_id not in discord_user_ids:
        discord_user_ids.append(host_discord_id)

    display_data_map = {}
    if discord_user_ids and game.guild_id:
        display_name_resolver = await display_names_module.get_display_name_resolver()
        guild_discord_id = game.guild.guild_id
        display_data_map = await display_name_resolver.resolve_display_names_and_avatars(
            guild_discord_id, discord_user_ids
        )

    return display_data_map, host_discord_id


async def _fetch_discord_names(
    game: game_model.GameSession,
) -> tuple[str | None, str | None]:
    """
    Fetch channel and guild names from Discord API.

    Args:
        game: Game session model with channel and guild loaded

    Returns:
        Tuple of (channel_name, guild_name)
    """
    channel_name = None
    if game.channel:
        channel_name = await fetch_channel_name_safe(game.channel.channel_id)

    guild_name = None
    if game.guild:
        guild_name = await fetch_guild_name_safe(game.guild.guild_id)

    return channel_name, guild_name


def _build_participant_responses(
    partitioned: participant_sorting.PartitionedParticipants,
    display_data_map: dict[str, dict[str, str | None]],
) -> list[participant_schemas.ParticipantResponse]:
    """
    Build ParticipantResponse objects from partitioned participants.

    Args:
        partitioned: Partitioned participant data
        display_data_map: Mapping of discord IDs to display data

    Returns:
        List of participant response objects
    """
    participant_responses = []
    for participant in partitioned.all_sorted:
        discord_id = participant.user.discord_id if participant.user else None
        display_name = participant.display_name
        avatar_url = None

        if discord_id and discord_id in display_data_map:
            display_name = display_data_map[discord_id]["display_name"]
            avatar_url = display_data_map[discord_id]["avatar_url"]

        participant_responses.append(
            participant_schemas.ParticipantResponse(
                id=participant.id,
                game_session_id=participant.game_session_id,
                user_id=participant.user_id,
                discord_id=discord_id,
                display_name=display_name,
                avatar_url=avatar_url,
                joined_at=datetime_utils.format_datetime_as_utc(participant.joined_at),
                position_type=participant.position_type,
                position=participant.position,
            )
        )

    return participant_responses


def _build_host_response(
    game: game_model.GameSession,
    host_discord_id: str | None,
    display_data_map: dict[str, dict[str, str | None]],
) -> participant_schemas.ParticipantResponse:
    """
    Build host participant response object.

    Args:
        game: Game session model
        host_discord_id: Discord ID of the host
        display_data_map: Mapping of discord IDs to display data

    Returns:
        Host participant response object
    """
    host_display_name = None
    host_avatar_url = None
    if host_discord_id and host_discord_id in display_data_map:
        host_display_name = display_data_map[host_discord_id]["display_name"]
        host_avatar_url = display_data_map[host_discord_id]["avatar_url"]

    return participant_schemas.ParticipantResponse(
        id=game.host_id,
        game_session_id=game.id,
        user_id=game.host_id,
        discord_id=host_discord_id,
        display_name=host_display_name,
        avatar_url=host_avatar_url,
        joined_at=datetime_utils.format_datetime_as_utc(game.created_at),
        position_type=ParticipantType.SELF_ADDED,
        position=0,
    )


async def _build_game_response(
    game: game_model.GameSession,
) -> game_schemas.GameResponse:
    """
    Build GameResponse from GameSession model with resolved display names.

    Args:
        game: Game session model with participants and guild loaded

    Returns:
        Game response schema with resolved display names and sorted participants
    """
    participant_count = len(game.participants)
    partitioned = participant_sorting.partition_participants(game.participants, game.max_players)

    display_data_map, host_discord_id = await _resolve_display_data(game, partitioned)
    channel_name, guild_name = await _fetch_discord_names(game)
    participant_responses = _build_participant_responses(partitioned, display_data_map)
    host_response = _build_host_response(game, host_discord_id, display_data_map)

    return game_schemas.GameResponse(
        id=game.id,
        title=game.title,
        description=game.description,
        signup_instructions=game.signup_instructions,
        scheduled_at=datetime_utils.format_datetime_as_utc(game.scheduled_at),
        where=game.where,
        max_players=game.max_players,
        guild_id=game.guild_id,
        guild_name=guild_name,
        channel_id=game.channel_id,
        channel_name=channel_name,
        message_id=game.message_id,
        host=host_response,
        reminder_minutes=game.reminder_minutes,
        expected_duration_minutes=game.expected_duration_minutes,
        notify_role_ids=game.notify_role_ids,
        status=game.status,
        signup_method=game.signup_method,
        participant_count=participant_count,
        participants=participant_responses,
        created_at=datetime_utils.format_datetime_as_utc(game.created_at),
        updated_at=datetime_utils.format_datetime_as_utc(game.updated_at),
        has_thumbnail=game.thumbnail_id is not None,
        has_image=game.banner_image_id is not None,
    )


@router.get("/{game_id}/thumbnail", operation_id="get_game_thumbnail")
@router.head("/{game_id}/thumbnail", operation_id="head_game_thumbnail")
async def get_game_thumbnail(
    game_id: str,
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
) -> Response:
    """Serve game thumbnail image."""
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Game not found")

    if not game.thumbnail:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No thumbnail for this game",
        )

    return Response(
        content=game.thumbnail.image_data,
        media_type=game.thumbnail.mime_type,
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{game_id}/image", operation_id="get_game_image")
@router.head("/{game_id}/image", operation_id="head_game_image")
async def get_game_image(
    game_id: str,
    game_service: Annotated[games_service.GameService, Depends(_get_game_service)],
) -> Response:
    """Serve game banner image."""
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Game not found")

    if not game.banner_image:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No banner image for this game",
        )

    return Response(
        content=game.banner_image.image_data,
        media_type=game.banner_image.mime_type,
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )
