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


"""Shared fixtures for integration tests."""

import contextlib
import os

import httpx
import pika
import pytest

from shared.cache import client as cache_module
from shared.data_access.guild_isolation import clear_current_guild_ids
from shared.database import engine


@pytest.fixture(scope="module")
def rabbitmq_url():
    """Get RabbitMQ URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


@pytest.fixture
async def async_client(api_base_url):
    """
    HTTP client for public endpoints without authentication.

    For testing public endpoints that don't require authentication.
    Uses the API base URL from environment.
    """
    client = httpx.AsyncClient(base_url=api_base_url, timeout=30.0)
    yield client
    await client.aclose()


@pytest.fixture
def rabbitmq_connection(rabbitmq_url):
    """Create RabbitMQ connection for test setup/assertions."""
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for test operations."""
    channel = rabbitmq_connection.channel()
    yield channel
    channel.close()


# ============================================================================
# RabbitMQ Helper Functions
# ============================================================================


def get_queue_message_count(channel, queue_name):
    """Get number of messages in queue."""
    result = channel.queue_declare(queue=queue_name, durable=True, passive=True)
    return result.method.message_count


def consume_one_message(channel, queue_name, timeout=5):
    """Consume one message from queue with timeout."""
    for method, properties, body in channel.consume(
        queue_name, auto_ack=False, inactivity_timeout=timeout
    ):
        if method is None:
            return None, None, None
        channel.basic_ack(method.delivery_tag)
        channel.cancel()
        return method, properties, body
    return None, None, None


def purge_queue(channel, queue_name):
    """Purge all messages from a queue."""
    with contextlib.suppress(Exception):
        channel.queue_purge(queue_name)


@pytest.fixture(autouse=True)
async def reset_redis_singleton():
    """
    Reset global Redis client singleton between integration tests.

    Autouse fixture that runs for all integration tests to prevent Redis
    event loop issues by disconnecting/reconnecting between tests and
    flushing data to ensure test isolation.
    """
    # Disconnect and clear singleton before test
    if cache_module._redis_client is not None:
        await cache_module._redis_client.disconnect()
        cache_module._redis_client = None

    yield

    # Disconnect and clear singleton after test
    if cache_module._redis_client is not None:
        await cache_module._redis_client.disconnect()
        cache_module._redis_client = None

    # Flush Redis data after test completes
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    temp_client = cache_module.RedisClient(redis_url=redis_url)
    await temp_client.connect()
    await temp_client._client.flushdb()
    await temp_client.disconnect()


@pytest.fixture(autouse=True)
async def cleanup_guild_context():
    """Ensure guild context is cleared before and after each test."""
    clear_current_guild_ids()
    yield
    clear_current_guild_ids()


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """
    Dispose database engine after each test to prevent event loop issues.

    Ensures connection pool is cleared between tests so connections
    don't get reused across different event loops in pytest-asyncio.
    """
    yield
    await engine.dispose()
