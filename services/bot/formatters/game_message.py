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


"""Game session message formatter.

This module provides utilities for formatting Discord messages for game sessions,
including announcements, updates, and participant lists.
"""

from datetime import datetime

import discord

from services.bot.utils.discord_format import (
    format_discord_mention,
    format_discord_timestamp,
    format_duration,
    format_game_status_emoji,
    format_participant_list,
)
from services.bot.views.game_view import GameView


class GameMessageFormatter:
    """Formatter for game session Discord messages.

    Formats game announcements and updates with Discord native mentions,
    timestamps, and embedded content.
    """

    @staticmethod
    def create_game_embed(
        game_title: str,
        description: str,
        scheduled_at: datetime,
        host_id: str,
        participant_ids: list[str],
        overflow_ids: list[str],
        current_count: int,
        max_players: int,
        status: str,
        channel_id: str | None = None,
        signup_instructions: str | None = None,
        expected_duration_minutes: int | None = None,
    ) -> discord.Embed:
        """Create an embed for a game session.

        Args:
            game_title: Game title
            description: Game description
            scheduled_at: When game is scheduled (UTC datetime)
            host_id: Discord ID of the game host
            participant_ids: List of confirmed participant Discord IDs (within max_players)
            overflow_ids: List of overflow participant Discord IDs (beyond max_players)
            current_count: Current confirmed participant count
            max_players: Maximum allowed participants
            status: Game status
            channel_id: Optional Discord channel ID
            signup_instructions: Optional signup instructions
            expected_duration_minutes: Optional expected game duration in minutes

        Returns:
            Configured Discord embed
        """
        status_emoji = format_game_status_emoji(status)

        # Truncate description to first 100 chars for Discord message
        truncated_description = description
        if description and len(description) > 100:
            truncated_description = description[:97] + "..."

        embed = discord.Embed(
            title=game_title,
            description=truncated_description,
            color=GameMessageFormatter._get_status_color(status),
            timestamp=scheduled_at,
        )

        embed.add_field(
            name="When",
            value=f"{format_discord_timestamp(scheduled_at, 'F')}\n"
            f"({format_discord_timestamp(scheduled_at, 'R')})",
            inline=False,
        )

        embed.add_field(name="Players", value=f"{current_count}/{max_players}", inline=True)

        embed.add_field(name="Host", value=format_discord_mention(host_id), inline=True)

        if expected_duration_minutes:
            duration_text = format_duration(expected_duration_minutes)
            embed.add_field(name="Duration", value=duration_text, inline=True)

        if channel_id:
            embed.add_field(name="Voice Channel", value=f"<#{channel_id}>", inline=True)

        if participant_ids:
            embed.add_field(
                name="Participants",
                value=format_participant_list(participant_ids, max_display=15),
                inline=False,
            )

        if overflow_ids:
            overflow_text = format_participant_list(overflow_ids, max_display=10)
            embed.add_field(
                name=f"Waitlist ({len(overflow_ids)})",
                value=overflow_text,
                inline=False,
            )

        if signup_instructions:
            embed.add_field(
                name="Signup Instructions",
                value=signup_instructions[:400]
                if len(signup_instructions) > 400
                else signup_instructions,
                inline=False,
            )

        embed.set_footer(text=f"Status: {status}")

        return embed

    @staticmethod
    def _get_status_color(status: str) -> discord.Color:
        """Get Discord color for game status.

        Args:
            status: Game status

        Returns:
            Discord color
        """
        color_map = {
            "SCHEDULED": discord.Color.green(),
            "IN_PROGRESS": discord.Color.blue(),
            "COMPLETED": discord.Color.gold(),
            "CANCELLED": discord.Color.red(),
        }
        return color_map.get(status, discord.Color.greyple())

    @staticmethod
    def create_notification_embed(
        game_title: str,
        scheduled_at: datetime,
        host_id: str,
        time_until: str,
    ) -> discord.Embed:
        """Create notification embed for game reminders.

        Args:
            game_title: Game title
            scheduled_at: When game is scheduled
            host_id: Discord ID of game host
            time_until: Human-readable time until game (e.g., "in 1 hour")

        Returns:
            Configured notification embed
        """
        embed = discord.Embed(
            title="🔔 Game Reminder",
            description=f"**{game_title}** starts {time_until}!",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="📅 Start Time", value=format_discord_timestamp(scheduled_at, "F"), inline=False
        )

        embed.add_field(name="🎯 Host", value=format_discord_mention(host_id), inline=False)

        return embed


def format_game_announcement(
    game_id: str,
    game_title: str,
    description: str,
    scheduled_at: datetime,
    host_id: str,
    participant_ids: list[str],
    overflow_ids: list[str],
    current_count: int,
    max_players: int,
    status: str,
    channel_id: str | None = None,
    signup_instructions: str | None = None,
    expected_duration_minutes: int | None = None,
    notify_role_ids: list[str] | None = None,
) -> tuple[str | None, discord.Embed, GameView]:
    """Format a complete game announcement with embed and buttons.

    Args:
        game_id: Game session UUID
        game_title: Game title
        description: Game description
        scheduled_at: When game is scheduled (UTC)
        host_id: Discord ID of game host
        participant_ids: List of confirmed participant Discord IDs (within max_players)
        overflow_ids: List of overflow participant Discord IDs (beyond max_players)
        current_count: Current confirmed participant count
        max_players: Maximum allowed participants
        status: Game status
        channel_id: Optional voice channel ID
        signup_instructions: Optional signup instructions
        expected_duration_minutes: Optional expected game duration in minutes
        notify_role_ids: Optional list of Discord role IDs to mention

    Returns:
        Tuple of (content, embed, view) where content contains role mentions if any
        Tuple of (embed, view) ready to send to Discord
    """
    formatter = GameMessageFormatter()

    embed = formatter.create_game_embed(
        game_title=game_title,
        description=description,
        scheduled_at=scheduled_at,
        host_id=host_id,
        participant_ids=participant_ids,
        overflow_ids=overflow_ids,
        current_count=current_count,
        max_players=max_players,
        status=status,
        channel_id=channel_id,
        signup_instructions=signup_instructions,
        expected_duration_minutes=expected_duration_minutes,
    )

    view = GameView.from_game_data(
        game_id=game_id,
        current_players=current_count,
        max_players=max_players,
        status=status,
    )

    # Format role mentions for message content (appears above embed)
    content = None
    if notify_role_ids:
        role_mentions = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])
        content = role_mentions

    return content, embed, view
