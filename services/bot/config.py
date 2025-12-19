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


"""Bot configuration management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    """
    Discord bot configuration loaded from environment variables.

    Attributes:
        discord_bot_token: Discord bot authentication token
        discord_client_id: Discord application ID for OAuth2
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
    discord_client_id: str | None = Field(default=None, description="Discord application ID")

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


_config: BotConfig | None = None


def get_config() -> BotConfig:
    """
    Get or create global bot configuration instance.

    Returns:
        Singleton BotConfig instance loaded from environment variables
    """
    global _config
    if _config is None:
        _config = BotConfig()
    return _config
