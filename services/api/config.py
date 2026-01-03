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
Configuration settings for the API service.

Loads environment variables for Discord OAuth2, database, Redis, RabbitMQ,
and API server settings.
"""

import os


class APIConfig:
    """API service configuration from environment variables."""

    def __init__(self):
        """Load configuration from environment variables."""
        self.discord_client_id = os.getenv("DISCORD_BOT_CLIENT_ID", "")
        self.discord_client_secret = os.getenv("DISCORD_BOT_CLIENT_SECRET", "")
        self.discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "")

        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://scheduler:password@localhost:5432/game_scheduler",
        )

        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.api_url = os.getenv("API_URL", "http://localhost:8000")

        self.jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = self.environment == "development"

        self.log_level = os.getenv("LOG_LEVEL", "INFO")


_config_instance: APIConfig | None = None


def get_api_config() -> APIConfig:
    """Get API configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = APIConfig()
    return _config_instance
