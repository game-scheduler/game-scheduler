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

from services.bot.config import get_config
from services.bot.utils.discord_format import (
    format_discord_mention,
    format_discord_timestamp,
    format_duration,
    format_participant_list,
)
from services.bot.views.game_view import GameView
from shared.utils.limits import MAX_STRING_DISPLAY_LENGTH


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
        where: str | None = None,
        game_id: str | None = None,
        host_display_name: str | None = None,
        host_avatar_url: str | None = None,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
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
            where: Optional game location
            game_id: Optional game UUID for calendar download link
            host_display_name: Optional host display name for embed author
            host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
            thumbnail_url: Optional thumbnail image URL
            image_url: Optional banner image URL

        Returns:
            Configured Discord embed
        """
        # Truncate description for Discord message
        truncated_description = description
        if description and len(description) > MAX_STRING_DISPLAY_LENGTH:
            truncated_description = description[: MAX_STRING_DISPLAY_LENGTH - 3] + "..."

        calendar_url = None
        if game_id:
            config = get_config()
            calendar_url = f"{config.frontend_url}/download-calendar/{game_id}"

        embed = discord.Embed(
            title=game_title,
            url=calendar_url,
            description=truncated_description,
            color=GameMessageFormatter._get_status_color(status),
        )

        # Set host as author with avatar if display name provided
        if host_display_name:
            if host_avatar_url:
                embed.set_author(name=f"Host: {host_display_name}", icon_url=host_avatar_url)
            else:
                embed.set_author(name=f"Host: {host_display_name}")

        # Field order matches web layout: When, Duration+Where, Channel, Participants
        when_value = (
            f"{format_discord_timestamp(scheduled_at, 'F')}\n"
            f"({format_discord_timestamp(scheduled_at, 'R')})"
        )
        if calendar_url:
            when_value += f" 📅 [Download]({calendar_url})"

        if expected_duration_minutes:
            duration_text = format_duration(expected_duration_minutes)
            when_value += f"\nDuration {duration_text}"
        if where:
            when_value += f"\nWhere: {where}"

        embed.add_field(name="\u200b", value=when_value, inline=False)

        if channel_id:
            embed.add_field(name="Voice Channel", value=f"<#{channel_id}>", inline=False)

        # Host is displayed in author field if host_display_name provided
        # Otherwise show as field for backward compatibility
        if not host_display_name:
            embed.add_field(name="Host", value=format_discord_mention(host_id), inline=False)

        if participant_ids:
            embed.add_field(
                name=f"Participants ({current_count}/{max_players})",
                value=format_participant_list(participant_ids, max_display=15),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"Participants ({current_count}/{max_players})",
                value="No participants yet",
                inline=False,
            )

        if overflow_ids:
            overflow_text = format_participant_list(overflow_ids, max_display=10)
            embed.add_field(
                name=f"Waitlist ({len(overflow_ids)})",
                value=overflow_text,
                inline=False,
            )

        from shared.models.game import GameStatus as GameStatusEnum

        # Get display name from enum if possible, fallback to raw status
        status_display = status
        try:
            status_display = GameStatusEnum(status).display_name
        except (ValueError, AttributeError):
            pass

        embed.set_footer(text=f"Status: {status_display}")

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        if image_url:
            embed.set_image(url=image_url)

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
            name="📅 Start Time",
            value=format_discord_timestamp(scheduled_at, "F"),
            inline=False,
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
    signup_method: str,
    channel_id: str | None = None,
    signup_instructions: str | None = None,
    expected_duration_minutes: int | None = None,
    notify_role_ids: list[str] | None = None,
    where: str | None = None,
    host_display_name: str | None = None,
    host_avatar_url: str | None = None,
    has_thumbnail: bool = False,
    has_image: bool = False,
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
        signup_method: Signup method (SELF_SIGNUP or HOST_SELECTED)
        channel_id: Optional voice channel ID
        signup_instructions: Optional signup instructions
        expected_duration_minutes: Optional expected game duration in minutes
        notify_role_ids: Optional list of Discord role IDs to mention
        where: Optional game location
        host_display_name: Optional host display name for embed author
        host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
        has_thumbnail: Whether game has a thumbnail image
        has_image: Whether game has a banner image

    Returns:
        Tuple of (content, embed, view) where content contains role mentions if any
        Tuple of (embed, view) ready to send to Discord
    """
    formatter = GameMessageFormatter()

    config = get_config()
    thumbnail_url = None
    image_url = None

    if has_thumbnail:
        thumbnail_url = f"{config.api_base_url}/api/v1/games/{game_id}/thumbnail"

    if has_image:
        image_url = f"{config.api_base_url}/api/v1/games/{game_id}/image"

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
        where=where,
        game_id=game_id,
        host_display_name=host_display_name,
        host_avatar_url=host_avatar_url,
        thumbnail_url=thumbnail_url,
        image_url=image_url,
    )

    view = GameView.from_game_data(
        game_id=game_id,
        current_players=current_count,
        max_players=max_players,
        status=status,
        signup_method=signup_method,
    )

    # Format role mentions for message content (appears above embed)
    content = None
    if notify_role_ids:
        role_mentions = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])
        content = role_mentions

    return content, embed, view
