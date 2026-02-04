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

import logging
import os
import sys
import time

import pika
from opentelemetry import trace
from pika.exceptions import AMQPConnectionError

from shared.messaging.infrastructure import (
    DEAD_LETTER_QUEUES,
    DLQ_BINDINGS,
    DLX_EXCHANGE,
    MAIN_EXCHANGE,
    PRIMARY_QUEUE_ARGUMENTS,
    PRIMARY_QUEUES,
    QUEUE_BINDINGS,
)
from shared.telemetry import flush_telemetry, init_telemetry

logger = logging.getLogger(__name__)


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
            logger.info("RabbitMQ is ready")
            return
        except AMQPConnectionError:
            if attempt < max_retries:
                print(f"  RabbitMQ not ready (attempt {attempt}/{max_retries}), retrying...")
                logger.debug(
                    "RabbitMQ not ready (attempt %s/%s), retrying...",
                    attempt,
                    max_retries,
                )
                time.sleep(1)
            else:
                print(f"✗ RabbitMQ failed to become ready after {max_retries} attempts")
                logger.error("RabbitMQ failed to become ready after %s attempts", max_retries)
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

    channel.exchange_declare(exchange=MAIN_EXCHANGE, exchange_type="topic", durable=True)
    print(f"  ✓ Exchange '{MAIN_EXCHANGE}' declared")
    logger.info("Declared exchange: %s", MAIN_EXCHANGE)

    channel.exchange_declare(exchange=DLX_EXCHANGE, exchange_type="topic", durable=True)
    print(f"  ✓ Exchange '{DLX_EXCHANGE}' declared")
    logger.info("Declared dead letter exchange: %s", DLX_EXCHANGE)

    for dlq_name in DEAD_LETTER_QUEUES:
        channel.queue_declare(queue=dlq_name, durable=True)
        print(f"  ✓ DLQ '{dlq_name}' declared")
        logger.info("Declared dead letter queue: %s", dlq_name)

    for dlq_name, routing_key in DLQ_BINDINGS:
        channel.queue_bind(exchange=DLX_EXCHANGE, queue=dlq_name, routing_key=routing_key)
        print(f"  ✓ Binding '{dlq_name}' -> DLX '{routing_key}'")
        logger.info(
            "Bound DLQ %s to %s with routing key %s",
            dlq_name,
            DLX_EXCHANGE,
            routing_key,
        )

    for queue_name in PRIMARY_QUEUES:
        channel.queue_declare(queue=queue_name, durable=True, arguments=PRIMARY_QUEUE_ARGUMENTS)
        print(f"  ✓ Queue '{queue_name}' declared")
        logger.info("Declared primary queue: %s", queue_name)

    for queue_name, routing_key in QUEUE_BINDINGS:
        channel.queue_bind(exchange=MAIN_EXCHANGE, queue=queue_name, routing_key=routing_key)
        print(f"  ✓ Binding '{queue_name}' -> '{routing_key}'")
        logger.info(
            "Bound queue %s to %s with routing key %s",
            queue_name,
            MAIN_EXCHANGE,
            routing_key,
        )

    connection.close()
    logger.info("RabbitMQ infrastructure creation completed")


def main() -> None:
    """Main initialization entry point."""
    init_telemetry("init-service")
    tracer = trace.get_tracer(__name__)

    print("=== RabbitMQ Infrastructure Initialization ===")
    logger.info("RabbitMQ Infrastructure Initialization started")

    with tracer.start_as_current_span("init.rabbitmq") as span:
        rabbitmq_url = os.getenv("RABBITMQ_URL")
        if not rabbitmq_url:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "RABBITMQ_URL not set"))
            print("✗ RABBITMQ_URL environment variable not set")
            logger.error("RABBITMQ_URL environment variable not set")
            sys.exit(1)

        print("Waiting for RabbitMQ...")
        logger.info("Waiting for RabbitMQ to be ready")
        wait_for_rabbitmq(rabbitmq_url)

        print("Creating RabbitMQ infrastructure...")
        logger.info("Creating RabbitMQ infrastructure")
        try:
            create_infrastructure(rabbitmq_url)
            span.set_status(trace.Status(trace.StatusCode.OK))
            print("✓ RabbitMQ infrastructure initialized successfully")
            logger.info("RabbitMQ infrastructure initialized successfully")
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            print(f"✗ Failed to initialize RabbitMQ infrastructure: {e}")
            logger.exception("Failed to initialize RabbitMQ infrastructure: %s", e)
            flush_telemetry()
            sys.exit(1)

    flush_telemetry()


if __name__ == "__main__":
    main()
