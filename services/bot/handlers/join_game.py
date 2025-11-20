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
        user = result["user"]
        participant_count = result["participant_count"]

        # Create participant in database
        participant = GameParticipant(
            game_session_id=str(game_id),
            user_id=user.id,
        )
        db.add(participant)
        await db.commit()

    await publisher.publish_player_joined(
        game_id=game_id,
        player_id=user_discord_id,
        player_count=participant_count + 1,
        max_players=game.max_players or 10,
    )

    await send_success_message(interaction, f"You've joined **{game.title}**!")

    logger.info(
        f"User {user_discord_id} joined game {game_id} "
        f"({participant_count + 1}/{game.max_players or 10})"
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
    result = await db.execute(select(GameSession).where(GameSession.id == str(game_id)))
    game = result.scalar_one_or_none()

    if not game:
        return {"can_join": False, "error": "Game not found"}

    if game.status != "SCHEDULED":
        return {"can_join": False, "error": "Game has already started or is completed"}

    result = await db.execute(select(User).where(User.discord_id == user_discord_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(discord_id=user_discord_id)
        db.add(user)
        await db.flush()

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id == user.id)
    )
    existing_participant = result.scalar_one_or_none()

    if existing_participant:
        return {"can_join": False, "error": "You've already joined this game"}

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id.isnot(None))
    )
    participant_count = len(result.scalars().all())

    max_players = game.max_players or 10

    if participant_count >= max_players:
        return {"can_join": False, "error": "Game is full"}

    return {"can_join": True, "user": user, "game": game, "participant_count": participant_count}
