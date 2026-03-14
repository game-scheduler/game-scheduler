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

from shared.messaging.config import RabbitMQConfig


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
