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


"""Notification service for sending game reminders."""

import logging
import uuid

from shared.messaging import events
from shared.messaging.sync_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing game notifications."""

    def __init__(self):
        """Initialize notification service with event publisher."""
        self.event_publisher = SyncEventPublisher()

    def send_game_reminder(
        self,
        game_id: uuid.UUID,
        user_id: uuid.UUID,
        game_title: str,
        game_time_unix: int,
        reminder_minutes: int,
    ) -> bool:
        """
        Send game reminder notification to user via Discord DM.

        Args:
            game_id: Game session UUID
            user_id: User UUID
            game_title: Title of the game
            game_time_unix: Unix timestamp of game start time
            reminder_minutes: Minutes before game this reminder is for

        Returns:
            True if notification published successfully
        """
        logger.info(
            f"=== NotificationService.send_game_reminder called: "
            f"game={game_id}, user={user_id}, reminder={reminder_minutes}min ==="
        )

        try:
            logger.info("Connecting to RabbitMQ event publisher")
            self.event_publisher.connect()
            logger.info("Successfully connected to RabbitMQ")

            message = (
                f"Your game '{game_title}' starts <t:{game_time_unix}:R> "
                f"(in {reminder_minutes} minutes)"
            )

            notification_event = events.NotificationSendDMEvent(
                user_id=str(user_id),
                game_id=game_id,
                game_title=game_title,
                game_time_unix=game_time_unix,
                notification_type=f"{reminder_minutes}_minutes_before",
                message=message,
            )

            logger.info(f"Created notification event: {notification_event.model_dump()}")

            event_wrapper = events.Event(
                event_type=events.EventType.NOTIFICATION_SEND_DM,
                data=notification_event.model_dump(),
            )

            logger.info("Publishing event to RabbitMQ with routing key: notification.send_dm")
            self.event_publisher.publish(event_wrapper)
            logger.info("Event published successfully to RabbitMQ")

            logger.info(
                f"Successfully published notification for user {user_id} game {game_id} "
                f"({reminder_minutes} min before)"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to publish notification for user {user_id} game {game_id}: {e}",
                exc_info=True,
            )
            return False

        finally:
            logger.info("Closing RabbitMQ connection")
            self.event_publisher.close()
            logger.info("RabbitMQ connection closed")


def get_notification_service() -> NotificationService:
    """Get singleton notification service instance."""
    return NotificationService()
