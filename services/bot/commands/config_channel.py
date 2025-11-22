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


"""Channel configuration slash command implementation."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.bot.commands.decorators import require_manage_channels
from shared.database import get_db_session
from shared.models import ChannelConfiguration, GuildConfiguration

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)


@require_manage_channels()
async def config_channel_command(
    interaction: Interaction,
    channel: discord.TextChannel | None = None,
    max_players: int | None = None,
    reminder_minutes: str | None = None,
    game_category: str | None = None,
    is_active: bool | None = None,
) -> None:
    """
    Configure channel-level settings that override guild defaults.

    Args:
        interaction: Discord interaction object
        channel: Channel to configure (defaults to current channel)
        max_players: Max players override (1-100, None to use guild default)
        reminder_minutes: Reminder times override (comma-separated minutes)
        game_category: Game category for this channel (e.g., "D&D", "Board Games")
        is_active: Enable/disable game posting in this channel
    """
    await interaction.response.defer(ephemeral=True)

    try:
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.followup.send(
                "❌ Could not determine the target channel.",
                ephemeral=True,
            )
            return

        async with get_db_session() as db:
            guild_config = await _get_guild_config(db, str(interaction.guild.id))
            if not guild_config:
                await interaction.followup.send(
                    "❌ Guild configuration not found. Please run `/config-guild` first.",
                    ephemeral=True,
                )
                return

            channel_config = await _get_or_create_channel_config(
                db,
                str(target_channel.id),
                target_channel.name,
                guild_config.id,
            )

            updated_fields = []

            if max_players is not None:
                if not 1 <= max_players <= 100:
                    await interaction.followup.send(
                        "❌ Max players must be between 1 and 100.",
                        ephemeral=True,
                    )
                    return
                channel_config.max_players = max_players
                updated_fields.append(f"Max Players: {max_players}")

            if reminder_minutes is not None:
                try:
                    reminders = [int(m.strip()) for m in reminder_minutes.split(",")]
                    if any(r < 0 for r in reminders):
                        raise ValueError("Negative minutes not allowed")
                    channel_config.reminder_minutes = reminders
                    updated_fields.append(f"Reminders: {', '.join(map(str, reminders))} min")
                except ValueError as e:
                    await interaction.followup.send(
                        f"❌ Invalid reminder format: {e!s}. "
                        "Use comma-separated numbers (e.g., '60,15').",
                        ephemeral=True,
                    )
                    return

            if game_category is not None:
                channel_config.game_category = game_category
                updated_fields.append(f"Category: {game_category}")

            if is_active is not None:
                channel_config.is_active = is_active
                status = "Enabled" if is_active else "Disabled"
                updated_fields.append(f"Status: {status}")

            if not updated_fields:
                embed = _create_config_display_embed(target_channel, channel_config, guild_config)
                await interaction.followup.send(
                    "Current channel configuration:",
                    embed=embed,
                    ephemeral=True,
                )
                return

            await db.commit()

            embed = _create_config_display_embed(target_channel, channel_config, guild_config)
            message = "✅ Channel configuration updated:\n" + "\n".join(
                f"• {field}" for field in updated_fields
            )
            await interaction.followup.send(
                message,
                embed=embed,
                ephemeral=True,
            )

    except Exception as e:
        logger.exception("Error updating channel configuration")
        await interaction.followup.send(
            f"❌ An error occurred: {e!s}",
            ephemeral=True,
        )


async def _get_guild_config(db: AsyncSession, guild_id: str) -> GuildConfiguration | None:
    """
    Get existing guild configuration.

    Args:
        db: Database session
        guild_id: Discord guild ID

    Returns:
        Guild configuration record or None
    """
    result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.guild_id == guild_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_channel_config(
    db: AsyncSession,
    channel_id: str,
    channel_name: str,
    guild_config_id: int,
) -> ChannelConfiguration:
    """
    Get existing channel config or create new one.

    Args:
        db: Database session
        channel_id: Discord channel ID
        channel_name: Discord channel name
        guild_config_id: Guild configuration ID

    Returns:
        Channel configuration record
    """
    result = await db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.channel_id == channel_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = ChannelConfiguration(
            guild_id=guild_config_id,
            channel_id=channel_id,
            channel_name=channel_name,
            is_active=True,
            max_players=None,
            reminder_minutes=None,
            allowed_host_role_ids=None,
            game_category=None,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


def _create_config_display_embed(
    channel: discord.TextChannel,
    config: ChannelConfiguration,
    guild_config: GuildConfiguration,
) -> discord.Embed:
    """
    Create Discord embed showing channel configuration with inheritance.

    Args:
        channel: Discord channel
        config: Channel configuration
        guild_config: Guild configuration

    Returns:
        Discord embed with configuration details
    """
    embed = discord.Embed(
        title=f"⚙️ Channel Configuration: #{channel.name}",
        color=discord.Color.blue(),
    )

    status_emoji = "✅" if config.is_active else "❌"
    embed.add_field(
        name="Status",
        value=f"{status_emoji} {'Active' if config.is_active else 'Inactive'}",
        inline=True,
    )

    embed.add_field(
        name="Category",
        value=config.game_category or "None",
        inline=True,
    )

    max_players = (
        str(config.max_players)
        if config.max_players
        else f"{guild_config.default_max_players} (guild default)"
    )
    embed.add_field(
        name="Max Players",
        value=max_players,
        inline=True,
    )

    if config.reminder_minutes:
        reminders_text = ", ".join(map(str, config.reminder_minutes)) + " min"
    else:
        guild_reminders = ", ".join(map(str, guild_config.default_reminder_minutes))
        reminders_text = f"{guild_reminders} min (guild default)"

    embed.add_field(
        name="Reminders",
        value=reminders_text,
        inline=True,
    )

    return embed


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register config_channel command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(
        name="config-channel",
        description="Configure channel-level settings (Admin only)",
    )
    @app_commands.describe(
        channel="Channel to configure (defaults to current channel)",
        max_players="Max players override (1-100)",
        reminder_minutes="Reminder times override (e.g., '60,15')",
        default_rules="Rules override for this channel",
        game_category="Game category (e.g., 'D&D', 'Board Games')",
        is_active="Enable/disable game posting in this channel",
    )
    async def config_channel_slash(
        interaction: Interaction,
        channel: discord.TextChannel | None = None,
        max_players: int | None = None,
        reminder_minutes: str | None = None,
        game_category: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        await config_channel_command(
            interaction,
            channel,
            max_players,
            reminder_minutes,
            game_category,
            is_active,
        )

    logger.info("Registered /config-channel command")


__all__ = ["config_channel_command", "setup"]
