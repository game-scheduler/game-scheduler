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


"""Join game button interaction handler."""

import logging
import uuid
from datetime import timedelta

import discord
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.bot.auth.role_checker import RoleChecker
from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.utils import (
    get_participant_count,
    send_deferred_response,
    send_error_message,
    upsert_interaction_display_name,
)
from shared.database import get_db_session
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant, ParticipantType
from shared.models.user import User
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import resolve_role_position

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

        role_checker = RoleChecker(bot=interaction.client, db_session=db)
        position_type, position = await _resolve_bot_role_position(interaction, game, role_checker)

        # Create participant in database
        participant = GameParticipant(
            game_session_id=str(game_id),
            user_id=user_result.id,
            position_type=position_type,
            position=position,
        )
        db.add(participant)
        try:
            await db.commit()
            await db.refresh(participant)
        except IntegrityError:
            logger.info("User %s attempted duplicate join for game %s", user_discord_id, game_id)
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

        await upsert_interaction_display_name(db, interaction, game.guild.guild_id, user_discord_id)

        await publisher.publish_game_updated(
            game_id=game_id,
            guild_id=game.guild_id,
            updated_fields={"participants": True},
        )

    logger.info(
        "User %s joined game %s (%s/%s)",
        user_discord_id,
        game_id,
        participant_count + 1,
        resolve_max_players(game.max_players),
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
        - game: GameSession (with template eagerly loaded)
        - participant_count: int
    """
    result_game = await db.execute(
        select(GameSession)
        .options(selectinload(GameSession.template))
        .options(selectinload(GameSession.guild))
        .where(GameSession.id == str(game_id))
    )
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

    participant_count = await get_participant_count(db, game_id)

    return {
        "can_join": True,
        "user": user_result,
        "game": game,
        "participant_count": participant_count,
    }


async def _resolve_bot_role_position(
    interaction: discord.Interaction,
    game: GameSession,
    role_checker: RoleChecker,
) -> tuple[int, int]:
    """Resolve position_type and position from the interaction payload.

    Extracts role IDs from the Discord member object (zero extra API calls)
    and seeds the role cache as a side effect.

    Args:
        interaction: Discord interaction containing member role data
        game: GameSession with template loaded
        role_checker: RoleChecker for cache seeding

    Returns:
        (position_type, position) tuple
    """
    priority_role_ids = (game.template.signup_priority_role_ids or []) if game.template else []
    if not priority_role_ids or not isinstance(interaction.user, discord.Member):
        return (ParticipantType.SELF_ADDED, 0)

    guild_discord_id = str(interaction.guild_id)
    user_discord_id = str(interaction.user.id)
    user_role_ids = [str(r.id) for r in interaction.user.roles if str(r.id) != guild_discord_id]

    await role_checker.seed_user_roles(user_discord_id, guild_discord_id, user_role_ids)
    return resolve_role_position(user_role_ids, priority_role_ids)
