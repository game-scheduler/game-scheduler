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
FastAPI application factory.

Creates and configures the FastAPI application with middleware,
error handlers, and route registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.api import middleware
from services.api.config import get_api_config
from services.api.routes import auth, channels, guilds
from shared.cache import client as redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes connections on startup and closes them on shutdown.

    Args:
        app: FastAPI application instance
    """
    logger.info("Starting API service...")

    redis_instance = await redis_client.get_redis_client()
    logger.info("Redis connection initialized")

    yield

    logger.info("Shutting down API service...")

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
        version="1.0.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
        lifespan=lifespan,
    )

    middleware.cors.configure_cors(app, config)
    middleware.error_handler.configure_error_handlers(app)

    app.include_router(auth.router)
    app.include_router(guilds.router)
    app.include_router(channels.router)

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "service": "api"}

    logger.info(f"FastAPI application created (environment: {config.environment})")

    return app
