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
Calendar export REST API endpoints.

Provides iCal export functionality for individual game sessions.
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.api.auth import roles as roles_module
from services.api.dependencies import auth as auth_deps
from services.api.dependencies import permissions as permissions_deps
from services.api.services.calendar_export import CalendarExportService
from shared import database
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def generate_calendar_filename(game_title: str, scheduled_at: datetime) -> str:
    """
    Generate descriptive filename for calendar download.

    Args:
        game_title: Game title (may contain special characters)
        scheduled_at: Game scheduled datetime

    Returns:
        Safe filename: "Game-Title_YYYY-MM-DD.ics"

    Examples:
        >>> generate_calendar_filename("D&D Campaign", datetime(2025, 11, 15))
        'D-D-Campaign_2025-11-15.ics'
        >>> generate_calendar_filename("Poker Night!", datetime(2025, 12, 25))
        'Poker-Night_2025-12-25.ics'
    """
    # Replace special characters with spaces (preserves word boundaries)
    safe_title = re.sub(r"[^\w\s-]", " ", game_title).strip()

    # Replace multiple spaces/hyphens with single hyphen
    safe_title = re.sub(r"[-\s]+", "-", safe_title)

    # Truncate if too long (max 100 chars before date)
    if len(safe_title) > 100:
        safe_title = safe_title[:100].rstrip("-")

    # Format date
    date_str = scheduled_at.strftime("%Y-%m-%d")

    return f"{safe_title}_{date_str}.ics"


@router.get(
    "/game/{game_id}",
    summary="Export game to iCal",
    description="Export a single game to iCal format (requires host or participant access)",
)
async def export_game(
    game_id: str,
    # B008: FastAPI dependency injection requires Depends() in default arguments
    user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),  # noqa: B008
    db: AsyncSession = Depends(database.get_db),  # noqa: B008
    role_service: roles_module.RoleVerificationService = Depends(  # noqa: B008
        permissions_deps.get_role_service
    ),
) -> Response:
    """
    Export a single game to iCal format.

    Only the host, participants, administrators, or bot managers can export a game.
    """
    # Fetch game with relationships to check permissions
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == game_id)
        .options(
            selectinload(GameSession.guild),
            selectinload(GameSession.host),
            selectinload(GameSession.participants).selectinload(GameParticipant.user),
        )
    )
    game = result.scalar_one_or_none()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Check permission using centralized helper
    can_export = await permissions_deps.can_export_game(
        game_host_id=game.host_id,
        game_participants=game.participants,
        guild_id=game.guild.guild_id,
        user_id=user.user.id,
        discord_id=user.user.discord_id,
        role_service=role_service,
        db=db,
        access_token=user.access_token,
        current_user=user,
    )

    service = CalendarExportService(db)

    try:
        ical_data = await service.export_game(
            game_id, user.user.id, user.user.discord_id, can_export
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Generate descriptive filename
    filename = generate_calendar_filename(game.title, game.scheduled_at)

    return Response(
        content=ical_data,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
