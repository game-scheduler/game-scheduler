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
Configuration settings for the API service.

Loads environment variables for Discord OAuth2, database, Redis, RabbitMQ,
and API server settings.
"""

import os
from urllib.parse import urlparse


def _get_cookie_domain(frontend_url: str, backend_url: str) -> str | None:
    """Derive cookie domain from frontend and backend URLs.

    If URLs are on different subdomains of the same parent domain, returns
    the common parent domain with leading dot for subdomain sharing.
    If same domain or no common parent, returns None for browser default.

    Args:
        frontend_url: Frontend application URL
        backend_url: Backend API URL

    Returns:
        Cookie domain string with leading dot, or None

    Examples:
        >>> _get_cookie_domain('https://app.example.com', 'https://api.example.com')
        '.example.com'
        >>> _get_cookie_domain('http://localhost:3000', 'http://localhost:8000')
        None
    """
    frontend_host = urlparse(frontend_url).hostname
    backend_host = urlparse(backend_url).hostname

    if not frontend_host or not backend_host:
        return None

    # Same hostname = no domain needed (same origin)
    if frontend_host == backend_host:
        return None

    # Different hostnames = find common parent domain
    frontend_parts = frontend_host.split(".")
    backend_parts = backend_host.split(".")

    min_domain_parts = 2
    # Find common suffix by comparing from right to left
    common_parts: list[str] = []
    for frontend_part, backend_part in zip(
        reversed(frontend_parts), reversed(backend_parts), strict=False
    ):
        if frontend_part == backend_part:
            common_parts.insert(0, frontend_part)
        else:
            break

    # Need at least 2 parts for valid domain (e.g., 'example.com')
    if len(common_parts) >= min_domain_parts:
        return "." + ".".join(common_parts)

    return None


class APIConfig:
    """API service configuration from environment variables."""

    def __init__(self) -> None:
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

        self.api_host = os.getenv(
            "API_HOST",
            "0.0.0.0",  # noqa: S104 - Intentional for container
        )
        self.api_port = int(os.getenv("API_PORT", "8000"))

        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        self.jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = self.environment == "development"

        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Derive cookie domain for cross-subdomain sharing
        self.cookie_domain = _get_cookie_domain(self.frontend_url, self.backend_url)


_config_instance: APIConfig | None = None


def get_api_config() -> APIConfig:
    """Get API configuration singleton."""
    global _config_instance  # noqa: PLW0603 - Singleton pattern for config instance
    if _config_instance is None:
        _config_instance = APIConfig()
    return _config_instance
