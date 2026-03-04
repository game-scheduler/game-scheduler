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


"""Unit tests for GameService._persist_and_publish helper method.

These tests verify that _persist_and_publish produces the same DB state and
RabbitMQ events as the original create_game steps 5-8 it replaces.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.services.games import GameService
from shared.models import channel as channel_model
from shared.models import game as game_model


@pytest.fixture
def mock_game():
    """Create a minimal mock GameSession."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-uuid-1234"
    game.title = "Test Game"
    game.guild_id = "guild-uuid-1234"
    game.host_id = "host-uuid-1234"
    game.channel_id = "channel-uuid-1234"
    game.scheduled_at = datetime.datetime(2026, 6, 1, 18, 0, 0)
    game.max_players = 4
    game.notify_role_ids = []
    game.signup_method = "normal"
    game.status = game_model.GameStatus.SCHEDULED.value
    return game


@pytest.fixture
def mock_channel_config():
    """Create a minimal mock ChannelConfiguration."""
    channel = MagicMock(spec=channel_model.ChannelConfiguration)
    channel.channel_id = "discord-channel-id"
    return channel


@pytest.fixture
def resolved_fields():
    """Resolved fields dict as produced by create_game."""
    return {
        "reminder_minutes": [30, 10],
        "expected_duration_minutes": 120,
        "where": "Discord",
        "max_players": 4,
        "signup_instructions": None,
        "signup_method": "normal",
    }


@pytest.fixture
def game_service():
    """Build a GameService with all dependencies mocked."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    event_publisher = MagicMock()
    event_publisher.publish_deferred = MagicMock()

    discord_client = AsyncMock()
    participant_resolver = AsyncMock()
    channel_resolver = AsyncMock()

    return GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=discord_client,
        participant_resolver=participant_resolver,
        channel_resolver=channel_resolver,
    )


@pytest.mark.asyncio
async def test_persist_and_publish_adds_game_to_db(
    game_service, mock_game, mock_channel_config, resolved_fields
):
    """_persist_and_publish must add the game to the session and flush."""
    with (
        patch.object(game_service, "_create_participant_records", new=AsyncMock()),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "get_game", new=AsyncMock(return_value=mock_game)),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
        patch.object(
            game_service.db,
            "execute",
            new=AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_game))),
        ),
    ):
        await game_service._persist_and_publish(mock_game, [], resolved_fields, mock_channel_config)

    game_service.db.add.assert_called_once_with(mock_game)
    game_service.db.flush.assert_called()


@pytest.mark.asyncio
async def test_persist_and_publish_creates_participant_records(
    game_service, mock_game, mock_channel_config, resolved_fields
):
    """_persist_and_publish must call _create_participant_records with given participants."""
    participants = [{"type": "discord", "discord_id": "111", "original_input": "@user"}]
    mock_create = AsyncMock()

    with (
        patch.object(game_service, "_create_participant_records", new=mock_create),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "get_game", new=AsyncMock(return_value=mock_game)),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
        patch.object(
            game_service.db,
            "execute",
            new=AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_game))),
        ),
    ):
        await game_service._persist_and_publish(
            mock_game, participants, resolved_fields, mock_channel_config
        )

    mock_create.assert_called_once_with(mock_game.id, participants)


@pytest.mark.asyncio
async def test_persist_and_publish_sets_up_schedules(
    game_service, mock_game, mock_channel_config, resolved_fields
):
    """_persist_and_publish must call _setup_game_schedules with reminder and duration fields."""
    mock_setup = AsyncMock()

    with (
        patch.object(game_service, "_create_participant_records", new=AsyncMock()),
        patch.object(game_service, "_setup_game_schedules", new=mock_setup),
        patch.object(game_service, "get_game", new=AsyncMock(return_value=mock_game)),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
        patch.object(
            game_service.db,
            "execute",
            new=AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_game))),
        ),
    ):
        await game_service._persist_and_publish(mock_game, [], resolved_fields, mock_channel_config)

    mock_setup.assert_called_once_with(
        mock_game,
        resolved_fields["reminder_minutes"],
        resolved_fields["expected_duration_minutes"],
    )


@pytest.mark.asyncio
async def test_persist_and_publish_fires_game_created_event(
    game_service, mock_game, mock_channel_config, resolved_fields
):
    """_persist_and_publish must publish the GAME_CREATED event."""
    mock_publish = AsyncMock()

    with (
        patch.object(game_service, "_create_participant_records", new=AsyncMock()),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "get_game", new=AsyncMock(return_value=mock_game)),
        patch.object(game_service, "_publish_game_created", new=mock_publish),
        patch.object(
            game_service.db,
            "execute",
            new=AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_game))),
        ),
    ):
        await game_service._persist_and_publish(mock_game, [], resolved_fields, mock_channel_config)

    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    assert call_args[0][1] is mock_channel_config


@pytest.mark.asyncio
async def test_persist_and_publish_returns_reloaded_game(
    game_service, mock_game, mock_channel_config, resolved_fields
):
    """_persist_and_publish must return the reloaded game from get_game."""
    reloaded_game = MagicMock(spec=game_model.GameSession)
    reloaded_game.id = mock_game.id

    with (
        patch.object(game_service, "_create_participant_records", new=AsyncMock()),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "get_game", new=AsyncMock(return_value=reloaded_game)),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
        patch.object(
            game_service.db,
            "execute",
            new=AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_game))),
        ),
    ):
        result = await game_service._persist_and_publish(
            mock_game, [], resolved_fields, mock_channel_config
        )

    assert result is reloaded_game
