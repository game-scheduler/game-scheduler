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


"""Bot event publisher wrapper for RabbitMQ messaging."""

import logging
from typing import Any
from uuid import UUID

from shared.messaging.events import (
    Event,
    EventType,
    GameCreatedEvent,
)
from shared.messaging.publisher import EventPublisher

logger = logging.getLogger(__name__)


class BotEventPublisher:
    """Publish events from bot service to RabbitMQ."""

    def __init__(self, publisher: EventPublisher | None = None):
        """
        Initialize bot event publisher.

        Args:
            publisher: Optional EventPublisher instance, creates default if None
        """
        self.publisher = publisher or EventPublisher()
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ broker."""
        if not self._connected:
            await self.publisher.connect()
            self._connected = True
            logger.info("Bot event publisher connected to RabbitMQ")

    async def disconnect(self) -> None:
        """Close connection to RabbitMQ broker."""
        if self._connected:
            await self.publisher.close()
            self._connected = False
            logger.info("Bot event publisher disconnected from RabbitMQ")

    async def publish_game_created(
        self,
        game_id: str,
        title: str,
        guild_id: str,
        channel_id: str,
        host_id: str,
        scheduled_at: str,
    ) -> None:
        """
        Publish game created event.

        Args:
            game_id: UUID of the game session
            title: Game title
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            host_id: Discord ID of the host
            scheduled_at: ISO 8601 UTC timestamp string
        """
        from datetime import datetime

        scheduled_at_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

        event_data = GameCreatedEvent(
            game_id=UUID(game_id),
            title=title,
            guild_id=guild_id,
            channel_id=channel_id,
            host_id=host_id,
            scheduled_at=scheduled_at_dt,
        )

        event = Event(event_type=EventType.GAME_CREATED, data=event_data.model_dump())

        await self.publisher.publish(event=event, routing_key="game.created")

        logger.info(
            f"Published game_created event: game={game_id}, title={title}, "
            f"guild={guild_id}, channel={channel_id}"
        )

    async def publish_game_updated(self, game_id: str, updated_fields: dict[str, Any]) -> None:
        """
        Publish game updated event.

        Args:
            game_id: UUID of the game session
            updated_fields: Dictionary of updated field names and values
        """
        event = Event(
            event_type=EventType.GAME_UPDATED,
            data={"game_id": game_id, "updated_fields": updated_fields},
        )

        await self.publisher.publish(event=event, routing_key="game.updated")

        fields_list = list(updated_fields.keys())
        logger.info(f"Published game_updated event: game={game_id}, fields={fields_list}")


# Global publisher instance
_publisher_instance: BotEventPublisher | None = None


def get_bot_publisher() -> BotEventPublisher:
    """Get or create global bot event publisher instance."""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = BotEventPublisher()
    return _publisher_instance
