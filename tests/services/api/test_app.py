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


"""Tests for API application factory."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api import app


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    return mock_client


@pytest.fixture
def mock_get_redis_client(mock_redis_client):
    """Mock get_redis_client function."""
    with patch("services.api.app.redis_client.get_redis_client") as mock:
        mock.return_value = mock_redis_client
        yield mock


def test_create_app_returns_fastapi_instance():
    """Test that create_app returns a FastAPI application instance."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        assert isinstance(application, FastAPI)


def test_create_app_configures_title_and_version():
    """Test that application has correct title and version."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        assert application.title == "Discord Game Scheduler API"
        assert application.version == "1.0.0"


def test_create_app_enables_docs_in_debug_mode():
    """Test that OpenAPI docs are enabled in debug mode."""
    with patch("services.api.app.get_api_config") as mock_config:
        mock_config.return_value.debug = True
        with patch("services.api.app.redis_client.get_redis_client"):
            application = app.create_app()
            assert application.docs_url == "/docs"
            assert application.redoc_url == "/redoc"


def test_create_app_disables_docs_in_production():
    """Test that OpenAPI docs are disabled in production mode."""
    with patch("services.api.app.get_api_config") as mock_config:
        mock_config.return_value.debug = False
        with patch("services.api.app.redis_client.get_redis_client"):
            application = app.create_app()
            assert application.docs_url is None
            assert application.redoc_url is None


def test_health_check_endpoint():
    """Test that health check endpoint returns correct response."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        client = TestClient(application)

        response = client.get("/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert response_data["service"] == "api"
        assert "version" in response_data


@pytest.mark.asyncio
async def test_lifespan_initializes_redis(mock_get_redis_client, mock_redis_client):
    """Test that lifespan initializes Redis connection on startup."""
    application = app.create_app()

    async with app.lifespan(application):
        pass

    mock_get_redis_client.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_disconnects_redis(mock_get_redis_client, mock_redis_client):
    """Test that lifespan disconnects Redis on shutdown."""
    application = app.create_app()

    async with app.lifespan(application):
        pass

    mock_redis_client.disconnect.assert_called_once()


def test_middleware_configured():
    """Test that CORS and error handler middleware are configured."""
    with patch("services.api.app.middleware.cors.configure_cors") as mock_cors:
        with patch(
            "services.api.app.middleware.error_handler.configure_error_handlers"
        ) as mock_error:
            with patch("services.api.app.redis_client.get_redis_client"):
                application = app.create_app()

                mock_cors.assert_called_once()
                mock_error.assert_called_once()

                # Verify the app was passed to both middleware configurers
                assert mock_cors.call_args[0][0] == application
                assert mock_error.call_args[0][0] == application
