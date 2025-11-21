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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import discord_client as discord_client_module
from services.api.dependencies import auth as auth_deps
from services.api.services import display_names as display_names_module
from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared import database
from shared.messaging import publisher as messaging_publisher
from shared.models import game as game_model
from shared.schemas import auth as auth_schemas
from shared.schemas import game as game_schemas
from shared.schemas import participant as participant_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/games", tags=["games"])

# ruff: noqa: B008


def _get_game_service(
    db: AsyncSession = Depends(database.get_db),
) -> games_service.GameService:
    """Get game service instance with dependencies."""
    event_publisher = messaging_publisher.EventPublisher()
    discord_client = discord_client_module.get_discord_client()
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
                "form_data": game_data.model_dump(),
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
) -> game_schemas.GameListResponse:
    """
    List games with optional filters.

    Supports filtering by guild, channel, and status with pagination.
    """
    games, total = await game_service.list_games(
        guild_id=guild_id,
        channel_id=channel_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    game_responses = [await _build_game_response(game) for game in games]

    return game_schemas.GameListResponse(
        games=game_responses,
        total=total,
    )


@router.get("/{game_id}", response_model=game_schemas.GameResponse)
async def get_game(
    game_id: str,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
) -> game_schemas.GameResponse:
    """Get game session by ID."""
    game = await game_service.get_game(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None

    return await _build_game_response(game)


@router.put("/{game_id}", response_model=game_schemas.GameResponse)
async def update_game(
    game_id: str,
    update_data: game_schemas.GameUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
) -> game_schemas.GameResponse:
    """
    Update game session.

    Only the game host can update. All fields are optional.
    """
    try:
        game = await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            host_user_id=current_user.user.id,
        )

        return await _build_game_response(game)

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: str,
    current_user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    game_service: games_service.GameService = Depends(_get_game_service),
) -> None:
    """
    Cancel game session.

    Only the game host can cancel. Sets status to CANCELLED and publishes event.
    """
    try:
        await game_service.delete_game(
            game_id=game_id,
            host_user_id=current_user.user.id,
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
) -> participant_schemas.ParticipantResponse:
    """
    Join game as participant.

    Validates game is open, user not already joined, and game not full.
    """
    try:
        participant = await game_service.join_game(
            game_id=game_id,
            user_discord_id=current_user.user.discord_id,
        )

        return participant_schemas.ParticipantResponse(
            id=participant.id,
            game_session_id=participant.game_session_id,
            user_id=participant.user_id,
            discord_id=participant.user.discord_id if participant.user else None,
            display_name=participant.display_name,
            joined_at=participant.joined_at.isoformat(),
            status=participant.status,
            is_pre_populated=participant.is_pre_populated,
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
        logger.info(f"User {current_user.user.discord_id} successfully left game {game_id}")
    except ValueError as e:
        logger.error(f"Leave game error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


async def _build_game_response(game: game_model.GameSession) -> game_schemas.GameResponse:
    """
    Build GameResponse from GameSession model with resolved display names.

    Args:
        game: Game session model with participants and guild loaded

    Returns:
        Game response schema with resolved display names
    """
    participant_count = sum(1 for p in game.participants if p.user_id is not None)

    discord_user_ids = [p.user.discord_id for p in game.participants if p.user is not None]

    # Add host to the list of users to resolve
    host_discord_id = game.host.discord_id if game.host else None
    if host_discord_id and host_discord_id not in discord_user_ids:
        discord_user_ids.append(host_discord_id)

    display_name_resolver = await display_names_module.get_display_name_resolver()
    display_names_map = {}

    if discord_user_ids:
        if game.guild_id:
            guild_discord_id = game.guild.guild_id
            display_names_map = await display_name_resolver.resolve_display_names(
                guild_discord_id, discord_user_ids
            )

    participant_responses = []
    for participant in game.participants:
        discord_id = participant.user.discord_id if participant.user else None
        display_name = participant.display_name

        if discord_id and discord_id in display_names_map:
            display_name = display_names_map[discord_id]

        participant_responses.append(
            participant_schemas.ParticipantResponse(
                id=participant.id,
                game_session_id=participant.game_session_id,
                user_id=participant.user_id,
                discord_id=discord_id,
                display_name=display_name,
                joined_at=participant.joined_at.isoformat(),
                status=participant.status,
                is_pre_populated=participant.is_pre_populated,
            )
        )

    # Build host participant response
    host_display_name = None
    if host_discord_id and host_discord_id in display_names_map:
        host_display_name = display_names_map[host_discord_id]

    host_response = participant_schemas.ParticipantResponse(
        id=game.host_id,
        game_session_id=game.id,
        user_id=game.host_id,
        discord_id=host_discord_id,
        display_name=host_display_name,
        joined_at=game.created_at.isoformat(),
        status="JOINED",
        is_pre_populated=False,
    )

    return game_schemas.GameResponse(
        id=game.id,
        title=game.title,
        description=game.description,
        scheduled_at=game.scheduled_at.isoformat(),
        scheduled_at_unix=int(game.scheduled_at.timestamp()),
        max_players=game.max_players,
        guild_id=game.guild_id,
        channel_id=game.channel_id,
        message_id=game.message_id,
        host=host_response,
        rules=game.rules,
        reminder_minutes=game.reminder_minutes,
        status=game.status,
        participant_count=participant_count,
        participants=participant_responses,
        created_at=game.created_at.isoformat(),
        updated_at=game.updated_at.isoformat(),
    )
