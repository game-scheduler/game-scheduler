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


"""Utilities for interaction handling."""

import logging
import uuid

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.participant import GameParticipant

logger = logging.getLogger(__name__)


async def send_deferred_response(interaction: discord.Interaction) -> None:
    """Send deferred response to Discord within 3-second timeout.

    Args:
        interaction: Discord interaction object
    """
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException as e:
            logger.warning(
                "Failed to defer interaction response for user %s: %s",
                interaction.user.id,
                e,
            )


async def get_participant_count(db: AsyncSession, game_id: uuid.UUID | str) -> int:
    """Get count of non-placeholder participants in a game.

    Args:
        db: Database session
        game_id: Game session ID (UUID or string)

    Returns:
        Number of participants with actual user IDs (excludes placeholders)
    """
    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id.isnot(None))
    )
    return len(result.scalars().all())


async def send_error_message(interaction: discord.Interaction, message: str) -> None:
    """Send error message as DM to user.

    Args:
        interaction: Discord interaction object
        message: Error message to display to user
    """
    try:
        await interaction.user.send(content=f"❌ {message}")
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning("Cannot send DM to user %s: %s", interaction.user.id, e)


async def send_success_message(interaction: discord.Interaction, message: str) -> None:
    """Send success message as DM to user.

    Args:
        interaction: Discord interaction object
        message: Success message to display to user
    """
    try:
        await interaction.user.send(content=message)
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning("Cannot send DM to user %s: %s", interaction.user.id, e)
