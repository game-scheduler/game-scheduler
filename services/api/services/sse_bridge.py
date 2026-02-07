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


"""
SSE bridge service for real-time game updates.

Consumes game update events from RabbitMQ and broadcasts them to
authorized SSE connections with server-side guild filtering.
"""

import asyncio
import json
import logging

from services.api.auth import oauth2, tokens
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType

logger = logging.getLogger(__name__)


class SSEGameUpdateBridge:
    """
    Bridges RabbitMQ game events to SSE connections.

    Maintains active SSE connections and filters events based on
    user's guild memberships to prevent information disclosure.
    """

    def __init__(self) -> None:
        """Initialize SSE bridge with empty connection registry."""
        self.connections: dict[str, tuple[asyncio.Queue, str, str]] = {}
        self.consumer: EventConsumer | None = None

    async def start_consuming(self) -> None:
        """
        Start consuming RabbitMQ events.

        Connects to web_sse_events queue and subscribes to game.updated.*
        routing keys using wildcard pattern.
        """
        self.consumer = EventConsumer(queue_name="web_sse_events")
        await self.consumer.connect()

        await self.consumer.bind("game.updated.*")

        self.consumer.register_handler(EventType.GAME_UPDATED, self._broadcast_to_clients)

        await self.consumer.start_consuming()

    async def stop_consuming(self) -> None:
        """Stop consuming RabbitMQ events and close connection."""
        if self.consumer:
            await self.consumer.close()
            self.consumer = None
            logger.info("SSE bridge stopped consuming")

    async def _broadcast_to_clients(self, event: Event) -> None:
        """
        Broadcast game update event to authorized SSE connections.

        Checks each connection's guild membership via cached get_user_guilds()
        and only sends events to users who are members of the event's guild.

        Args:
            event: Game update event with guild_id in data
        """
        guild_id = event.data.get("guild_id")
        if not guild_id:
            logger.warning("Game update event missing guild_id: %s", event.data.get("game_id"))
            return

        game_id = event.data.get("game_id")
        message = json.dumps({
            "type": "game_updated",
            "game_id": str(game_id),
            "guild_id": guild_id,
        })

        disconnected_clients: list[str] = []

        for client_id, (queue, session_token, discord_id) in self.connections.items():
            try:
                token_data = await tokens.get_user_tokens(session_token)
                if not token_data:
                    logger.debug("Session expired for client %s", client_id)
                    disconnected_clients.append(client_id)
                    continue

                user_guilds = await oauth2.get_user_guilds(token_data["access_token"], discord_id)

                if guild_id in {g["id"] for g in user_guilds}:
                    try:
                        queue.put_nowait(message)
                        logger.debug(
                            "Sent game_updated event to client %s for game %s", client_id, game_id
                        )
                    except asyncio.QueueFull:
                        logger.warning("Queue full for client %s, dropping event", client_id)

            except Exception as e:
                logger.warning("Failed to check guild membership for client %s: %s", client_id, e)

        for client_id in disconnected_clients:
            self.connections.pop(client_id, None)
            logger.debug("Removed disconnected client: %s", client_id)


_sse_bridge: SSEGameUpdateBridge | None = None


def get_sse_bridge() -> SSEGameUpdateBridge:
    """Get or create SSE bridge singleton."""
    global _sse_bridge  # noqa: PLW0603
    if _sse_bridge is None:
        _sse_bridge = SSEGameUpdateBridge()
    return _sse_bridge
