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


"""Leave game button interaction handler."""

import logging
import uuid

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.utils import (
    get_participant_count,
    send_deferred_response,
    send_error_message,
    send_success_message,
)
from shared.database import get_db_session
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
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
            if result["error"]:
                await send_error_message(interaction, result["error"])
            return

        game = result["game"]
        participant_count = result["participant_count"]
        participant = result["participant"]

        notif_result = await db.execute(
            select(NotificationSchedule).where(
                NotificationSchedule.participant_id == participant.id,
                NotificationSchedule.sent == False,  # noqa: E712
            )
        )
        join_not_sent = notif_result.scalar_one_or_none() is not None

        # Delete participant from database
        await db.delete(participant)
        await db.commit()

        await publisher.publish_game_updated(
            game_id=game_id,
            guild_id=game.guild_id,
            updated_fields={"participants": True},
        )

    if not join_not_sent:
        await send_success_message(interaction, f"❌ You've left **{game.title}**")

    logger.info(
        "User %s left game %s (%s remaining)",
        user_discord_id,
        game_id,
        participant_count - 1,
    )


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
    result = await db.execute(
        select(GameSession)
        .options(selectinload(GameSession.guild))
        .where(GameSession.id == str(game_id))
    )
    game = result.scalar_one_or_none()

    if not game:
        return {"can_leave": False, "error": "Game not found"}

    if game.status == "COMPLETED":
        return {"can_leave": False, "error": "Cannot leave a completed game"}

    result = await db.execute(select(User).where(User.discord_id == user_discord_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"can_leave": False, "error": None}

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id == user.id)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        return {"can_leave": False, "error": None}

    participant_count = await get_participant_count(db, game_id)

    return {
        "can_leave": True,
        "game": game,
        "participant_count": participant_count,
        "participant": participant,
    }
