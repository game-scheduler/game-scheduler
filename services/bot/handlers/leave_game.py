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


"""Leave game button interaction handler."""

import logging
import uuid

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.utils import (
    send_deferred_response,
    send_error_message,
    send_success_message,
)
from shared.database import get_db_session
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.models.user import User

logger = logging.getLogger(__name__)


async def handle_leave_game(
    interaction: discord.Interaction, game_id: str, publisher: BotEventPublisher
) -> None:
    """Handle leave game button interaction.

    Args:
        interaction: Discord interaction from button click
        game_id: Game session ID from custom_id
        publisher: Bot event publisher

    Validates user is participant, publishes event to RabbitMQ,
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
        result = await _validate_leave_game(db, game_uuid, user_discord_id)

        if not result["can_leave"]:
            await send_error_message(interaction, result["error"])
            return

        game = result["game"]
        participant_count = result["participant_count"]
        participant = result["participant"]

        # Delete participant from database
        await db.delete(participant)
        await db.commit()

    await publisher.publish_player_left(
        game_id=game_id, player_id=user_discord_id, player_count=participant_count - 1
    )

    await send_success_message(interaction, f"You've left **{game.title}**")

    logger.info(f"User {user_discord_id} left game {game_id} ({participant_count - 1} remaining)")


async def _validate_leave_game(db: AsyncSession, game_id: uuid.UUID, user_discord_id: str) -> dict:
    """Validate user can leave game.

    Args:
        db: Database session
        game_id: Game session UUID
        user_discord_id: Discord user ID

    Returns:
        Dictionary with validation results:
        - can_leave: bool
        - error: str (if can_leave is False)
        - game: GameSession
        - participant_count: int
    """
    result = await db.execute(select(GameSession).where(GameSession.id == str(game_id)))
    game = result.scalar_one_or_none()

    if not game:
        return {"can_leave": False, "error": "Game not found"}

    if game.status == "COMPLETED":
        return {"can_leave": False, "error": "Cannot leave a completed game"}

    result = await db.execute(select(User).where(User.discord_id == user_discord_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"can_leave": False, "error": "You're not part of this game"}

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id == user.id)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        return {"can_leave": False, "error": "You're not part of this game"}

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id.isnot(None))
    )
    participant_count = len(result.scalars().all())

    return {
        "can_leave": True,
        "game": game,
        "participant_count": participant_count,
        "participant": participant,
    }
