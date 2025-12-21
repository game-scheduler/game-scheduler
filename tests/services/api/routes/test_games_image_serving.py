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
Tests for game image serving endpoints.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.api.routes import games as games_routes
from services.api.services import games as games_service
from shared.models import game as game_model


@pytest.fixture
def mock_game_service():
    """Mock game service."""
    service = AsyncMock(spec=games_service.GameService)
    return service


@pytest.fixture
def sample_game():
    """Sample game with images."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-123"
    game.title = "Test Game"
    game.thumbnail_data = b"fake_png_data"
    game.thumbnail_mime_type = "image/png"
    game.image_data = b"fake_jpg_data"
    game.image_mime_type = "image/jpeg"
    return game


@pytest.fixture
def sample_game_no_images():
    """Sample game without images."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-456"
    game.title = "Test Game No Images"
    game.thumbnail_data = None
    game.thumbnail_mime_type = None
    game.image_data = None
    game.image_mime_type = None
    return game


@pytest.mark.asyncio
async def test_get_thumbnail_success(mock_game_service, sample_game):
    """Test successful thumbnail retrieval."""
    mock_game_service.get_game.return_value = sample_game

    response = await games_routes.get_game_thumbnail(
        game_id="game-123", game_service=mock_game_service
    )

    assert response.status_code == 200
    assert response.body == b"fake_png_data"
    assert response.media_type == "image/png"
    assert response.headers["Cache-Control"] == "public, max-age=3600"


@pytest.mark.asyncio
async def test_get_thumbnail_game_not_found(mock_game_service):
    """Test thumbnail endpoint with non-existent game."""
    mock_game_service.get_game.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await games_routes.get_game_thumbnail(game_id="invalid", game_service=mock_game_service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Game not found"


@pytest.mark.asyncio
async def test_get_thumbnail_no_thumbnail(mock_game_service, sample_game_no_images):
    """Test thumbnail endpoint when game has no thumbnail."""
    mock_game_service.get_game.return_value = sample_game_no_images

    with pytest.raises(HTTPException) as exc_info:
        await games_routes.get_game_thumbnail(game_id="game-456", game_service=mock_game_service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No thumbnail for this game"


@pytest.mark.asyncio
async def test_get_thumbnail_default_mime_type(mock_game_service):
    """Test thumbnail endpoint with missing MIME type defaults to image/png."""
    game_no_mime = MagicMock(spec=game_model.GameSession)
    game_no_mime.id = "game-789"
    game_no_mime.thumbnail_data = b"fake_png_data"
    game_no_mime.thumbnail_mime_type = None

    mock_game_service.get_game.return_value = game_no_mime

    response = await games_routes.get_game_thumbnail(
        game_id="game-789", game_service=mock_game_service
    )

    assert response.media_type == "image/png"


@pytest.mark.asyncio
async def test_get_image_success(mock_game_service, sample_game):
    """Test successful banner image retrieval."""
    mock_game_service.get_game.return_value = sample_game

    response = await games_routes.get_game_image(game_id="game-123", game_service=mock_game_service)

    assert response.status_code == 200
    assert response.body == b"fake_jpg_data"
    assert response.media_type == "image/jpeg"
    assert response.headers["Cache-Control"] == "public, max-age=3600"


@pytest.mark.asyncio
async def test_get_image_game_not_found(mock_game_service):
    """Test image endpoint with non-existent game."""
    mock_game_service.get_game.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await games_routes.get_game_image(game_id="invalid", game_service=mock_game_service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Game not found"


@pytest.mark.asyncio
async def test_get_image_no_image(mock_game_service, sample_game_no_images):
    """Test image endpoint when game has no banner image."""
    mock_game_service.get_game.return_value = sample_game_no_images

    with pytest.raises(HTTPException) as exc_info:
        await games_routes.get_game_image(game_id="game-456", game_service=mock_game_service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No banner image for this game"


@pytest.mark.asyncio
async def test_get_image_default_mime_type(mock_game_service):
    """Test image endpoint with missing MIME type defaults to image/png."""
    game_no_mime = MagicMock(spec=game_model.GameSession)
    game_no_mime.id = "game-789"
    game_no_mime.image_data = b"fake_jpg_data"
    game_no_mime.image_mime_type = None

    mock_game_service.get_game.return_value = game_no_mime

    response = await games_routes.get_game_image(game_id="game-789", game_service=mock_game_service)

    assert response.media_type == "image/png"
