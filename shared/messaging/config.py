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
RabbitMQ connection configuration and management.

Provides async connection handling with automatic reconnection
and connection pooling for RabbitMQ.
"""

import asyncio
import contextlib
import logging
import os

import aio_pika
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger(__name__)


class RabbitMQConfig:
    """RabbitMQ connection configuration."""

    def __init__(
        self,
        password: str,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        virtual_host: str = "/",
        connection_timeout: int = 60,
        heartbeat: int = 60,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.connection_timeout = connection_timeout
        self.heartbeat = heartbeat

    @property
    def url(self) -> str:
        """Build RabbitMQ connection URL."""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.virtual_host}"


_connection: AbstractRobustConnection | None = None
_connection_lock = asyncio.Lock()


async def get_rabbitmq_connection(
    config: RabbitMQConfig | None = None,
) -> AbstractRobustConnection:
    """
    Get or create RabbitMQ connection with automatic reconnection.

    Args:
        config: RabbitMQ configuration. Uses environment URL or defaults if not provided.

    Returns:
        Robust connection that automatically reconnects on failure.
    """
    global _connection  # noqa: PLW0603 - Singleton pattern for RabbitMQ connection pooling

    async with _connection_lock:
        if _connection is None or _connection.is_closed:
            if config is None:
                rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
                logger.info("Connecting to RabbitMQ using URL: %s", rabbitmq_url)
                connection_timeout = 60
                heartbeat = 60
            else:
                rabbitmq_url = config.url
                connection_timeout = config.connection_timeout
                heartbeat = config.heartbeat
                logger.info("Connecting to RabbitMQ at %s:%s", config.host, config.port)

            _connection = await aio_pika.connect_robust(
                rabbitmq_url,
                timeout=connection_timeout,
                heartbeat=heartbeat,
            )

            logger.info("Successfully connected to RabbitMQ")

        return _connection


async def close_rabbitmq_connection() -> None:
    """Close RabbitMQ connection gracefully."""
    global _connection  # noqa: PLW0603 - Singleton pattern for RabbitMQ connection cleanup

    conn = _connection
    _connection = None
    if conn and not conn.is_closed:
        logger.info("Closing RabbitMQ connection")
        with contextlib.suppress(Exception):
            await conn.close()
