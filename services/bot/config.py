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


"""Bot configuration management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    """
    Discord bot configuration loaded from environment variables.

    Attributes:
        discord_bot_token: Discord bot authentication token
        discord_bot_client_id: Discord application ID for OAuth2
        database_url: PostgreSQL connection string with asyncpg driver
        rabbitmq_url: RabbitMQ AMQP connection string
        redis_url: Redis connection string
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name (development, staging, production)
        frontend_url: Frontend application URL for calendar download links
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Make Discord tokens optional for integration tests
    discord_bot_token: str | None = Field(default=None, description="Discord bot token")
    discord_bot_client_id: str | None = Field(default=None, description="Discord application ID")
    discord_api_base_url: str = Field(
        default="https://discord.com/api/v10",
        description="Discord API base URL",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/game_scheduler",
        description="PostgreSQL connection URL",
    )

    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    environment: str = Field(
        default="development",
        description="Environment name",
    )

    frontend_url: str = Field(
        default="http://localhost:5173",
        description="Frontend application URL for calendar downloads",
    )

    backend_url: str = Field(
        default="http://localhost:8000",
        description="Backend API URL for image URLs in Discord embeds and frontend calls",
    )


_config: BotConfig | None = None


def get_config() -> BotConfig:
    """
    Get or create global bot configuration instance.

    Returns:
        Singleton BotConfig instance loaded from environment variables
    """
    global _config  # noqa: PLW0603 - Singleton pattern for bot config instance
    if _config is None:
        _config = BotConfig()
    return _config
