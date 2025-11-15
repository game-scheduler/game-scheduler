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


"""My games slash command implementation."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord import Interaction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session
from shared.models import GameParticipant, GameSession, User

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)


async def my_games_command(interaction: Interaction) -> None:
    """
    List games that the user is hosting or participating in.

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer(ephemeral=True)

    try:
        async with get_db_session() as db:
            user = await _get_or_create_user(db, str(interaction.user.id))

            hosted_games = await _get_hosted_games(db, user.id)
            participating_games = await _get_participating_games(db, user.id)

            if not hosted_games and not participating_games:
                await interaction.followup.send(
                    "You are not hosting or participating in any scheduled games.",
                    ephemeral=True,
                )
                return

            embeds = []

            if hosted_games:
                embed = _create_games_embed(
                    "🎮 Games You're Hosting",
                    hosted_games,
                    discord.Color.green(),
                )
                embeds.append(embed)

            if participating_games:
                embed = _create_games_embed(
                    "👥 Games You've Joined",
                    participating_games,
                    discord.Color.blue(),
                )
                embeds.append(embed)

            await interaction.followup.send(embeds=embeds, ephemeral=True)

    except Exception as e:
        logger.exception("Error fetching user's games")
        await interaction.followup.send(
            f"❌ An error occurred: {e!s}",
            ephemeral=True,
        )


async def _get_or_create_user(db: AsyncSession, discord_id: str) -> User:
    """
    Get existing user or create new user record.

    Args:
        db: Database session
        discord_id: Discord user ID

    Returns:
        User record
    """
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(discord_id=discord_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def _get_hosted_games(db: AsyncSession, user_id: int) -> list[GameSession]:
    """
    Fetch games hosted by user.

    Args:
        db: Database session
        user_id: Internal user ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.host_id == user_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def _get_participating_games(db: AsyncSession, user_id: int) -> list[GameSession]:
    """
    Fetch games user is participating in (excluding hosted games).

    Args:
        db: Database session
        user_id: Internal user ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(GameParticipant)
        .where(GameParticipant.user_id == user_id)
        .where(GameSession.host_id != user_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


def _create_games_embed(
    title: str, games: list[GameSession], color: discord.Color
) -> discord.Embed:
    """
    Create Discord embed for games list.

    Args:
        title: Embed title
        games: List of game sessions
        color: Embed color

    Returns:
        Discord embed with games list
    """
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(UTC),
    )

    for game in games[:10]:
        unix_timestamp = int(game.scheduled_at.timestamp())
        value = f"🕒 <t:{unix_timestamp}:F> (<t:{unix_timestamp}:R>)\n"
        if game.description:
            value += f"{game.description[:100]}\n"
        value += f"ID: `{game.id}`"

        embed.add_field(
            name=game.title,
            value=value,
            inline=False,
        )

    if len(games) > 10:
        embed.set_footer(text=f"Showing 10 of {len(games)} games")
    else:
        embed.set_footer(text=f"{len(games)} game(s)")

    return embed


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register my_games command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(name="my-games", description="Show your hosted and joined games")
    async def my_games_slash(interaction: Interaction) -> None:
        await my_games_command(interaction)

    logger.info("Registered /my-games command")


__all__ = ["my_games_command", "setup"]
