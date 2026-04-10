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


"""Integration tests for EmbedDeletionConsumer._handle_embed_deleted.

Verifies that the handler deletes the game row and publishes GAME_CANCELLED
to RabbitMQ when called with valid event data.

Note: These tests call the handler directly (not via RabbitMQ dispatch) because
the bot container is not part of the integration environment. Event dispatch
registration is verified separately in unit tests.
"""

import asyncio
import json
import uuid

import pytest
from sqlalchemy import text

from services.api.services.embed_deletion_consumer import EmbedDeletionConsumer
from shared.database import bot_engine
from shared.messaging.events import Event, EventType
from tests.integration.conftest import consume_one_message, get_queue_message_count

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    """Dispose engine pools after each test for clean event loop state."""
    yield
    await bot_engine.dispose()


@pytest.fixture
def game_cancelled_queue(rabbitmq_channel):
    """Temporary queue bound to game.cancelled for verifying GAME_CANCELLED publications."""
    result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
    queue_name = result.method.queue
    rabbitmq_channel.queue_bind(
        exchange="game_scheduler", queue=queue_name, routing_key="game.cancelled"
    )
    return queue_name


@pytest.mark.asyncio
async def test_handle_embed_deleted_removes_game_and_publishes_cancelled(
    admin_db_sync,
    rabbitmq_channel,
    game_cancelled_queue,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """_handle_embed_deleted must delete the game row and publish GAME_CANCELLED."""
    guild = create_guild(discord_guild_id="550000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="550000000000000002")
    host = create_user(discord_user_id="550000000000000003")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Embed Deletion Consumer Integration Test",
    )

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_before) == 1, "Game must exist before the handler runs"

    consumer = EmbedDeletionConsumer()
    event = Event(
        event_type=EventType.EMBED_DELETED,
        data={"game_id": game["id"], "channel_id": "550000000000000002", "message_id": "1"},
    )

    await consumer._handle_embed_deleted(event)

    # Allow the deferred-publish asyncio task to complete.
    await asyncio.sleep(0.5)

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_after) == 0, "Game must be deleted after the handler runs"

    message_count = get_queue_message_count(rabbitmq_channel, game_cancelled_queue)
    assert message_count == 1, "Handler must publish GAME_CANCELLED to RabbitMQ"

    _, _, body = consume_one_message(rabbitmq_channel, game_cancelled_queue)
    payload = json.loads(body)
    assert str(payload["data"]["game_id"]) == game["id"]


@pytest.mark.asyncio
async def test_handle_embed_deleted_is_idempotent_when_game_missing(
    rabbitmq_channel,
    game_cancelled_queue,
):
    """_handle_embed_deleted must not raise or publish when the game is already gone."""
    consumer = EmbedDeletionConsumer()
    event = Event(
        event_type=EventType.EMBED_DELETED,
        data={
            "game_id": str(uuid.uuid4()),
            "channel_id": "550000000000000002",
            "message_id": "1",
        },
    )

    await consumer._handle_embed_deleted(event)

    await asyncio.sleep(0.5)

    message_count = get_queue_message_count(rabbitmq_channel, game_cancelled_queue)
    assert message_count == 0, "No GAME_CANCELLED must be published when game was not found"
