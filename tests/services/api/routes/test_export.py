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


"""Tests for calendar export API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from services.api.app import create_app
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.participant import GameParticipant
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
        scheduled_at=datetime(2025, 12, 15, 18, 0, 0),
        max_players=5,
        status="SCHEDULED",
    )
    game.host = User(id="user-123", discord_id="123456789")
    game.guild = GuildConfiguration(id="guild-123", guild_id="987654321")
    game.participants = []
    return game


def test_export_game_as_host_success(app, mock_user, mock_game):
    """Test successful export of game as host."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies
    from services.api.dependencies import auth as auth_deps
    from services.api.dependencies import permissions as permissions_deps
    from shared import database

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        return mock_db

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with patch(
            "services.api.dependencies.permissions.can_export_game",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                return_value=mock_ical,
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


def test_export_game_not_found(app, mock_user):
    """Test export of non-existent game returns 404."""
    # Mock database session returning None
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies
    from services.api.dependencies import auth as auth_deps
    from services.api.dependencies import permissions as permissions_deps
    from shared import database

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        return mock_db

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        client = TestClient(app)
        response = client.get("/api/v1/export/game/game-999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_export_game_permission_denied(app, mock_user, mock_game):
    """Test export without permission returns 403."""
    # User is not host or participant
    mock_game.host_id = "different-user"
    mock_game.participants = []

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies
    from services.api.dependencies import auth as auth_deps
    from services.api.dependencies import permissions as permissions_deps
    from shared import database

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        return mock_db

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with patch(
            "services.api.dependencies.permissions.can_export_game",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                side_effect=PermissionError("You must be the host"),
            ):
                client = TestClient(app)
                response = client.get("/api/v1/export/game/game-123")

                assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_export_game_as_participant(app, mock_user, mock_game):
    """Test successful export as participant."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

    # User is participant but not host
    mock_game.host_id = "different-user"
    participant = GameParticipant(
        id="part-123",
        game_session_id="game-123",
        user_id="123456789",
    )
    participant.user = mock_user.user
    mock_game.participants = [participant]

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock role service
    mock_role_service = AsyncMock()

    # Override dependencies
    from services.api.dependencies import auth as auth_deps
    from services.api.dependencies import permissions as permissions_deps
    from shared import database

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        return mock_db

    async def override_get_role_service():
        return mock_role_service

    app.dependency_overrides[auth_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[permissions_deps.get_role_service] = override_get_role_service

    try:
        with patch(
            "services.api.dependencies.permissions.can_export_game",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "services.api.services.calendar_export.CalendarExportService.export_game",
                new_callable=AsyncMock,
                return_value=mock_ical,
            ):
                client = TestClient(app)
                response = client.get("/api/v1/export/game/game-123")

                assert response.status_code == status.HTTP_200_OK
                assert response.content == mock_ical
    finally:
        app.dependency_overrides.clear()


def test_generate_calendar_filename_basic():
    """Test filename generation with basic title."""
    from services.api.routes.export import generate_calendar_filename

    filename = generate_calendar_filename("D&D Campaign", datetime(2025, 11, 15))
    assert filename == "D-D-Campaign_2025-11-15.ics"


def test_generate_calendar_filename_special_chars():
    """Test filename generation removes special characters."""
    from services.api.routes.export import generate_calendar_filename

    filename = generate_calendar_filename("Poker Night!", datetime(2025, 12, 25))
    assert filename == "Poker-Night_2025-12-25.ics"


def test_generate_calendar_filename_multiple_spaces():
    """Test filename generation normalizes spaces."""
    from services.api.routes.export import generate_calendar_filename

    filename = generate_calendar_filename("Weekly  Game   Night", datetime(2025, 1, 10))
    assert filename == "Weekly-Game-Night_2025-01-10.ics"


def test_generate_calendar_filename_long_title():
    """Test filename generation truncates long titles."""
    from services.api.routes.export import generate_calendar_filename

    long_title = "A" * 150
    filename = generate_calendar_filename(long_title, datetime(2025, 6, 1))
    assert len(filename.split("_")[0]) <= 100
    assert filename.endswith("_2025-06-01.ics")


def test_generate_calendar_filename_emoji_and_unicode():
    """Test filename generation handles emoji and unicode."""
    from services.api.routes.export import generate_calendar_filename

    filename = generate_calendar_filename("🎲 Game Night 🎮", datetime(2025, 3, 15))
    assert filename == "Game-Night_2025-03-15.ics"


def test_generate_calendar_filename_only_special_chars():
    """Test filename generation with title containing only special characters."""
    from services.api.routes.export import generate_calendar_filename

    filename = generate_calendar_filename("!@#$%", datetime(2025, 7, 20))
    assert filename == "_2025-07-20.ics"
