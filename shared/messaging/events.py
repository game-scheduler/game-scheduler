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


"""
Event schema definitions for inter-service communication.

Defines event types and structures for publishing and consuming
events across the microservices architecture.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for inter-service messaging."""

    # Game lifecycle events
    GAME_CREATED = "game.created"
    GAME_UPDATED = "game.updated"
    GAME_CANCELLED = "game.cancelled"
    GAME_STARTED = "game.started"
    GAME_COMPLETED = "game.completed"

    # Participant events
    PLAYER_JOINED = "game.player_joined"
    PLAYER_LEFT = "game.player_left"
    PLAYER_REMOVED = "game.player_removed"
    WAITLIST_ADDED = "game.waitlist_added"
    WAITLIST_REMOVED = "game.waitlist_removed"

    # Notification events
    NOTIFICATION_SEND_DM = "notification.send_dm"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # Configuration events
    GUILD_CONFIG_UPDATED = "guild.config_updated"
    CHANNEL_CONFIG_UPDATED = "channel.config_updated"


class Event(BaseModel):
    """
    Base event structure for RabbitMQ messaging.

    All events follow this structure for consistent handling
    across services.

    Attributes:
        event_type: Type of event being published
        timestamp: UTC timestamp when event was created
        data: Event-specific payload
        trace_id: Optional correlation ID for tracing
    """

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    data: dict[str, Any]
    trace_id: str | None = None


class GameCreatedEvent(BaseModel):
    """Payload for game.created event."""

    game_id: UUID
    title: str
    guild_id: str
    channel_id: str
    host_id: str
    scheduled_at: datetime
    max_players: int | None = None
    notify_role_ids: list[str] | None = None


class PlayerJoinedEvent(BaseModel):
    """Payload for game.player_joined event."""

    game_id: UUID
    player_id: str
    player_count: int
    max_players: int | None = None


class PlayerLeftEvent(BaseModel):
    """Payload for game.player_left event."""

    game_id: UUID
    player_id: str
    player_count: int
    max_players: int | None = None


class NotificationSendDMEvent(BaseModel):
    """Payload for notification.send_dm event."""

    user_id: str
    game_id: UUID
    game_title: str
    game_time_unix: int
    notification_type: str
    message: str
