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


"""Tests for calendar export API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.dependencies import auth as auth_deps
from services.api.dependencies import permissions as permissions_deps
from services.api.routes.export import generate_calendar_filename
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.participant import GameParticipant, ParticipantType
from shared.models.user import User
from shared.schemas.auth import CurrentUser


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    user = User(id="user-123", discord_id="123456789")
    return CurrentUser(user=user, access_token="mock_token", session_token="mock_session")


@pytest.fixture
def mock_game():
    """Create mock game session."""
    game = GameSession(
        id="game-123",
        title="Test Game",
        host_id="user-123",
        guild_id="guild-123",
        channel_id="channel-123",
        scheduled_at=datetime(2025, 12, 15, 18, 0, 0, tzinfo=UTC),
        max_players=5,
        status="SCHEDULED",
    )
    game.host = User(id="user-123", discord_id="123456789")
    game.guild = GuildConfiguration(id="guild-123", guild_id="987654321")
    game.participants = []
    return game


def test_export_game_as_host_success(app, mock_user, mock_game, mock_get_user_tokens):
    """Test successful export of game as host."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    # Mock AsyncSessionLocal to return our mock session
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies

    async def override_get_current_user():
        return mock_user

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        # Mock the critical functions
        with (
            patch("shared.database.AsyncSessionLocal", mock_session_local),
            patch(
                "shared.cache.client.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch(
                "shared.cache.projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
            patch(
                "services.api.dependencies.permissions.can_export_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                return_value=mock_ical,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/export/game/game-123")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/calendar; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]
            assert "Test-Game_2025-12-15.ics" in response.headers["content-disposition"]
            assert response.content == mock_ical
    finally:
        app.dependency_overrides.clear()


def test_export_game_not_found(app, mock_user, mock_get_user_tokens):
    """Test export of non-existent game returns 404."""
    # Mock database session returning None
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    # Mock AsyncSessionLocal
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies

    async def override_get_current_user():
        return mock_user

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with (
            patch("shared.database.AsyncSessionLocal", mock_session_local),
            patch(
                "shared.cache.client.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch(
                "shared.cache.projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/export/game/game-999")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_export_game_permission_denied(app, mock_user, mock_game, mock_get_user_tokens):
    """Test export without permission returns 403."""
    # User is not host or participant
    mock_game.host_id = "different-user"
    mock_game.participants = []

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    # Mock AsyncSessionLocal
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies

    async def override_get_current_user():
        return mock_user

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with (
            patch("shared.database.AsyncSessionLocal", mock_session_local),
            patch(
                "shared.cache.client.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch(
                "shared.cache.projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
            patch(
                "services.api.dependencies.permissions.can_export_game",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                side_effect=PermissionError("You must be the host"),
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/export/game/game-123")

            assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_export_game_as_participant(app, mock_user, mock_game, mock_get_user_tokens):
    """Test successful export as participant."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

    # User is participant but not host
    mock_game.host_id = "different-user"
    participant = GameParticipant(
        id="part-123",
        game_session_id="game-123",
        user_id="123456789",
        position_type=ParticipantType.SELF_ADDED,
        position=0,
    )
    participant.user = mock_user.user
    mock_game.participants = [participant]

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    # Mock AsyncSessionLocal
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies

    async def override_get_current_user():
        return mock_user

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with (
            patch("shared.database.AsyncSessionLocal", mock_session_local),
            patch(
                "shared.cache.client.get_redis_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch(
                "shared.cache.projection.get_user_guilds",
                new_callable=AsyncMock,
                return_value=["987654321"],
            ),
            patch(
                "services.api.dependencies.permissions.can_export_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                return_value=mock_ical,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/export/game/game-123")

            assert response.status_code == status.HTTP_200_OK
            assert response.content == mock_ical
    finally:
        app.dependency_overrides.clear()


def test_generate_calendar_filename_basic():
    """Test filename generation with basic title."""

    filename = generate_calendar_filename("D&D Campaign", datetime(2025, 11, 15, tzinfo=UTC))
    assert filename == "D-D-Campaign_2025-11-15.ics"


def test_generate_calendar_filename_special_chars():
    """Test filename generation removes special characters."""

    filename = generate_calendar_filename("Poker Night!", datetime(2025, 12, 25, tzinfo=UTC))
    assert filename == "Poker-Night_2025-12-25.ics"


def test_generate_calendar_filename_multiple_spaces():
    """Test filename generation normalizes spaces."""

    filename = generate_calendar_filename("Weekly  Game   Night", datetime(2025, 1, 10, tzinfo=UTC))
    assert filename == "Weekly-Game-Night_2025-01-10.ics"


def test_generate_calendar_filename_long_title():
    """Test filename generation truncates long titles."""

    long_title = "A" * 150
    filename = generate_calendar_filename(long_title, datetime(2025, 6, 1, tzinfo=UTC))
    assert len(filename.split("_")[0]) <= 100
    assert filename.endswith("_2025-06-01.ics")


def test_generate_calendar_filename_emoji_and_unicode():
    """Test filename generation handles emoji and unicode."""

    filename = generate_calendar_filename("🎲 Game Night 🎮", datetime(2025, 3, 15, tzinfo=UTC))
    assert filename == "Game-Night_2025-03-15.ics"


def test_generate_calendar_filename_only_special_chars():
    """Test filename generation with title containing only special characters."""

    filename = generate_calendar_filename("!@#$%", datetime(2025, 7, 20, tzinfo=UTC))
    assert filename == "_2025-07-20.ics"
