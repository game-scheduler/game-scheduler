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


"""Unit tests for RabbitMQ messaging configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import shared.messaging.config as config_module
from shared.messaging.config import RabbitMQConfig, close_rabbitmq_connection


class TestRabbitMQConfig:
    """Test RabbitMQ configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RabbitMQConfig(password="test-password")

        assert config.host == "localhost"
        assert config.port == 5672
        assert config.username == "guest"
        assert config.password == "test-password"
        assert config.virtual_host == "/"
        assert config.connection_timeout == 60
        assert config.heartbeat == 60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RabbitMQConfig(
            host="rabbitmq.example.com",
            port=5673,
            username="admin",
            password="secret",
            virtual_host="/custom",
            connection_timeout=30,
            heartbeat=30,
        )

        assert config.host == "rabbitmq.example.com"
        assert config.port == 5673
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.virtual_host == "/custom"
        assert config.connection_timeout == 30
        assert config.heartbeat == 30

    def test_url_generation_default(self):
        """Test URL generation with default values."""
        config = RabbitMQConfig(password="guest")
        expected_url = "amqp://guest:guest@localhost:5672/"

        assert config.url == expected_url

    def test_url_generation_custom(self):
        """Test URL generation with custom values."""
        config = RabbitMQConfig(
            password="secret",
            host="rabbitmq.example.com",
            port=5673,
            username="admin",
            virtual_host="/custom",
        )
        expected_url = "amqp://admin:secret@rabbitmq.example.com:5673/custom"

        assert config.url == expected_url

    def test_url_generation_special_chars(self):
        """Test URL generation handles special characters."""
        config = RabbitMQConfig(
            password="p@ssw0rd!",
            username="user@domain",
        )

        assert "user@domain" in config.url
        assert "p@ssw0rd!" in config.url


class TestCloseRabbitmqConnection:
    """Tests for close_rabbitmq_connection."""

    @pytest.fixture(autouse=True)
    def reset_connection_singleton(self):
        """Restore _connection to None before and after each test."""
        config_module._connection = None
        yield
        config_module._connection = None

    @pytest.mark.asyncio
    async def test_clears_singleton_when_connection_is_open(self):
        """Should close the connection and reset the singleton to None."""
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        mock_conn.close = AsyncMock()
        config_module._connection = mock_conn

        await close_rabbitmq_connection()

        mock_conn.close.assert_awaited_once()
        assert config_module._connection is None

    @pytest.mark.asyncio
    async def test_skips_close_when_connection_already_closed(self):
        """Should reset singleton without calling close on an already-closed connection."""
        mock_conn = MagicMock()
        mock_conn.is_closed = True
        mock_conn.close = AsyncMock()
        config_module._connection = mock_conn

        await close_rabbitmq_connection()

        mock_conn.close.assert_not_awaited()
        assert config_module._connection is None

    @pytest.mark.asyncio
    async def test_is_noop_when_no_connection(self):
        """Should complete without error when no connection exists."""
        config_module._connection = None

        await close_rabbitmq_connection()

        assert config_module._connection is None

    @pytest.mark.asyncio
    async def test_clears_singleton_even_if_close_raises(self):
        """Should reset singleton to None even when conn.close() raises an exception."""
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        mock_conn.close = AsyncMock(side_effect=RuntimeError("close failed"))
        config_module._connection = mock_conn

        await close_rabbitmq_connection()  # must not raise

        assert config_module._connection is None
