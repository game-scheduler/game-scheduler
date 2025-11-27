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
RabbitMQ messaging infrastructure for event-driven communication.

Provides async RabbitMQ connection management, event publishing,
and consumption framework for microservices communication.
"""

from shared.messaging.config import get_rabbitmq_connection
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher
from shared.messaging.sync_publisher import SyncEventPublisher

__all__ = [
    "get_rabbitmq_connection",
    "Event",
    "EventType",
    "EventPublisher",
    "EventConsumer",
    "SyncEventPublisher",
]
