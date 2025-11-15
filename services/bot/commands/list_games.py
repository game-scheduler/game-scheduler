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


"""List games slash command implementation."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session
from shared.models import ChannelConfiguration, GameSession, GuildConfiguration

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)


async def list_games_command(
    interaction: Interaction,
    channel: discord.TextChannel | None = None,
    show_all: bool = False,
) -> None:
    """
    List scheduled games in the current channel or all channels.

    Args:
        interaction: Discord interaction object
        channel: Specific channel to list games from (optional)
        show_all: Whether to show games from all channels in guild
    """
    await interaction.response.defer(ephemeral=True)

    try:
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with get_db_session() as db:
            if show_all:
                games = await _get_all_guild_games(db, str(interaction.guild.id))
                title = f"📅 All Scheduled Games in {interaction.guild.name}"
            elif channel:
                games = await _get_channel_games(db, str(channel.id))
                title = f"📅 Scheduled Games in #{channel.name}"
            else:
                if not interaction.channel or not isinstance(
                    interaction.channel, discord.TextChannel
                ):
                    await interaction.followup.send(
                        "❌ Could not determine the current channel.",
                        ephemeral=True,
                    )
                    return
                games = await _get_channel_games(db, str(interaction.channel.id))
                title = f"📅 Scheduled Games in #{interaction.channel.name}"

            if not games:
                await interaction.followup.send(
                    "No scheduled games found.",
                    ephemeral=True,
                )
                return

            embed = _create_games_list_embed(title, games)
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.exception("Error listing games")
        await interaction.followup.send(
            f"❌ An error occurred: {e!s}",
            ephemeral=True,
        )


async def _get_channel_games(db: AsyncSession, channel_id: str) -> list[GameSession]:
    """
    Fetch scheduled games for a specific channel.

    Args:
        db: Database session
        channel_id: Discord channel ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(ChannelConfiguration)
        .where(ChannelConfiguration.channel_id == channel_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def _get_all_guild_games(db: AsyncSession, guild_id: str) -> list[GameSession]:
    """
    Fetch all scheduled games for a guild.

    Args:
        db: Database session
        guild_id: Discord guild ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(GuildConfiguration)
        .where(GuildConfiguration.guild_id == guild_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


def _create_games_list_embed(title: str, games: list[GameSession]) -> discord.Embed:
    """
    Create Discord embed for games list.

    Args:
        title: Embed title
        games: List of game sessions

    Returns:
        Discord embed with games list
    """
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue(),
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
        embed.set_footer(text=f"{len(games)} game(s) found")

    return embed


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register list_games command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(name="list-games", description="List scheduled games")
    @app_commands.describe(
        channel="Specific channel to list games from (optional)",
        show_all="Show games from all channels in this server",
    )
    async def list_games_slash(
        interaction: Interaction,
        channel: discord.TextChannel | None = None,
        show_all: bool = False,
    ) -> None:
        await list_games_command(interaction, channel, show_all)

    logger.info("Registered /list-games command")


__all__ = ["list_games_command", "setup"]
