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
Game management REST API endpoints.

Provides CRUD operations for game sessions with validation and authorization.
"""

import logging
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import roles as roles_module
from services.api.dependencies import auth as auth_deps
from services.api.dependencies import permissions as permissions_deps
from services.api.dependencies.discord import get_discord_client
from services.api.services import display_names as display_names_module
from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared import database
from shared.discord.client import fetch_channel_name_safe, fetch_guild_name_safe
from shared.messaging import publisher as messaging_publisher
from shared.models import game as game_model
from shared.schemas import auth as auth_schemas
from shared.schemas import game as game_schemas
from shared.schemas import participant as participant_schemas
from shared.utils import datetime_utils, participant_sorting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/games", tags=["games"])

# ruff: noqa: B008


def _get_game_service(
    db: AsyncSession = Depends(database.get_db),
) -> games_service.GameService:
    """Get game service instance with dependencies."""
    event_publisher = messaging_publisher.EventPublisher()
    discord_client = get_discord_client()
    participant_resolver = resolver_module.ParticipantResolver(discord_client)

    return games_service.GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=discord_client,
        participant_resolver=participant_resolver,
    )


@router.post("", response_model=game_schemas.GameResponse, status_code=201)
async def create_game(
    game_data: game_schemas.GameCreateRequest,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
) -> game_schemas.GameResponse:
    """
    Create new game session.

    Validates @mentions in initial_participants and creates GameParticipant records.
    Returns 422 if any @mentions cannot be resolved with disambiguation suggestions.
    """
    try:
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=current_user.user.id,
            access_token=current_user.access_token,
        )

        return await _build_game_response(game)

    except resolver_module.ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_mentions",
                "message": "Some @mentions could not be resolved",
                "invalid_mentions": e.invalid_mentions,
                "valid_participants": e.valid_participants,
                "form_data": game_data.model_dump(mode="json"),
            },
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("", response_model=game_schemas.GameListResponse)
async def list_games(
    guild_id: str | None = Query(None, description="Filter by guild UUID"),
    channel_id: str | None = Query(None, description="Filter by channel UUID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> game_schemas.GameListResponse:
    """
    List games with optional filters.

    Supports filtering by guild, channel, and status with pagination.
    Games are filtered by guild membership and template player role restrictions.
    """
    games, total = await game_service.list_games(
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
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> game_schemas.GameResponse:
    """Get game session by ID with guild membership and role verification."""
    game = await game_service.get_game(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None

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
    update_data: game_schemas.GameUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> game_schemas.GameResponse:
    """
    Update game session.

    Authorization:
    - Game host can update their own game
    - Bot Managers can update any game in the guild
    - Guild admins (MANAGE_GUILD) can update any game in the guild
    """
    try:
        game = await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=current_user,
            role_service=role_service,
        )

        return await _build_game_response(game)

    except resolver_module.ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_mentions",
                "message": "Some @mentions could not be resolved",
                "invalid_mentions": e.invalid_mentions,
                "valid_participants": e.valid_participants,
                "form_data": update_data.model_dump(mode="json"),
            },
        ) from None
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from None
        if "minimum players cannot be greater" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg) from None
        raise HTTPException(status_code=403, detail=error_msg) from None


@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: str,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
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
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.post("/{game_id}/join", response_model=participant_schemas.ParticipantResponse)
async def join_game(
    game_id: str,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> participant_schemas.ParticipantResponse:
    """
    Join game as participant.

    Validates game is open, user not already joined, and game not full.
    Verifies guild membership and required player roles before allowing join.
    """
    # Fetch game to verify authorization
    game = await game_service.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

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
            display_name_resolver = (
                await display_names_module.get_display_name_resolver()
            )
            guild_discord_id = game.guild.guild_id
            display_data_map = (
                await display_name_resolver.resolve_display_names_and_avatars(
                    guild_discord_id, [participant.user.discord_id]
                )
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
            joined_at=participant.joined_at.replace(tzinfo=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            pre_filled_position=participant.pre_filled_position,
        )

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{game_id}/leave", status_code=204)
async def leave_game(
    game_id: str,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
) -> None:
    """
    Leave game as participant.

    Validates user is a participant and game not completed.
    """
    logger.info(
        f"Leave game request: game_id={game_id}, user_discord_id={current_user.user.discord_id}"
    )
    try:
        await game_service.leave_game(
            game_id=game_id,
            user_discord_id=current_user.user.discord_id,
        )
        logger.info(
            f"User {current_user.user.discord_id} successfully left game {game_id}"
        )
    except ValueError as e:
        logger.error(f"Leave game error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


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

    sorted_participants = participant_sorting.sort_participants(game.participants)

    discord_user_ids = [
        p.user.discord_id for p in sorted_participants if p.user is not None
    ]

    # Add host to the list of users to resolve
    host_discord_id = game.host.discord_id if game.host else None
    if host_discord_id and host_discord_id not in discord_user_ids:
        discord_user_ids.append(host_discord_id)

    display_name_resolver = await display_names_module.get_display_name_resolver()
    display_data_map = {}

    if discord_user_ids:
        if game.guild_id:
            guild_discord_id = game.guild.guild_id
            display_data_map = (
                await display_name_resolver.resolve_display_names_and_avatars(
                    guild_discord_id, discord_user_ids
                )
            )

    # Fetch channel name from Discord API with caching
    channel_name = None
    if game.channel:
        channel_name = await fetch_channel_name_safe(game.channel.channel_id)

    # Fetch guild name from Discord API with caching
    guild_name = None
    if game.guild:
        guild_name = await fetch_guild_name_safe(game.guild.guild_id)

    participant_responses = []
    for participant in sorted_participants:
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
                pre_filled_position=participant.pre_filled_position,
            )
        )

    # Build host participant response
    host_display_name = None
    host_avatar_url = None
    if host_discord_id and host_discord_id in display_data_map:
        host_display_name = display_data_map[host_discord_id]["display_name"]
        host_avatar_url = display_data_map[host_discord_id]["avatar_url"]

    host_response = participant_schemas.ParticipantResponse(
        id=game.host_id,
        game_session_id=game.id,
        user_id=game.host_id,
        discord_id=host_discord_id,
        display_name=host_display_name,
        avatar_url=host_avatar_url,
        joined_at=datetime_utils.format_datetime_as_utc(game.created_at),
        pre_filled_position=None,
    )

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
        participant_count=participant_count,
        participants=participant_responses,
        created_at=datetime_utils.format_datetime_as_utc(game.created_at),
        updated_at=datetime_utils.format_datetime_as_utc(game.updated_at),
    )
