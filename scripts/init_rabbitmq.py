#!/usr/bin/env python3
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


"""Initialize RabbitMQ infrastructure for game scheduler."""

import os
import sys
import time

import pika
from pika.exceptions import AMQPConnectionError


def wait_for_rabbitmq(rabbitmq_url: str, max_retries: int = 30) -> None:
    """
    Wait for RabbitMQ to be ready.

    Args:
        rabbitmq_url: RabbitMQ connection URL
        max_retries: Maximum connection attempts

    Raises:
        SystemExit: If RabbitMQ is not available after max_retries
    """
    for attempt in range(1, max_retries + 1):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            connection.close()
            print("✓ RabbitMQ is ready")
            return
        except AMQPConnectionError:
            if attempt < max_retries:
                print(f"  RabbitMQ not ready (attempt {attempt}/{max_retries}), retrying...")
                time.sleep(1)
            else:
                print(f"✗ RabbitMQ failed to become ready after {max_retries} attempts")
                sys.exit(1)


def create_infrastructure(rabbitmq_url: str) -> None:
    """
    Create RabbitMQ exchanges, queues, and bindings.

    All operations are idempotent - safe to run multiple times.

    Args:
        rabbitmq_url: RabbitMQ connection URL
    """
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()

    # Declare main exchange
    channel.exchange_declare(exchange="game_scheduler", exchange_type="topic", durable=True)
    print("  ✓ Exchange 'game_scheduler' declared")

    # Declare dead letter exchange
    channel.exchange_declare(exchange="game_scheduler.dlx", exchange_type="topic", durable=True)
    print("  ✓ Exchange 'game_scheduler.dlx' declared")

    # Queue configuration with dead letter exchange and TTL
    queue_args = {
        "x-dead-letter-exchange": "game_scheduler.dlx",
        "x-message-ttl": 3600000,  # 1 hour in milliseconds
    }

    # Declare queues with TTL and DLX
    queues = ["bot_events", "api_events", "scheduler_events", "notification_queue"]
    for queue_name in queues:
        channel.queue_declare(queue=queue_name, durable=True, arguments=queue_args)
        print(f"  ✓ Queue '{queue_name}' declared")

    # Declare dead letter queue (no TTL - infinite retention)
    channel.queue_declare(queue="DLQ", durable=True)
    print("  ✓ Queue 'DLQ' declared (infinite TTL)")

    # Create bindings (matching original definitions.json.template)
    bindings = [
        # bot_events receives game, guild, and channel events
        ("bot_events", "game.*"),
        ("bot_events", "guild.*"),
        ("bot_events", "channel.*"),
        # api_events receives game events for API updates
        ("api_events", "game.*"),
        # scheduler_events receives specific game lifecycle events
        ("scheduler_events", "game.created"),
        ("scheduler_events", "game.updated"),
        ("scheduler_events", "game.cancelled"),
        # notification_queue receives DM notifications
        ("notification_queue", "notification.send_dm"),
    ]

    for queue_name, routing_key in bindings:
        channel.queue_bind(exchange="game_scheduler", queue=queue_name, routing_key=routing_key)
        print(f"  ✓ Binding '{queue_name}' -> '{routing_key}'")

    # Bind DLQ to dead letter exchange (catch-all)
    channel.queue_bind(exchange="game_scheduler.dlx", queue="DLQ", routing_key="#")
    print("  ✓ Binding 'DLQ' -> 'game_scheduler.dlx' (catch-all)")

    connection.close()


def main() -> None:
    """Main initialization entry point."""
    print("=== RabbitMQ Infrastructure Initialization ===")

    rabbitmq_url = os.getenv("RABBITMQ_URL")
    if not rabbitmq_url:
        print("✗ RABBITMQ_URL environment variable not set")
        sys.exit(1)

    print("Waiting for RabbitMQ...")
    wait_for_rabbitmq(rabbitmq_url)

    print("Creating RabbitMQ infrastructure...")
    try:
        create_infrastructure(rabbitmq_url)
        print("✓ RabbitMQ infrastructure initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize RabbitMQ infrastructure: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
