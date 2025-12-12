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
Shared RabbitMQ infrastructure configuration.

Centralizes queue and exchange definitions to ensure consistency
across init scripts, consumers, and publishers.
"""

from typing import TypedDict


class QueueArguments(TypedDict, total=False):
    """Queue declaration arguments."""

    x_dead_letter_exchange: str
    x_message_ttl: int


# Exchange names
MAIN_EXCHANGE = "game_scheduler"
DLX_EXCHANGE = "game_scheduler.dlx"

# Queue names
QUEUE_BOT_EVENTS = "bot_events"
QUEUE_NOTIFICATION = "notification_queue"

# Dead letter queue names (per-queue DLQ pattern)
QUEUE_BOT_EVENTS_DLQ = "bot_events.dlq"
QUEUE_NOTIFICATION_DLQ = "notification_queue.dlq"

# Queue configuration
PRIMARY_QUEUE_TTL_MS = 3600000  # 1 hour in milliseconds

PRIMARY_QUEUE_ARGUMENTS: dict[str, str | int] = {
    "x-dead-letter-exchange": DLX_EXCHANGE,
    "x-message-ttl": PRIMARY_QUEUE_TTL_MS,
}

# List of primary queues (with TTL and DLX)
PRIMARY_QUEUES = [
    QUEUE_BOT_EVENTS,
    QUEUE_NOTIFICATION,
]

# List of dead letter queues (no TTL, durable)
DEAD_LETTER_QUEUES = [
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION_DLQ,
]

# Routing key bindings (queue_name, routing_key)
QUEUE_BINDINGS = [
    # bot_events receives game, guild, and channel events
    (QUEUE_BOT_EVENTS, "game.*"),
    (QUEUE_BOT_EVENTS, "guild.*"),
    (QUEUE_BOT_EVENTS, "channel.*"),
    # notification_queue receives DM notifications
    (QUEUE_NOTIFICATION, "notification.send_dm"),
]

# DLQ bindings to dead letter exchange
# Each DLQ receives messages from its corresponding primary queue
# using the same routing keys
DLQ_BINDINGS = [
    # bot_events.dlq receives dead-lettered messages with game.*, guild.*, channel.* keys
    (QUEUE_BOT_EVENTS_DLQ, "game.*"),
    (QUEUE_BOT_EVENTS_DLQ, "guild.*"),
    (QUEUE_BOT_EVENTS_DLQ, "channel.*"),
    # notification_queue.dlq receives dead-lettered messages with notification.send_dm key
    (QUEUE_NOTIFICATION_DLQ, "notification.send_dm"),
]
