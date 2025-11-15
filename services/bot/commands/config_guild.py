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


"""Guild configuration slash command implementation."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.commands.decorators import require_manage_guild
from shared.database import get_db_session
from shared.models import GuildConfiguration

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)


@require_manage_guild()
async def config_guild_command(
    interaction: Interaction,
    max_players: int | None = None,
    reminder_minutes: str | None = None,
    default_rules: str | None = None,
) -> None:
    """
    Configure guild-level default settings for games.

    Args:
        interaction: Discord interaction object
        max_players: Default max players for games (1-100)
        reminder_minutes: Comma-separated reminder times in minutes (e.g., "60,15")
        default_rules: Default rules text for all games
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
            guild_config = await _get_or_create_guild_config(
                db, str(interaction.guild.id), interaction.guild.name
            )

            updated_fields = []

            if max_players is not None:
                if not 1 <= max_players <= 100:
                    await interaction.followup.send(
                        "❌ Max players must be between 1 and 100.",
                        ephemeral=True,
                    )
                    return
                guild_config.default_max_players = max_players
                updated_fields.append(f"Max Players: {max_players}")

            if reminder_minutes is not None:
                try:
                    reminders = [int(m.strip()) for m in reminder_minutes.split(",")]
                    if any(r < 0 for r in reminders):
                        raise ValueError("Negative minutes not allowed")
                    guild_config.default_reminder_minutes = reminders
                    updated_fields.append(f"Reminders: {', '.join(map(str, reminders))} min")
                except ValueError as e:
                    await interaction.followup.send(
                        f"❌ Invalid reminder format: {e!s}. "
                        "Use comma-separated numbers (e.g., '60,15').",
                        ephemeral=True,
                    )
                    return

            if default_rules is not None:
                guild_config.default_rules = default_rules
                rules_preview = (
                    default_rules[:50] + "..." if len(default_rules) > 50 else default_rules
                )
                updated_fields.append(f"Rules: {rules_preview}")

            if not updated_fields:
                embed = _create_config_display_embed(interaction.guild, guild_config)
                await interaction.followup.send(
                    "Current guild configuration:",
                    embed=embed,
                    ephemeral=True,
                )
                return

            await db.commit()

            embed = _create_config_display_embed(interaction.guild, guild_config)
            message = "✅ Guild configuration updated:\n" + "\n".join(
                f"• {field}" for field in updated_fields
            )
            await interaction.followup.send(
                message,
                embed=embed,
                ephemeral=True,
            )

    except Exception as e:
        logger.exception("Error updating guild configuration")
        await interaction.followup.send(
            f"❌ An error occurred: {e!s}",
            ephemeral=True,
        )


async def _get_or_create_guild_config(
    db: AsyncSession, guild_id: str, guild_name: str
) -> GuildConfiguration:
    """
    Get existing guild config or create new one.

    Args:
        db: Database session
        guild_id: Discord guild ID
        guild_name: Discord guild name

    Returns:
        Guild configuration record
    """
    result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.guild_id == guild_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = GuildConfiguration(
            guild_id=guild_id,
            guild_name=guild_name,
            default_max_players=10,
            default_reminder_minutes=[60, 15],
            default_rules="",
            allowed_host_role_ids=[],
            require_host_role=False,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


def _create_config_display_embed(guild: discord.Guild, config: GuildConfiguration) -> discord.Embed:
    """
    Create Discord embed showing guild configuration.

    Args:
        guild: Discord guild
        config: Guild configuration

    Returns:
        Discord embed with configuration details
    """
    embed = discord.Embed(
        title=f"⚙️ Guild Configuration: {guild.name}",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="Default Max Players",
        value=str(config.default_max_players or "Not set"),
        inline=True,
    )

    reminders_text = (
        ", ".join(map(str, config.default_reminder_minutes)) + " min"
        if config.default_reminder_minutes
        else "Not set"
    )
    embed.add_field(
        name="Default Reminders",
        value=reminders_text,
        inline=True,
    )

    rules_value = config.default_rules or "Not set"
    if len(config.default_rules or "") > 100:
        rules_value = config.default_rules[:100] + "..."

    embed.add_field(
        name="Default Rules",
        value=rules_value,
        inline=False,
    )

    return embed


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register config_guild command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(
        name="config-guild",
        description="Configure guild-level default settings (Admin only)",
    )
    @app_commands.describe(
        max_players="Default max players for games (1-100)",
        reminder_minutes="Comma-separated reminder times in minutes (e.g., '60,15')",
        default_rules="Default rules text for all games",
    )
    async def config_guild_slash(
        interaction: Interaction,
        max_players: int | None = None,
        reminder_minutes: str | None = None,
        default_rules: str | None = None,
    ) -> None:
        await config_guild_command(interaction, max_players, reminder_minutes, default_rules)

    logger.info("Registered /config-guild command")


__all__ = ["config_guild_command", "setup"]
