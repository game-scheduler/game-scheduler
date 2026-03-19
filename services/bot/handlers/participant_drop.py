# Copyright 2026 Bret McKee
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


"""Bot handler for PARTICIPANT_DROP_DUE events."""

import logging
from typing import Any

import discord
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from services.bot.events.publisher import BotEventPublisher
from shared.database import get_bypass_db_session
from shared.message_formats import DMFormats
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant

logger = logging.getLogger(__name__)


async def handle_participant_drop_due(
    data: dict[str, Any],
    bot: discord.Client,
    publisher: BotEventPublisher,
) -> None:
    """
    Handle game.participant_drop_due event by removing the participant and
    sending a removal DM.

    Args:
        data: Event payload containing game_id and participant_id
        bot: Discord bot client for sending DMs
        publisher: Bot event publisher for GAME_UPDATED notification
    """
    game_id = data.get("game_id")
    participant_id = data.get("participant_id")

    if not game_id or not participant_id:
        logger.error("Missing game_id or participant_id in PARTICIPANT_DROP_DUE event")
        return

    async with get_bypass_db_session() as db:
        result = await db.execute(
            select(GameParticipant)
            .options(
                selectinload(GameParticipant.user),
                selectinload(GameParticipant.game),
            )
            .where(GameParticipant.id == participant_id)
        )
        participant = result.scalar_one_or_none()

        if not participant:
            logger.info("Participant %s not found for drop — already removed", participant_id)
            return

        game_title = participant.game.title
        guild_id = participant.game.guild_id
        discord_id = participant.user.discord_id if participant.user else None

        notif_result = await db.execute(
            select(NotificationSchedule).where(
                NotificationSchedule.participant_id == str(participant_id),
                NotificationSchedule.sent == False,  # noqa: E712
            )
        )
        welcome_not_sent = notif_result.scalar_one_or_none() is not None

        await db.delete(participant)
        await db.commit()

    logger.info("Dropped participant %s from game %s", participant_id, game_id)

    if discord_id and not welcome_not_sent:
        try:
            user = await bot.fetch_user(int(discord_id))
            await user.send(DMFormats.removal(game_title))
        except Exception:
            logger.warning("Failed to send removal DM to user %s", discord_id, exc_info=True)

    await publisher.publish_game_updated(
        game_id=game_id,
        guild_id=guild_id,
        updated_fields={"participants": True},
    )
