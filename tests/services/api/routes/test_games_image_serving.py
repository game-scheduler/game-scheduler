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
    return AsyncMock(spec=games_service.GameService)


@pytest.mark.asyncio
async def test_get_thumbnail_success(mock_game_service, sample_game_with_images):
    """Test successful thumbnail retrieval."""
    mock_game_service.get_game.return_value = sample_game_with_images

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
    """Test thumbnail endpoint returns mime type from database."""
    game_with_mime = MagicMock(spec=game_model.GameSession)
    game_with_mime.id = "game-789"

    thumbnail = MagicMock()
    thumbnail.image_data = b"fake_png_data"
    thumbnail.mime_type = "image/png"
    game_with_mime.thumbnail = thumbnail
    game_with_mime.thumbnail_id = "thumb-id"

    mock_game_service.get_game.return_value = game_with_mime

    response = await games_routes.get_game_thumbnail(
        game_id="game-789", game_service=mock_game_service
    )

    assert response.media_type == "image/png"


@pytest.mark.asyncio
async def test_get_image_success(mock_game_service, sample_game_with_images):
    """Test successful banner image retrieval."""
    mock_game_service.get_game.return_value = sample_game_with_images

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
    """Test image endpoint returns mime type from database."""
    game_with_mime = MagicMock(spec=game_model.GameSession)
    game_with_mime.id = "game-789"

    banner_image = MagicMock()
    banner_image.image_data = b"fake_jpg_data"
    banner_image.mime_type = "image/jpeg"
    game_with_mime.banner_image = banner_image
    game_with_mime.banner_image_id = "banner-id"

    mock_game_service.get_game.return_value = game_with_mime

    response = await games_routes.get_game_image(game_id="game-789", game_service=mock_game_service)

    assert response.media_type == "image/jpeg"
