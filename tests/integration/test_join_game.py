# Copyright 2026 Bret McKee
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


"""Integration tests for handle_join_game against a real database.

Calls the handler directly (not via Discord dispatch) with a minimal mock
interaction and real DB fixtures. The bot container is not part of the
integration environment, so Discord API calls are not possible.

The handler uses get_db_session() (RLS-enforced app user). We patch it to
BotAsyncSessionLocal (BYPASSRLS) so the handler can read/write the test data
created by the admin fixtures without needing to set guild context.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.join_game import handle_join_game
from shared.database import BotAsyncSessionLocal, bot_engine
from shared.utils.status_transitions import GameStatus

pytestmark = pytest.mark.integration

JOINER_DISCORD_ID = "500000000000000001"
NEW_USER_DISCORD_ID = "500000000000000002"


def _make_interaction(discord_user_id: str) -> MagicMock:
    """Build minimal Discord interaction mock for join/leave handlers."""
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = int(discord_user_id)
    interaction.user.global_name = None
    interaction.user.name = f"TestUser{discord_user_id[-4:]}"
    interaction.user.display_avatar = None
    interaction.user.send = AsyncMock()
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    return interaction


def _patch_db():
    """Patch get_db_session in join_game module to use BYPASSRLS session."""

    def _bypass():
        return BotAsyncSessionLocal()

    return patch("services.bot.handlers.join_game.get_db_session", side_effect=_bypass)


@pytest.fixture
def mock_publisher() -> MagicMock:
    publisher = MagicMock(spec=BotEventPublisher)
    publisher.publish_game_updated = AsyncMock()
    return publisher


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    """Dispose bot engine pool after each test for clean event loop state."""
    yield
    await bot_engine.dispose()


@pytest.fixture
def test_game(create_guild, create_channel, create_user, create_game):
    """Create a complete game fixture: guild → channel → user → SCHEDULED game."""
    guild = create_guild(discord_guild_id="500111111111111111")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="500222222222222222")
    host = create_user(discord_user_id="500333333333333333")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Join Integration Test Game",
        status=GameStatus.SCHEDULED,
    )
    return {"guild": guild, "channel": channel, "host": host, "game": game}


@pytest.mark.asyncio
async def test_invalid_uuid_returns_error_without_touching_db(
    test_game, mock_publisher, admin_db_sync
) -> None:
    """An unparseable game_id sends an error DM and makes no DB changes."""
    interaction = _make_interaction(JOINER_DISCORD_ID)
    rows_before = admin_db_sync.execute(text("SELECT COUNT(*) FROM game_participants")).scalar()

    with _patch_db():
        await handle_join_game(interaction, "not-a-uuid", mock_publisher)

    rows_after = admin_db_sync.execute(text("SELECT COUNT(*) FROM game_participants")).scalar()
    assert rows_after == rows_before
    mock_publisher.publish_game_updated.assert_not_called()
    interaction.user.send.assert_called_once()
    assert "Invalid game ID" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_game_not_found_sends_error(test_game, mock_publisher) -> None:
    """A valid UUID with no matching game sends the 'Game not found' error."""
    interaction = _make_interaction(JOINER_DISCORD_ID)
    missing_id = str(uuid.uuid4())

    with _patch_db():
        await handle_join_game(interaction, missing_id, mock_publisher)

    mock_publisher.publish_game_updated.assert_not_called()
    interaction.user.send.assert_called_once()
    assert "Game not found" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_non_scheduled_game_sends_error(test_game, mock_publisher, admin_db_sync) -> None:
    """A game that is not SCHEDULED returns the appropriate error."""
    guild = test_game["guild"]
    channel = test_game["channel"]
    host = test_game["host"]
    completed_game_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, title, description, "
            "scheduled_at, max_players, status, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :title, :description, "
            ":scheduled_at, :max_players, :status, :created_at, :updated_at)"
        ),
        {
            "id": completed_game_id,
            "guild_id": guild["id"],
            "channel_id": channel["id"],
            "host_id": host["id"],
            "title": "Completed Game",
            "description": "A completed game",
            "scheduled_at": datetime.now(UTC) - timedelta(hours=1),
            "max_players": 4,
            "status": GameStatus.COMPLETED,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()

    interaction = _make_interaction(JOINER_DISCORD_ID)

    with _patch_db():
        await handle_join_game(interaction, completed_game_id, mock_publisher)

    mock_publisher.publish_game_updated.assert_not_called()
    interaction.user.send.assert_called_once()
    assert "already started or is completed" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_successful_join_existing_user_creates_participant(
    test_game, mock_publisher, create_user, admin_db_sync
) -> None:
    """Happy path: existing user joins a SCHEDULED game; participant row created."""
    player = create_user(discord_user_id=JOINER_DISCORD_ID)
    game = test_game["game"]
    interaction = _make_interaction(JOINER_DISCORD_ID)

    with _patch_db():
        await handle_join_game(interaction, game["id"], mock_publisher)

    rows = admin_db_sync.execute(
        text(
            "SELECT id FROM game_participants "
            "WHERE game_session_id = :game_id AND user_id = :user_id"
        ),
        {"game_id": game["id"], "user_id": player["id"]},
    ).fetchall()
    assert len(rows) == 1, "Participant row must be created after join"

    mock_publisher.publish_game_updated.assert_called_once()
    call_kwargs = mock_publisher.publish_game_updated.call_args.kwargs
    assert call_kwargs["game_id"] == game["id"]
    assert call_kwargs["guild_id"] == test_game["guild"]["id"]


@pytest.mark.asyncio
async def test_successful_join_creates_new_user_when_not_in_db(
    test_game, mock_publisher, admin_db_sync
) -> None:
    """Handler creates a new User row for a Discord user that has no DB record yet."""
    game = test_game["game"]
    interaction = _make_interaction(NEW_USER_DISCORD_ID)

    # Confirm user does not exist before the test
    existing = admin_db_sync.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": NEW_USER_DISCORD_ID},
    ).fetchall()
    assert len(existing) == 0, "Precondition: user must not exist before join"

    with _patch_db():
        await handle_join_game(interaction, game["id"], mock_publisher)

    new_users = admin_db_sync.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": NEW_USER_DISCORD_ID},
    ).fetchall()
    assert len(new_users) == 1, "New User row must be created for unknown Discord user"

    participants = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE game_session_id = :game_id"),
        {"game_id": game["id"]},
    ).fetchall()
    assert len(participants) == 1, "Participant row must be created"

    mock_publisher.publish_game_updated.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_join_does_not_create_second_participant(
    test_game, mock_publisher, create_user, admin_db_sync
) -> None:
    """IntegrityError on duplicate join is swallowed; only one participant row exists."""
    player = create_user(discord_user_id=JOINER_DISCORD_ID)
    game = test_game["game"]
    interaction = _make_interaction(JOINER_DISCORD_ID)

    with _patch_db():
        await handle_join_game(interaction, game["id"], mock_publisher)

    # Reset call count then attempt duplicate join
    mock_publisher.publish_game_updated.reset_mock()
    interaction2 = _make_interaction(JOINER_DISCORD_ID)

    with _patch_db():
        await handle_join_game(interaction2, game["id"], mock_publisher)

    rows = admin_db_sync.execute(
        text(
            "SELECT id FROM game_participants "
            "WHERE game_session_id = :game_id AND user_id = :user_id"
        ),
        {"game_id": game["id"], "user_id": player["id"]},
    ).fetchall()
    assert len(rows) == 1, "Duplicate join must not create a second participant row"
    mock_publisher.publish_game_updated.assert_not_called()
