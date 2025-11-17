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
RabbitMQ connection configuration and management.

Provides async connection handling with automatic reconnection
and connection pooling for RabbitMQ.
"""

import asyncio
import logging
import os

import aio_pika
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger(__name__)


class RabbitMQConfig:
    """RabbitMQ connection configuration."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/",
        connection_timeout: int = 60,
        heartbeat: int = 60,
    ):
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
    global _connection

    async with _connection_lock:
        if _connection is None or _connection.is_closed:
            if config is None:
                rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
                logger.info(f"Connecting to RabbitMQ using URL: {rabbitmq_url}")
                connection_timeout = 60
                heartbeat = 60
            else:
                rabbitmq_url = config.url
                connection_timeout = config.connection_timeout
                heartbeat = config.heartbeat
                logger.info(f"Connecting to RabbitMQ at {config.host}:{config.port}")

            _connection = await aio_pika.connect_robust(
                rabbitmq_url,
                timeout=connection_timeout,
                heartbeat=heartbeat,
            )

            logger.info("Successfully connected to RabbitMQ")

        return _connection


async def close_rabbitmq_connection() -> None:
    """Close RabbitMQ connection gracefully."""
    global _connection

    if _connection and not _connection.is_closed:
        logger.info("Closing RabbitMQ connection")
        await _connection.close()
        _connection = None
