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


"""Integration tests for ButtonHandler.handle_interaction dispatch logic.

Tests the routing in ButtonHandler.handle_interaction (lines 44, 55-78) by
calling it with real game data so the dispatch falls through to the actual
join/leave handlers running against the real DB.

Exception-path and pure-guard tests use minimal mocks where no DB is involved.
"""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.button_handler import ButtonHandler
from shared.database import BotAsyncSessionLocal, bot_engine
from shared.utils.status_transitions import GameStatus

pytestmark = pytest.mark.integration

JOIN_DISCORD_ID = "700000000000000001"
LEAVE_DISCORD_ID = "700000000000000002"


def _make_interaction(custom_id: str | None, discord_user_id: str) -> MagicMock:
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
    interaction.response.send_message = AsyncMock()
    interaction.data = {"custom_id": custom_id} if custom_id is not None else None
    return interaction


@pytest.fixture
def mock_publisher() -> MagicMock:
    publisher = MagicMock(spec=BotEventPublisher)
    publisher.publish_game_updated = AsyncMock()
    return publisher


@pytest.fixture
def handler(mock_publisher: MagicMock) -> ButtonHandler:
    return ButtonHandler(publisher=mock_publisher)


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    yield
    await bot_engine.dispose()


@pytest.fixture
def test_game(create_guild, create_channel, create_user, create_game):
    guild = create_guild(discord_guild_id="700111111111111111")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="700222222222222222")
    host = create_user(discord_user_id="700333333333333333")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Button Handler Integration Test Game",
        status=GameStatus.SCHEDULED,
    )
    assert game
    return {"guild": guild, "channel": channel, "host": host, "game": game}


def _patch_join_db():
    def _bypass():
        return BotAsyncSessionLocal()

    return patch("services.bot.handlers.join_game.get_db_session", side_effect=_bypass)


def _patch_leave_db():
    def _bypass():
        return BotAsyncSessionLocal()

    return patch("services.bot.handlers.leave_game.get_db_session", side_effect=_bypass)


# -- Dispatch path tests (cover lines 55-75 in button_handler.py) ---------------


@pytest.mark.asyncio
async def test_join_game_custom_id_creates_participant(
    handler, mock_publisher, test_game, create_user, admin_db_sync
) -> None:
    """join_game_ prefix dispatches to handle_join_game; participant row is created."""
    player = create_user(discord_user_id=JOIN_DISCORD_ID)
    game = test_game["game"]
    interaction = _make_interaction(f"join_game_{game['id']}", JOIN_DISCORD_ID)

    with _patch_join_db():
        await handler.handle_interaction(interaction)

    rows = admin_db_sync.execute(
        text(
            "SELECT id FROM game_participants "
            "WHERE game_session_id = :game_id AND user_id = :user_id"
        ),
        {"game_id": game["id"], "user_id": player["id"]},
    ).fetchall()
    assert len(rows) == 1, "Participant must be created via join_game_ dispatch"
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=ANY, guild_id=ANY, updated_fields=ANY
    )


@pytest.mark.asyncio
async def test_leave_game_custom_id_removes_participant(
    handler, mock_publisher, test_game, create_user, admin_db_sync
) -> None:
    """leave_game_ prefix dispatches to handle_leave_game; participant row is deleted."""
    player = create_user(discord_user_id=LEAVE_DISCORD_ID)
    game = test_game["game"]

    # Insert participant row manually so leave has something to delete
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game["id"],
            "user_id": player["id"],
            "position": 1,
            "position_type": 1,
        },
    )
    admin_db_sync.commit()

    interaction = _make_interaction(f"leave_game_{game['id']}", LEAVE_DISCORD_ID)

    with _patch_leave_db():
        await handler.handle_interaction(interaction)

    rows = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"), {"id": participant_id}
    ).fetchall()
    assert len(rows) == 0, "Participant must be deleted via leave_game_ dispatch"
    mock_publisher.publish_game_updated.assert_awaited_once_with(
        game_id=ANY, guild_id=ANY, updated_fields=ANY
    )


# -- Pure-logic guard tests (no DB; cover early-return branches) ---------------


@pytest.mark.asyncio
async def test_missing_data_returns_early(handler: ButtonHandler) -> None:
    """Interaction with None data returns before dispatching to any handler."""
    interaction = _make_interaction(None, JOIN_DISCORD_ID)
    interaction.data = None

    join_path = "services.bot.handlers.button_handler.handle_join_game"
    leave_path = "services.bot.handlers.button_handler.handle_leave_game"
    with (
        patch(join_path, new=AsyncMock()) as mock_join,
        patch(leave_path, new=AsyncMock()) as mock_leave,
    ):
        await handler.handle_interaction(interaction)

    mock_join.assert_not_called()
    mock_leave.assert_not_called()


@pytest.mark.asyncio
async def test_non_game_custom_id_returns_early(handler: ButtonHandler) -> None:
    """Unrecognised custom_id prefix is ignored without dispatching."""
    interaction = _make_interaction("other_button_abc", JOIN_DISCORD_ID)

    join_path = "services.bot.handlers.button_handler.handle_join_game"
    leave_path = "services.bot.handlers.button_handler.handle_leave_game"
    with (
        patch(join_path, new=AsyncMock()) as mock_join,
        patch(leave_path, new=AsyncMock()) as mock_leave,
    ):
        await handler.handle_interaction(interaction)

    mock_join.assert_not_called()
    mock_leave.assert_not_called()


# -- Exception-path test (cover lines 76-78) ----------------------------------------


@pytest.mark.asyncio
async def test_exception_in_handler_triggers_error_response(
    handler: ButtonHandler, test_game
) -> None:
    """Unhandled exception sends ephemeral error message while response is not done."""
    game_id = test_game["game"]["id"]
    interaction = _make_interaction(f"join_game_{game_id}", JOIN_DISCORD_ID)
    interaction.response.is_done = MagicMock(return_value=False)

    with patch(
        "services.bot.handlers.button_handler.handle_join_game",
        side_effect=RuntimeError("simulated failure"),
    ):
        await handler.handle_interaction(interaction)

    interaction.response.send_message.assert_called_once()
    assert interaction.response.send_message.call_args.kwargs.get("ephemeral") is True
