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


"""Calendar export service for generating iCal files."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from icalendar import Alarm, Calendar, Event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.cache import projection as member_projection
from shared.cache.client import get_redis_client
from shared.discord.client import (
    fetch_channel_name_safe,
    fetch_guild_name_safe,
)
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession
from shared.models.participant import GameParticipant

logger = logging.getLogger(__name__)


class CalendarExportService:
    """Service for exporting game sessions to iCal format."""

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def export_game(
        self,
        game_id: str,
        _user_id: str,
        _discord_id: str,
        can_export: bool,
    ) -> bytes:
        """
        Export a single game to iCal format.

        Args:
            game_id: Game session ID
            user_id: User UUID (for host check)
            discord_id: Discord user ID (for participant check)
            can_export: Whether user has permission to export (pre-checked by caller)

        Returns:
            iCal file content as bytes

        Raises:
            ValueError: If game not found
            PermissionError: If user is not host, participant, admin, or bot manager
        """
        query = (
            select(GameSession)
            .where(GameSession.id == game_id)
            .options(
                selectinload(GameSession.guild),
                selectinload(GameSession.channel).selectinload(ChannelConfiguration.guild),
                selectinload(GameSession.host),
                selectinload(GameSession.participants).selectinload(GameParticipant.user),
            )
        )

        result = await self.db.execute(query)
        game = result.scalar_one_or_none()

        if not game:
            msg = f"Game with ID {game_id} not found"
            raise ValueError(msg)

        # Check permission (pre-computed by caller)
        if not can_export:
            msg = (
                "You must be the host, a participant, or have admin/bot manager permissions "
                "to export this game"
            )
            raise PermissionError(msg)

        return await self._generate_calendar([game])

    async def _generate_calendar(self, games: Sequence[GameSession]) -> bytes:
        """
        Generate iCal calendar from game sessions.

        Args:
            games: Sequence of game sessions to export

        Returns:
            iCal file content as bytes
        """
        cal = Calendar()
        cal.add("prodid", "-//Game Scheduler//Discord Game Scheduler//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", "Game Scheduler")
        cal.add("x-wr-timezone", "UTC")
        cal.add("x-wr-caldesc", "Game sessions from Discord Game Scheduler")

        for game in games:
            event = await self._create_event(game)
            cal.add_component(event)

        return cal.to_ical()

    async def _resolve_host_display(self, game: GameSession) -> str | None:
        guild_id = game.guild.guild_id if game.guild else None
        if not guild_id or not game.host:
            return None
        redis = await get_redis_client()
        member = await member_projection.get_member(guild_id, game.host.discord_id, redis=redis)
        if not member:
            return None
        return member.get("nick") or member.get("global_name") or member.get("username")

    async def _create_event(self, game: GameSession) -> Event:
        """
        Create iCal event from game session.

        Args:
            game: Game session to convert

        Returns:
            iCal Event component
        """
        event = Event()

        # Use game ID as UID for calendar updates
        event.add("uid", f"game-{game.id}@game-scheduler")

        # Basic event information
        event.add("summary", game.title)

        # Start time - explicitly mark as UTC
        # Database stores as naive UTC, so we add UTC timezone info
        start_time = game.scheduled_at.replace(tzinfo=UTC)
        event.add("dtstart", start_time)

        # End time (if duration specified, otherwise default 2 hours)
        duration_minutes = game.expected_duration_minutes or 120
        end_time = start_time + timedelta(minutes=duration_minutes)
        event.add("dtend", end_time)

        # Description with game details
        description_parts = []
        if game.host:
            host_display = await self._resolve_host_display(game)
            host_name = f"@{host_display or game.host.discord_id}"
            description_parts.append(f"Host: {host_name}")

        if game.where:
            description_parts.append(f"Location: {game.where}")

        if game.host or game.where:
            description_parts.append("")

        if game.description:
            description_parts.append(game.description)

        if game.signup_instructions:
            description_parts.append("----------")
            description_parts.append(game.signup_instructions)

        event.add("description", "\n".join(description_parts))

        # Location - Discord server and channel
        if game.channel:
            guild_name = await fetch_guild_name_safe(game.channel.guild.guild_id)
            channel_name = await fetch_channel_name_safe(game.channel.channel_id)
            event.add("location", f"{guild_name} #{channel_name}")

        # Status mapping
        status_map = {
            "SCHEDULED": "CONFIRMED",
            "IN_PROGRESS": "CONFIRMED",
            "COMPLETED": "CONFIRMED",
            "CANCELLED": "CANCELLED",
        }
        event.add("status", status_map.get(game.status, "CONFIRMED"))

        # Timestamps
        now = datetime.now(UTC).replace(tzinfo=None)
        event.add("dtstamp", now)
        event.add("created", game.created_at)
        event.add("last-modified", game.updated_at)

        # Add reminders/alarms if specified
        if game.reminder_minutes:
            for minutes in game.reminder_minutes:
                alarm = self._create_alarm(minutes)
                event.add_component(alarm)

        return event

    def _create_alarm(self, minutes_before: int) -> Event:
        """
        Create alarm component for reminder.

        Args:
            minutes_before: Minutes before event to trigger alarm

        Returns:
            VALARM component
        """
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", "Game starting soon!")
        alarm.add("trigger", timedelta(minutes=-minutes_before))
        return alarm
