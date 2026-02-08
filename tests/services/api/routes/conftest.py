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


"""Shared fixtures for API routes tests."""

from unittest.mock import MagicMock

import pytest

from shared.models import game as game_model


def create_mock_game_image(image_data: bytes, mime_type: str) -> MagicMock:
    """
    Create a mock GameImage with proper structure.

    Helper to create consistent GameImage mocks for tests that need
    image relationships.
    """
    image = MagicMock()
    image.image_data = image_data
    image.mime_type = mime_type
    return image


@pytest.fixture
def sample_game_with_images():
    """
    Sample game with both thumbnail and banner images.

    This fixture provides a properly mocked GameSession with image
    relationships matching the new database schema.
    """
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-123"
    game.title = "Test Game"

    # Mock thumbnail relationship
    game.thumbnail = create_mock_game_image(b"fake_png_data", "image/png")
    game.thumbnail_id = "thumb-id"

    # Mock banner_image relationship
    game.banner_image = create_mock_game_image(b"fake_jpg_data", "image/jpeg")
    game.banner_image_id = "banner-id"

    return game


@pytest.fixture
def sample_game_no_images():
    """
    Sample game without images.

    This fixture provides a game session with no image relationships.
    """
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-456"
    game.title = "Test Game No Images"
    game.thumbnail = None
    game.thumbnail_id = None
    game.banner_image = None
    game.banner_image_id = None
    return game
