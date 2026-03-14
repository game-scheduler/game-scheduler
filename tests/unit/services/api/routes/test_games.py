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


"""Unit tests for game routes error handling."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from starlette import status as http_status

from services.api.routes import games as games_routes
from services.api.services import participant_resolver as resolver_module
from shared.schemas import game as game_schemas


@pytest.fixture
def sample_game_data():
    """Sample game data for error responses."""
    return game_schemas.GameCreateRequest(
        template_id="template-123",
        title="Test Game",
        scheduled_at=datetime(2026, 2, 1, 14, 0, 0, tzinfo=UTC),
        description="Test description",
        max_players=4,
    )


@pytest.fixture
def sample_update_data():
    """Sample game update data for error responses."""
    return game_schemas.GameUpdateRequest(
        title="Updated Game",
        description="Updated description",
    )


def test_handle_game_operation_errors_validation_error(sample_game_data):
    """Test handling ValidationError returns 422 with invalid mentions."""
    validation_error = resolver_module.ValidationError(
        invalid_mentions=["@unknown"],
        valid_participants=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(validation_error, sample_game_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail["error"] == "invalid_mentions"
    assert exc_info.value.detail["message"] == "Some @mentions could not be resolved"
    assert exc_info.value.detail["invalid_mentions"] == ["@unknown"]
    assert exc_info.value.detail["valid_participants"] == []
    assert "form_data" in exc_info.value.detail


def test_handle_game_operation_errors_value_error_not_found(sample_update_data):
    """Test handling ValueError with 'not found' returns 404."""
    value_error = ValueError("Game not found")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Game not found"


def test_handle_game_operation_errors_value_error_min_players(sample_update_data):
    """Test handling ValueError with minimum players error returns 422."""
    value_error = ValueError("Minimum players cannot be greater than maximum players")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail == "Minimum players cannot be greater than maximum players"


def test_handle_game_operation_errors_value_error_forbidden(sample_game_data):
    """Test handling generic ValueError returns 403."""
    value_error = ValueError("You do not have permission to perform this action")

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(value_error, sample_game_data)

    assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You do not have permission to perform this action"


def test_handle_game_operation_errors_with_update_data(sample_update_data):
    """Test error handling with GameUpdateBase data."""
    validation_error = resolver_module.ValidationError(
        invalid_mentions=["@invalid"],
        valid_participants=["123"],
    )

    with pytest.raises(HTTPException) as exc_info:
        games_routes._handle_game_operation_errors(validation_error, sample_update_data)

    assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
    form_data = exc_info.value.detail["form_data"]
    assert form_data["title"] == "Updated Game"
    assert form_data["description"] == "Updated description"
