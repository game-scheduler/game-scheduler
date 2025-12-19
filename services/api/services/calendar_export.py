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


"""Calendar export service for generating iCal files."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from icalendar import Calendar, Event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.api.auth.discord_client import (
    fetch_channel_name_safe,
    fetch_guild_name_safe,
    fetch_user_display_name_safe,
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
    ):
        self.db = db

    async def export_game(
        self,
        game_id: str,
        user_id: str,
        discord_id: str,
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
            raise ValueError(f"Game with ID {game_id} not found")

        # Check permission (pre-computed by caller)
        if not can_export:
            raise PermissionError(
                "You must be the host, a participant, or have admin/bot manager permissions "
                "to export this game"
            )

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
            host_name = await fetch_user_display_name_safe(game.host.discord_id)
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
        from icalendar import Alarm

        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", "Game starting soon!")
        alarm.add("trigger", timedelta(minutes=-minutes_before))
        return alarm
