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


"""Integration tests for RabbitMQ Dead Letter Queue (DLQ) configuration.

Tests verify that:
1. DLQ exchange and queue exist
2. Primary queues have dead-letter-exchange configured
3. Rejected messages are routed to DLQ
4. Message metadata is preserved in DLQ
"""

import json
import os
import time

import pika
import pytest


@pytest.fixture(scope="module")
def rabbitmq_connection_params():
    """Get RabbitMQ connection parameters from environment."""
    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            username=os.getenv("RABBITMQ_DEFAULT_USER", "gamebot"),
            password=os.getenv("RABBITMQ_DEFAULT_PASS", "dev_password_change_in_prod"),
        ),
    )


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection_params):
    """Create RabbitMQ channel for testing."""
    connection = pika.BlockingConnection(rabbitmq_connection_params)
    channel = connection.channel()

    # Purge queues before each test to ensure clean state
    try:
        channel.queue_purge("bot_events")
        channel.queue_purge("DLQ")
    except Exception:
        pass  # Queues might not exist yet

    yield channel

    # Purge queues after each test to clean up
    try:
        channel.queue_purge("bot_events")
        channel.queue_purge("DLQ")
    except Exception:
        pass

    connection.close()


def test_dlq_exchange_exists(rabbitmq_channel):
    """Verify that game_scheduler.dlx exchange exists."""
    # Passive declaration will raise exception if exchange doesn't exist
    rabbitmq_channel.exchange_declare(
        exchange="game_scheduler.dlx", exchange_type="topic", passive=True, durable=True
    )


def test_dlq_queue_exists(rabbitmq_channel):
    """Verify that DLQ queue exists and is durable."""
    result = rabbitmq_channel.queue_declare(queue="DLQ", passive=True, durable=True)
    assert result.method.queue == "DLQ"


def test_bot_events_queue_has_dlx_configured(rabbitmq_channel):
    """Verify bot_events queue has dead-letter-exchange configured."""
    # Passive declare just confirms queue exists - we can't get arguments from it
    # Instead, test that messages rejected from bot_events go to DLQ (proves DLX is configured)
    rabbitmq_channel.queue_declare(queue="bot_events", passive=True)

    # Publish a test message to bot_events
    test_message = json.dumps({"test": "dlx_config_check"})
    rabbitmq_channel.basic_publish(
        exchange="game_scheduler",
        routing_key="game.test",
        body=test_message,
    )

    # Consume and NACK (reject) the message
    method, properties, body = rabbitmq_channel.basic_get(queue="bot_events", auto_ack=False)
    assert method is not None, "Message should arrive in bot_events"
    rabbitmq_channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    time.sleep(0.5)

    # If DLX is configured, message should be in DLQ
    dlq_method, dlq_properties, dlq_body = rabbitmq_channel.basic_get(queue="DLQ", auto_ack=True)
    assert dlq_method is not None, "Rejected message should be in DLQ (proves DLX is configured)"


def test_dlq_binding_exists(rabbitmq_channel):
    """Verify DLQ is bound to game_scheduler.dlx with catch-all routing."""
    # Create a test message and publish to DLX
    test_routing_key = "test.dlq.routing"
    test_message = json.dumps({"test": "dlq_binding"})

    # Publish directly to DLX
    rabbitmq_channel.basic_publish(
        exchange="game_scheduler.dlx",
        routing_key=test_routing_key,
        body=test_message,
    )

    # Check if message arrived in DLQ
    method, properties, body = rabbitmq_channel.basic_get(queue="DLQ", auto_ack=True)

    assert method is not None, "Message should have been routed to DLQ"
    assert body.decode() == test_message


def test_rejected_message_goes_to_dlq(rabbitmq_channel):
    """Verify that NACKed messages from bot_events go to DLQ."""
    # Publish a test message to bot_events
    test_message = json.dumps(
        {
            "event_type": "GAME_REMINDER_DUE",
            "data": {"game_id": "test-game-id", "reminder_minutes": 60},
        }
    )

    rabbitmq_channel.basic_publish(
        exchange="game_scheduler",
        routing_key="game.test",
        body=test_message,
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )

    # Consume and NACK the message (requeue=False sends to DLQ)
    method, properties, body = rabbitmq_channel.basic_get(queue="bot_events", auto_ack=False)

    assert method is not None, "Message should be in bot_events queue"
    assert body.decode() == test_message

    # NACK without requeue - should go to DLQ
    rabbitmq_channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    # Give RabbitMQ a moment to route to DLQ
    time.sleep(0.5)

    # Check DLQ for the message
    dlq_method, dlq_properties, dlq_body = rabbitmq_channel.basic_get(queue="DLQ", auto_ack=True)

    assert dlq_method is not None, "Message should have been routed to DLQ after NACK"
    assert dlq_body.decode() == test_message


def test_dlq_message_preserves_metadata(rabbitmq_channel):
    """Verify that messages in DLQ preserve death metadata."""
    # Publish a test message with custom headers
    test_message = json.dumps({"test": "metadata_preservation"})
    custom_headers = {"custom-header": "test-value"}

    rabbitmq_channel.basic_publish(
        exchange="game_scheduler",
        routing_key="game.test",
        body=test_message,
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent,
            headers=custom_headers,
        ),
    )

    # Consume and NACK
    method, properties, body = rabbitmq_channel.basic_get(queue="bot_events", auto_ack=False)
    assert method is not None
    rabbitmq_channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    time.sleep(0.5)

    # Check DLQ message headers
    dlq_method, dlq_properties, dlq_body = rabbitmq_channel.basic_get(queue="DLQ", auto_ack=True)

    assert dlq_method is not None
    assert dlq_properties.headers is not None

    # Check for x-death header (RabbitMQ adds this)
    assert "x-death" in dlq_properties.headers
    x_death = dlq_properties.headers["x-death"]
    assert len(x_death) > 0

    death_record = x_death[0]
    assert death_record["queue"] == "bot_events"
    assert death_record["reason"] == "rejected"
    assert death_record["exchange"] == "game_scheduler"


def test_expired_message_goes_to_dlq(rabbitmq_channel):
    """Verify that messages with expired TTL are routed to DLQ."""
    # Publish message with very short TTL (1ms)
    test_message = json.dumps({"test": "ttl_expiration"})

    rabbitmq_channel.basic_publish(
        exchange="game_scheduler",
        routing_key="game.ttl",
        body=test_message,
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent,
            expiration="1",  # 1ms TTL
        ),
    )

    # Wait for message to expire
    time.sleep(1)

    # Message should have expired and gone to DLQ
    # Try to get from bot_events (should be empty)
    method, properties, body = rabbitmq_channel.basic_get(queue="bot_events", auto_ack=True)
    assert method is None, "Message should have expired from bot_events"

    # Check DLQ for expired message
    dlq_method, dlq_properties, dlq_body = rabbitmq_channel.basic_get(queue="DLQ", auto_ack=True)

    assert dlq_method is not None, "Expired message should be in DLQ"
    assert dlq_body.decode() == test_message

    # Verify death reason is 'expired'
    assert "x-death" in dlq_properties.headers
    death_record = dlq_properties.headers["x-death"][0]
    assert death_record["reason"] == "expired"
