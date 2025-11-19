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
CORS middleware configuration for the API service.

Configures Cross-Origin Resource Sharing to allow frontend access.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.config import APIConfig


def configure_cors(app: FastAPI, config: APIConfig) -> None:
    """
    Configure CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        config: API configuration with frontend URL
    """
    origins = [
        config.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Note: Cannot use "*" wildcard when allow_credentials=True
    # In debug mode, be more permissive but still specific
    if config.debug:
        origins.extend(
            [
                "http://localhost:5173",  # Vite default dev port
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
