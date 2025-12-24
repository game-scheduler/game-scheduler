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


"""Join game button interaction handler."""

import logging
import uuid
from datetime import timedelta

import discord
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.utils import (
    send_deferred_response,
    send_error_message,
)
from shared.database import get_db_session
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant
from shared.models.user import User
from shared.utils.games import resolve_max_players

logger = logging.getLogger(__name__)


async def handle_join_game(
    interaction: discord.Interaction, game_id: str, publisher: BotEventPublisher
) -> None:
    """Handle join game button interaction.

    Args:
        interaction: Discord interaction from button click
        game_id: Game session ID from custom_id
        publisher: Bot event publisher

    Validates user can join game, publishes event to RabbitMQ,
    and sends confirmation message.
    """
    await send_deferred_response(interaction)

    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        await send_error_message(interaction, "Invalid game ID")
        return

    user_discord_id = str(interaction.user.id)

    async with get_db_session() as db:
        result = await _validate_join_game(db, game_uuid, user_discord_id)

        if not result["can_join"]:
            await send_error_message(interaction, result["error"])
            return

        game = result["game"]
        user_result = result["user"]
        participant_count = result["participant_count"]

        # Create participant in database
        participant = GameParticipant(
            game_session_id=str(game_id),
            user_id=user_result.id,
        )
        db.add(participant)
        try:
            await db.commit()
            await db.refresh(participant)
        except IntegrityError:
            logger.info(f"User {user_discord_id} attempted duplicate join for game {game_id}")
            return

        # Create delayed join notification schedule
        schedule = NotificationSchedule(
            game_id=str(game_id),
            participant_id=participant.id,
            notification_type="join_notification",
            notification_time=utc_now() + timedelta(seconds=60),
            sent=False,
            game_scheduled_at=game.scheduled_at,
            reminder_minutes=None,
        )
        db.add(schedule)
        await db.commit()

    await publisher.publish_game_updated(game_id=game_id, updated_fields={"participants": True})

    # Update button interaction view (no DM notification here)
    await interaction.edit_original_response(
        content=f"✅ You've joined **{game.title}**!",
        view=None,
    )

    logger.info(
        f"User {user_discord_id} joined game {game_id} "
        f"({participant_count + 1}/{resolve_max_players(game.max_players)})"
    )


async def _validate_join_game(db: AsyncSession, game_id: uuid.UUID, user_discord_id: str) -> dict:
    """Validate user can join game.

    Args:
        db: Database session
        game_id: Game session UUID
        user_discord_id: Discord user ID

    Returns:
        Dictionary with validation results:
        - can_join: bool
        - error: str (if can_join is False)
        - user: User
        - game: GameSession
        - participant_count: int
    """
    result_game = await db.execute(select(GameSession).where(GameSession.id == str(game_id)))
    game = result_game.scalar_one_or_none()

    if not game:
        return {"can_join": False, "error": "Game not found"}

    if game.status != "SCHEDULED":
        return {"can_join": False, "error": "Game has already started or is completed"}

    result_user = await db.execute(select(User).where(User.discord_id == user_discord_id))
    user_result = result_user.scalar_one_or_none()

    if not user_result:
        user_result = User(discord_id=user_discord_id)
        db.add(user_result)
        await db.flush()

    # Count current participants
    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id.isnot(None))
    )
    participant_count = len(result.scalars().all())

    return {
        "can_join": True,
        "user": user_result,
        "game": game,
        "participant_count": participant_count,
    }
