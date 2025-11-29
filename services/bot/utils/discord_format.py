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


"""Discord message formatting utilities.

This module provides utilities for formatting Discord messages with mentions,
timestamps, and participant lists following Discord's native formatting patterns.
"""

from datetime import datetime


def format_discord_mention(user_id: str) -> str:
    """Format a Discord user mention.

    Args:
        user_id: Discord user snowflake ID

    Returns:
        Discord mention string in format <@user_id>
    """
    return f"<@{user_id}>"


def format_discord_timestamp(dt: datetime, style: str = "F") -> str:
    """Format a datetime as a Discord timestamp.

    Discord timestamps are automatically displayed in each user's local timezone.

    Args:
        dt: Datetime to format (should be UTC)
        style: Discord timestamp style:
            - F: Full date/time (default): "Friday, November 15, 2025 7:00 PM"
            - f: Short date/time: "November 15, 2025 7:00 PM"
            - D: Date only: "11/15/2025"
            - d: Short date: "11/15/25"
            - T: Time only: "7:00 PM"
            - t: Short time: "7:00 PM"
            - R: Relative: "in 2 hours"

    Returns:
        Discord timestamp string in format <t:unix_timestamp:style>
    """
    unix_timestamp = int(dt.timestamp())
    return f"<t:{unix_timestamp}:{style}>"


def format_participant_list(
    participant_ids: list[str], max_display: int = 10, include_count: bool = True
) -> str:
    """Format a list of participants using Discord mentions or placeholder names.

    Args:
        participant_ids: List of Discord user IDs or placeholder names
        max_display: Maximum number of participants to display
        include_count: Whether to include total count if truncated

    Returns:
        Formatted participant list with Discord mentions and/or placeholder names
    """
    if not participant_ids:
        return "No participants yet"

    # Format each participant: Discord mention for IDs, plain text for placeholders
    mentions = [
        uid if not uid.isdigit() else format_discord_mention(uid)
        for uid in participant_ids[:max_display]
    ]
    result = "\n".join(mentions)

    if len(participant_ids) > max_display and include_count:
        remaining = len(participant_ids) - max_display
        result += f"\n... and {remaining} more"

    return result


def format_game_status_emoji(status: str) -> str:
    """Get emoji for game status.

    Args:
        status: Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)

    Returns:
        Appropriate emoji for the status
    """
    emoji_map = {
        "SCHEDULED": "📅",
        "IN_PROGRESS": "🎮",
        "COMPLETED": "✅",
        "CANCELLED": "❌",
    }
    return emoji_map.get(status, "❓")


def format_rules_section(rules: str | None, max_length: int = 500) -> str:
    """Format rules section for display in embed.

    Args:
        rules: Game rules text
        max_length: Maximum length before truncation

    Returns:
        Formatted rules text, truncated if necessary
    """
    if not rules or not rules.strip():
        return "No rules specified"


def format_duration(minutes: int | None) -> str:
    """Format duration in minutes to human-readable string.

    Args:
        minutes: Duration in minutes

    Returns:
        Formatted duration string (e.g., "2h 30m", "1h", "45m")
    """
    if minutes is None or minutes <= 0:
        return ""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0 and remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{remaining_minutes}m"
