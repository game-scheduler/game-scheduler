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


"""Integration tests for SSE bridge infrastructure.

Validates SSE bridge infrastructure without Discord complexity, covering:
1. RabbitMQ message delivery to SSE clients
2. Guild authorization filtering (server-side)
3. Concurrent connection handling

These tests verify the core SSE functionality for real-time game updates
across web and Discord interfaces.
"""

import asyncio
import json
import logging
import os
from uuid import uuid4

import aio_pika
import httpx
import pytest

from services.api.services.sse_bridge import get_sse_bridge
from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)

TEST_BOT_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_tests"
TEST_BOT_DISCORD_ID_A = "test_bot_a_123456789"
TEST_BOT_DISCORD_ID_B = "test_bot_b_987654321"


@pytest.fixture
async def rabbitmq_publisher():
    """
    EventPublisher for integration tests with isolated connection.

    Creates a dedicated RabbitMQ connection for this test without touching
    the global singleton, ensuring hermetic test isolation.
    """
    loop = asyncio.get_running_loop()
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    test_connection = await aio_pika.connect_robust(
        rabbitmq_url, timeout=60, heartbeat=60, loop=loop
    )

    publisher = EventPublisher(connection=test_connection)
    await publisher.connect()

    yield publisher

    await publisher.close()

    if test_connection and not test_connection.is_closed:
        await test_connection.close()


@pytest.fixture
async def authenticated_client_guild_a(
    api_base_url,
    create_guild,
    create_user,
    seed_redis_cache,
):
    """Authenticated HTTP client for user in Guild A."""
    guild_a = create_guild()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID_A)

    session_token, _ = await create_test_session(TEST_BOT_TOKEN, TEST_BOT_DISCORD_ID_A)

    # Seed user's guild membership in cache
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID_A,
        guild_discord_id=guild_a["guild_id"],
    )

    client = httpx.AsyncClient(base_url=api_base_url, timeout=30.0)
    client.cookies.set("session_token", session_token)

    yield client, guild_a

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def authenticated_client_guild_b(
    api_base_url,
    create_guild,
    create_user,
    seed_redis_cache,
):
    """Authenticated HTTP client for user in Guild B."""
    guild_b = create_guild()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID_B)

    session_token, _ = await create_test_session(TEST_BOT_TOKEN, TEST_BOT_DISCORD_ID_B)

    # Seed user's guild membership in cache
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID_B,
        guild_discord_id=guild_b["guild_id"],
    )

    client = httpx.AsyncClient(base_url=api_base_url, timeout=30.0)
    client.cookies.set("session_token", session_token)

    yield client, guild_b

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def create_authenticated_client_factory(api_base_url, create_user, seed_redis_cache):
    """Factory to create multiple authenticated clients for same guild."""
    created_clients: list[tuple[httpx.AsyncClient, str]] = []

    async def _create_client(guild_discord_id: str) -> httpx.AsyncClient:
        discord_id = f"test_user_{uuid4().hex[:8]}"
        create_user(discord_user_id=discord_id)
        session_token, _ = await create_test_session(TEST_BOT_TOKEN, discord_id)

        await seed_redis_cache(
            user_discord_id=discord_id,
            guild_discord_id=guild_discord_id,
        )

        client = httpx.AsyncClient(base_url=api_base_url, timeout=30.0)
        client.cookies.set("session_token", session_token)
        created_clients.append((client, session_token))

        return client

    yield _create_client

    for client, session_token in created_clients:
        await client.aclose()
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_sse_receives_rabbitmq_game_updated_events(
    authenticated_client_guild_a,
    rabbitmq_publisher,
):
    """SSE client receives game.updated events published to RabbitMQ."""
    client, guild_a = authenticated_client_guild_a
    test_game_id = str(uuid4())

    async with client.stream(
        "GET",
        "/api/v1/sse/game-updates",
        timeout=30.0,
    ) as response:
        assert response.status_code == 200

        # Publish game.updated event to RabbitMQ
        await rabbitmq_publisher.publish(
            event=Event(
                event_type=EventType.GAME_UPDATED,
                data={
                    "game_id": test_game_id,
                    "guild_id": guild_a["id"],
                },
            ),
            routing_key=f"game.updated.{guild_a['guild_id']}",
        )

        # Read SSE stream with timeout
        received_event = None
        timeout_task = asyncio.create_task(asyncio.sleep(5.0))
        read_task = asyncio.create_task(anext(response.aiter_lines()))

        done, pending = await asyncio.wait(
            [timeout_task, read_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        if read_task in done:
            line = await read_task
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("type") == "game_updated":
                    received_event = data

    assert received_event is not None, "SSE event not received within timeout"
    assert received_event["game_id"] == test_game_id
    assert received_event["guild_id"] == guild_a["id"]


@pytest.mark.asyncio
async def test_sse_filters_events_by_guild_membership(
    authenticated_client_guild_a,
    authenticated_client_guild_b,
    rabbitmq_publisher,
):
    """SSE clients only receive events for guilds they're authorized to access."""
    client_a, guild_a = authenticated_client_guild_a
    client_b, guild_b = authenticated_client_guild_b

    guild_a_events: list[dict] = []
    guild_b_events: list[dict] = []

    async def consume_sse_events(client, event_list, max_events=2):
        """Helper to consume SSE events into list."""
        async with client.stream(
            "GET",
            "/api/v1/sse/game-updates",
            timeout=10.0,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "game_updated":
                        event_list.append(data)
                        if len(event_list) >= max_events:
                            return

    # Start both SSE consumers
    consumer_a = asyncio.create_task(consume_sse_events(client_a, guild_a_events))
    consumer_b = asyncio.create_task(consume_sse_events(client_b, guild_b_events))

    # Wait for connections to establish
    await asyncio.sleep(0.5)

    # Publish event for Guild A
    game_id_a = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            event_type=EventType.GAME_UPDATED,
            data={"game_id": game_id_a, "guild_id": guild_a["id"]},
        ),
        routing_key=f"game.updated.{guild_a['guild_id']}",
    )

    # Publish event for Guild B
    game_id_b = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            event_type=EventType.GAME_UPDATED,
            data={"game_id": game_id_b, "guild_id": guild_b["id"]},
        ),
        routing_key=f"game.updated.{guild_b['guild_id']}",
    )

    # Wait for event processing
    await asyncio.sleep(2.0)

    # Cancel consumers
    consumer_a.cancel()
    consumer_b.cancel()

    await asyncio.gather(consumer_a, consumer_b, return_exceptions=True)

    # Assertions: Each client only received events for their guild
    assert len(guild_a_events) == 1, "Guild A user should receive exactly 1 event"
    assert guild_a_events[0]["game_id"] == game_id_a
    assert guild_a_events[0]["guild_id"] == guild_a["id"]

    assert len(guild_b_events) == 1, "Guild B user should receive exactly 1 event"
    assert guild_b_events[0]["game_id"] == game_id_b
    assert guild_b_events[0]["guild_id"] == guild_b["id"]

    # Critical: Verify NO cross-guild leakage
    guild_a_game_ids = [e["game_id"] for e in guild_a_events]
    guild_b_game_ids = [e["game_id"] for e in guild_b_events]

    assert game_id_b not in guild_a_game_ids, "Guild A user MUST NOT receive Guild B events"
    assert game_id_a not in guild_b_game_ids, "Guild B user MUST NOT receive Guild A events"


@pytest.mark.asyncio
async def test_sse_broadcasts_to_multiple_clients(
    create_authenticated_client_factory,
    create_guild,
    rabbitmq_publisher,
):
    """SSE bridge broadcasts events to all authorized concurrent connections."""
    # Configure short keepalive interval for faster test execution
    bridge = get_sse_bridge()
    bridge.set_keepalive_interval(1)

    guild = create_guild()
    num_clients = 5
    client_events: list[list[dict]] = [[] for _ in range(num_clients)]
    ready_events = [asyncio.Event() for _ in range(num_clients)]

    async def consume_sse(client, event_list, ready_event, client_num):
        """Consumer that collects SSE events, signals when ready."""
        try:
            async with client.stream(
                "GET",
                "/api/v1/sse/game-updates",
                timeout=10.0,
            ) as response:
                ready_event.set()
                await asyncio.sleep(0.1)

                async for line in response.aiter_lines():
                    if line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        data_json = line[5:].strip()
                        try:
                            data = json.loads(data_json)
                            if data.get("type") == "game_updated":
                                event_list.append(data)
                                return
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

    clients = []
    for _ in range(num_clients):
        client = await create_authenticated_client_factory(guild["guild_id"])
        clients.append(client)

    consumer_tasks = [
        asyncio.create_task(consume_sse(client, client_events[i], ready_events[i], i))
        for i, client in enumerate(clients)
    ]

    await asyncio.gather(*[event.wait() for event in ready_events])

    test_game_id = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            event_type=EventType.GAME_UPDATED,
            data={
                "game_id": test_game_id,
                "guild_id": guild["id"],
            },
        ),
        routing_key=f"game.updated.{guild['guild_id']}",
    )

    done, pending = await asyncio.wait(consumer_tasks, timeout=5.0)

    for task in consumer_tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*consumer_tasks, return_exceptions=True)

    for i, events in enumerate(client_events):
        assert len(events) == 1, f"Client {i} should receive exactly 1 event"
        assert events[0]["game_id"] == test_game_id
        assert events[0]["guild_id"] == guild["id"]

    # Verify all clients got same event
    received_game_ids = [events[0]["game_id"] for events in client_events]
    assert all(game_id == test_game_id for game_id in received_game_ids)
