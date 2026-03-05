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


"""Integration tests for handle_participant_drop_due against a real database.

Verifies that the handler deletes the target participant record and publishes
GAME_UPDATED to RabbitMQ when called with valid event data.

Note: These tests call the handler directly (not via RabbitMQ dispatch) because
the bot container is not part of the integration environment — it requires a real
Discord token. Event dispatch registration is verified separately in unit tests.
"""

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import aio_pika
import discord
import pytest
from sqlalchemy import text

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.participant_drop import handle_participant_drop_due
from shared.database import bot_engine
from shared.messaging.publisher import EventPublisher
from shared.models.participant import ParticipantType
from tests.integration.conftest import consume_one_message, get_queue_message_count

pytestmark = pytest.mark.integration

PLAYER_DISCORD_ID = "444000000000000001"


def _insert_participant(admin_db_sync, game_id: str, user_id: str) -> str:
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": 1,
            "position_type": ParticipantType.HOST_ADDED,
        },
    )
    admin_db_sync.commit()
    return participant_id


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    """Dispose engine pools after each test for clean event loop state."""
    yield
    await bot_engine.dispose()


@pytest.fixture
def game_updated_queue(rabbitmq_channel):
    """Temporary queue bound to game.updated.* for verifying GAME_UPDATED publications."""
    result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
    queue_name = result.method.queue
    rabbitmq_channel.queue_bind(
        exchange="game_scheduler", queue=queue_name, routing_key="game.updated.#"
    )
    return queue_name


@pytest.fixture
async def real_publisher():
    """BotEventPublisher backed by a fresh per-test aio_pika connection."""
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    connection = await aio_pika.connect_robust(rabbitmq_url)
    ep = EventPublisher(connection=connection)
    publisher = BotEventPublisher(publisher=ep)
    await publisher.connect()
    yield publisher
    await publisher.disconnect()
    await connection.close()


@pytest.mark.asyncio
async def test_handler_removes_participant_from_db(
    admin_db_sync,
    rabbitmq_channel,
    real_publisher,
    game_updated_queue,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """handle_participant_drop_due must delete the participant row and publish GAME_UPDATED."""
    guild = create_guild(discord_guild_id="333000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="333000000000000002")
    host = create_user(discord_user_id="333000000000000003")
    player = create_user(discord_user_id=PLAYER_DISCORD_ID)

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Drop Integration Test Game",
    )
    participant_id = _insert_participant(admin_db_sync, game["id"], player["id"])

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": participant_id},
    ).fetchall()
    assert len(rows_before) == 1, "Participant must exist before the handler runs"

    mock_bot = MagicMock(spec=discord.Client)
    mock_bot.fetch_user = AsyncMock(return_value=AsyncMock())

    data = {"game_id": game["id"], "participant_id": participant_id}

    await handle_participant_drop_due(data, mock_bot, real_publisher)

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": participant_id},
    ).fetchall()
    assert len(rows_after) == 0, "Participant must be deleted after the handler runs"

    message_count = get_queue_message_count(rabbitmq_channel, game_updated_queue)
    assert message_count == 1, "Handler must publish GAME_UPDATED to RabbitMQ"

    _, _, body = consume_one_message(rabbitmq_channel, game_updated_queue)
    payload = json.loads(body)
    assert payload["data"]["game_id"] == game["id"]


@pytest.mark.asyncio
async def test_handler_is_idempotent_when_participant_missing(
    admin_db_sync,
    rabbitmq_channel,
    real_publisher,
    game_updated_queue,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """handle_participant_drop_due must not raise or publish when participant is already gone."""
    guild = create_guild(discord_guild_id="334000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="334000000000000002")
    host = create_user(discord_user_id="334000000000000003")

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Idempotent Drop Test",
    )

    missing_participant_id = str(uuid.uuid4())

    mock_bot = MagicMock(spec=discord.Client)
    mock_bot.fetch_user = AsyncMock(return_value=AsyncMock())

    data = {"game_id": game["id"], "participant_id": missing_participant_id}

    await handle_participant_drop_due(data, mock_bot, real_publisher)

    message_count = get_queue_message_count(rabbitmq_channel, game_updated_queue)
    assert message_count == 0, "No GAME_UPDATED must be published when participant was not found"
