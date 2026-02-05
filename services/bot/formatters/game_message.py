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


"""Game session message formatter.

This module provides utilities for formatting Discord messages for game sessions,
including announcements, updates, and participant lists.
"""

import contextlib
import logging
from datetime import datetime

import discord

from services.bot.config import get_config
from services.bot.utils.discord_format import (
    format_discord_mention,
    format_discord_timestamp,
    format_duration,
    format_participant_list,
    format_user_or_placeholder,
)
from services.bot.views.game_view import GameView
from shared.models.game import GameStatus
from shared.utils.limits import MAX_STRING_DISPLAY_LENGTH

logger = logging.getLogger(__name__)


class GameMessageFormatter:
    """Formatter for game session Discord messages.

    Formats game announcements and updates with Discord native mentions,
    timestamps, and embedded content.
    """

    @staticmethod
    def _prepare_description_and_urls(
        description: str,
        game_id: str | None,
        thumbnail_url: str | None,
        image_url: str | None,
    ) -> tuple[str, str | None, str | None, str | None]:
        """Prepare truncated description and URLs for embed.

        Args:
            description: Original game description
            game_id: Optional game UUID
            thumbnail_url: Optional thumbnail URL
            image_url: Optional image URL

        Returns:
            Tuple of (truncated_description, calendar_url, thumbnail_url, image_url)
        """
        truncated_description = description
        if description and len(description) > MAX_STRING_DISPLAY_LENGTH:
            truncated_description = description[: MAX_STRING_DISPLAY_LENGTH - 3] + "..."

        calendar_url = None
        if game_id:
            config = get_config()
            calendar_url = f"{config.frontend_url}/download-calendar/{game_id}"

        return truncated_description, calendar_url, thumbnail_url, image_url

    @staticmethod
    def _configure_embed_author(
        embed: discord.Embed,
        host_id: str,
        host_display_name: str | None,
        host_avatar_url: str | None,
    ) -> None:
        """Configure embed author with host information.

        Args:
            embed: Discord embed to configure
            host_id: Discord ID of the game host
            host_display_name: Optional display name for host
            host_avatar_url: Optional host avatar URL
        """
        if host_display_name:
            author_name = f"@{host_display_name}"
        else:
            author_name = host_id if not host_id.isdigit() else "@User"

        if host_avatar_url:
            embed.set_author(name=author_name, icon_url=host_avatar_url)
        else:
            embed.set_author(name=author_name)

    @staticmethod
    def _add_game_time_fields(
        embed: discord.Embed,
        scheduled_at: datetime,
        host_id: str,
        expected_duration_minutes: int | None,
        where: str | None,
        channel_id: str | None,
    ) -> None:
        """Add game time, host, duration, location, and channel fields.

        Args:
            embed: Discord embed to configure
            scheduled_at: When game is scheduled
            host_id: Discord ID of host
            expected_duration_minutes: Optional game duration
            where: Optional game location
            channel_id: Optional voice channel ID
        """
        game_time_value = (
            f"{format_discord_timestamp(scheduled_at, 'F')} "
            f"({format_discord_timestamp(scheduled_at, 'R')})"
        )
        embed.add_field(name="Game Time", value=game_time_value, inline=False)

        formatted_host = format_user_or_placeholder(host_id)
        embed.add_field(name="Host", value=formatted_host, inline=True)

        if expected_duration_minutes:
            duration_text = format_duration(expected_duration_minutes)
            embed.add_field(name="Run Time", value=duration_text, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if where:
            embed.add_field(name="Where", value=where, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if channel_id:
            embed.add_field(name="Voice Channel", value=f"<#{channel_id}>", inline=False)

    @staticmethod
    def _add_participant_fields(
        embed: discord.Embed,
        participant_ids: list[str],
        overflow_ids: list[str],
        current_count: int,
        max_players: int,
    ) -> None:
        """Add participant and waitlist fields to embed.

        Args:
            embed: Discord embed to configure
            participant_ids: List of confirmed participant IDs
            overflow_ids: List of waitlisted participant IDs
            current_count: Current participant count
            max_players: Maximum allowed participants
        """
        if participant_ids:
            embed.add_field(
                name=f"Participants ({current_count}/{max_players})",
                value=format_participant_list(participant_ids, max_display=15, start_number=1),
                inline=True,
            )
        else:
            embed.add_field(
                name=f"Participants ({current_count}/{max_players})",
                value="No participants yet",
                inline=True,
            )

        if overflow_ids:
            start_num = len(participant_ids) + 1
            overflow_text = format_participant_list(
                overflow_ids, max_display=10, start_number=start_num
            )
            embed.add_field(
                name=f"Waitlisted ({len(overflow_ids)})",
                value=overflow_text,
                inline=True,
            )

    @staticmethod
    def _add_footer_and_links(
        embed: discord.Embed,
        status: str,
        calendar_url: str | None,
    ) -> None:
        """Add links field and footer to embed.

        Args:
            embed: Discord embed to configure
            status: Game status
            calendar_url: Optional calendar download URL
        """
        if calendar_url:
            links_value = f"📅 [Add to Calendar]({calendar_url})"
            embed.add_field(name="Links", value=links_value, inline=True)

        status_display = status
        with contextlib.suppress(ValueError, AttributeError):
            status_display = GameStatus(status).display_name

        embed.set_footer(text=f"Status: {status_display}")

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
        _signup_instructions: str | None = None,
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
            host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
            thumbnail_url: Optional thumbnail image URL
            image_url: Optional banner image URL

        Returns:
            Configured Discord embed
        """
        truncated_description, calendar_url, thumb_url, img_url = (
            GameMessageFormatter._prepare_description_and_urls(
                description, game_id, thumbnail_url, image_url
            )
        )

        embed = discord.Embed(
            title=game_title,
            description=truncated_description,
            color=GameMessageFormatter._get_status_color(status),
        )

        GameMessageFormatter._configure_embed_author(
            embed, host_id, host_display_name, host_avatar_url
        )

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)
        if img_url:
            embed.set_image(url=img_url)

        GameMessageFormatter._add_game_time_fields(
            embed, scheduled_at, host_id, expected_duration_minutes, where, channel_id
        )

        GameMessageFormatter._add_participant_fields(
            embed, participant_ids, overflow_ids, current_count, max_players
        )

        GameMessageFormatter._add_footer_and_links(embed, status, calendar_url)

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
    guild_id: str | None = None,
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
        host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
        has_thumbnail: Whether game has a thumbnail image
        has_image: Whether game has a banner image
        guild_id: Optional guild ID for special @everyone handling

    Returns:
        Tuple of (content, embed, view) where content contains role mentions if any
    """
    formatter = GameMessageFormatter()

    config = get_config()
    thumbnail_url = None
    image_url = None

    if has_thumbnail:
        thumbnail_url = f"{config.backend_url}/api/v1/games/{game_id}/thumbnail"

    if has_image:
        image_url = f"{config.backend_url}/api/v1/games/{game_id}/image"

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
        _signup_instructions=signup_instructions,
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
        mentions = []
        for role_id in notify_role_ids:
            # Special handling: @everyone uses literal string, not <@&guild_id>
            if guild_id and role_id == guild_id:
                mentions.append("@everyone")
            else:
                mentions.append(f"<@&{role_id}>")
        content = " ".join(mentions)

    return content, embed, view
