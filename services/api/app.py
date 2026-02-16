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
FastAPI application factory.

Creates and configures the FastAPI application with middleware,
error handlers, and route registration.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: PLC2701
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from services.api import middleware
from services.api.config import get_api_config
from services.api.routes import (
    auth,
    channels,
    export,
    games,
    guilds,
    public,
    sse,
    templates,
    webhooks,
)
from services.api.services.guild_service import sync_all_bot_guilds
from services.api.services.sse_bridge import get_sse_bridge
from shared.cache import client as redis_client
from shared.database import get_db_session
from shared.telemetry import init_telemetry
from shared.version import get_api_version, get_git_version

# Configure logging at module level before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Override any existing configuration
)

# Set log levels for various loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("services.api").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Initialize rate limiter for public endpoints
# Note: slowapi 0.1.9 uses in-memory storage regardless of storage_uri
limiter = Limiter(key_func=get_remote_address)

# Initialize OpenTelemetry instrumentation
init_telemetry("api-service")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.

    Initializes connections on startup and closes them on shutdown.
    Guild isolation event listener registered via import.

    Args:
        _app: FastAPI application instance (unused, required by framework)
    """
    logger.info("Starting API service...")

    redis_instance = await redis_client.get_redis_client()
    logger.info("Redis connection initialized")

    logger.info("Guild isolation middleware registered (event listener active)")

    # Sync all bot guilds on startup
    config = get_api_config()
    if config.discord_bot_token:
        try:
            async with get_db_session() as db:
                result = await sync_all_bot_guilds(db, config.discord_bot_token)
                await db.commit()
                logger.info(
                    "Startup guild sync completed: %d new guilds, %d new channels",
                    result["new_guilds"],
                    result["new_channels"],
                )
        except Exception as e:
            logger.exception("Failed to sync guilds on startup: %s", e)
            # Don't fail startup if guild sync fails
    else:
        logger.warning("Discord bot token not configured, skipping startup guild sync")

    bridge = get_sse_bridge()
    bridge_task = asyncio.create_task(bridge.start_consuming())
    logger.info("SSE bridge started consuming game events")

    yield

    logger.info("Shutting down API service...")

    bridge_task.cancel()
    with suppress(asyncio.CancelledError):
        await bridge_task
    await bridge.stop_consuming()
    logger.info("SSE bridge stopped")

    await redis_instance.disconnect()
    logger.info("Redis connection closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    config = get_api_config()

    app = FastAPI(
        title="Discord Game Scheduler API",
        description="REST API for Discord game scheduling web dashboard",
        version=get_api_version(),
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
        lifespan=lifespan,
    )

    # Configure rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    middleware.cors.configure_cors(app, config)
    middleware.error_handler.configure_error_handlers(app)

    app.include_router(auth.router)
    app.include_router(guilds.router)
    app.include_router(channels.router)
    app.include_router(templates.router)
    app.include_router(games.router)
    app.include_router(export.router)
    app.include_router(public.router)
    app.include_router(sse.router)
    app.include_router(webhooks.router)

    @app.get("/health")
    async def health_check() -> dict[str, str | dict[str, str]]:
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "service": "api",
            "version": {
                "git": get_git_version(),
                "api": get_api_version(),
            },
        }

    @app.get("/api/v1/version")
    async def version_info() -> dict[str, str]:
        """
        Get version information for the API service.

        Returns version details including git version and API version.
        """
        return {
            "service": "api",
            "git_version": get_git_version(),
            "api_version": get_api_version(),
            "api_prefix": "/api/v1",
        }

    logger.info("FastAPI application created (environment: %s)", config.environment)

    # Instrument FastAPI for automatic HTTP tracing
    FastAPIInstrumentor.instrument_app(app)

    return app
