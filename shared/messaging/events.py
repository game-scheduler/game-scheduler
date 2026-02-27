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


"""
Event schema definitions for inter-service communication.

Defines event types and structures for publishing and consuming
events across the microservices architecture.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(StrEnum):
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
    NOTIFICATION_DUE = "game.notification_due"
    GAME_STATUS_TRANSITION_DUE = "game.status_transition_due"
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    signup_method: str


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


class NotificationDueEvent(BaseModel):
    """Payload for game.notification_due event."""

    game_id: UUID
    notification_type: str
    participant_id: str | None = None


class GameStartedEvent(BaseModel):
    """Payload for game.started event."""

    game_id: UUID
    title: str
    guild_id: str | None
    channel_id: str | None


class NotificationSendDMEvent(BaseModel):
    """Payload for notification.send_dm event."""

    user_id: str
    game_id: UUID
    game_title: str
    game_time_unix: int
    notification_type: str
    message: str
