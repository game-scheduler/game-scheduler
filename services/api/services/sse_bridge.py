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

from sqlalchemy import select

from services.api.auth import oauth2, tokens
from shared.database import get_bypass_db_session
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType
from shared.models.guild import GuildConfiguration

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
        self.keepalive_interval_seconds: int = 30

    def set_keepalive_interval(self, seconds: int) -> None:
        """
        Set keepalive interval for SSE connections.

        Args:
            seconds: Interval in seconds between keepalive pings
        """
        if seconds <= 0:
            msg = "Keepalive interval must be positive"
            raise ValueError(msg)
        self.keepalive_interval_seconds = seconds

    async def start_consuming(self) -> None:
        """
        Start consuming RabbitMQ events.

        Connects to web_sse_events queue and subscribes to game.updated.#
        routing keys using wildcard pattern to match guild-specific events.
        """
        self.consumer = EventConsumer(queue_name="web_sse_events")
        await self.consumer.connect()

        await self.consumer.bind("game.updated.#")

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
            event: Game update event with guild_id (UUID) in data
        """
        logger.info("SSE bridge received event: %s", event.data)

        guild_uuid = event.data.get("guild_id")
        if not guild_uuid:
            logger.warning("Game update event missing guild_id: %s", event.data.get("game_id"))
            return

        # Look up Discord snowflake ID from UUID using BYPASSRLS session
        async with get_bypass_db_session() as db:
            guild_result = await db.execute(
                select(GuildConfiguration.guild_id).where(GuildConfiguration.id == guild_uuid)
            )
            discord_guild_id = guild_result.scalar_one_or_none()

        if not discord_guild_id:
            logger.warning("Guild UUID not found in database: %s", guild_uuid)
            return

        game_id = event.data.get("game_id")
        message = json.dumps({
            "type": "game_updated",
            "game_id": str(game_id),
            "guild_id": guild_uuid,
        })

        logger.info(
            (
                "Broadcasting game update to %d connections: "
                "game=%s, guild_uuid=%s, discord_guild_id=%s"
            ),
            len(self.connections),
            game_id,
            guild_uuid,
            discord_guild_id,
        )

        disconnected_clients: list[str] = []

        for client_id, (queue, session_token, discord_id) in list(self.connections.items()):
            try:
                token_data = await tokens.get_user_tokens(session_token)
                if not token_data:
                    disconnected_clients.append(client_id)
                    continue
                user_guilds = await oauth2.get_user_guilds(token_data["access_token"], discord_id)
                user_guild_ids = {g["id"] for g in user_guilds}

                logger.info(
                    "Guild check: discord_guild_id=%s (type=%s), user has %d guilds, match=%s",
                    discord_guild_id,
                    type(discord_guild_id).__name__,
                    len(user_guild_ids),
                    discord_guild_id in user_guild_ids,
                )

                if discord_guild_id in user_guild_ids:
                    try:
                        queue.put_nowait(message)
                        logger.info("Sent game update to client %s", client_id)
                    except asyncio.QueueFull:
                        logger.warning(
                            "Queue full for client %s, dropping event",
                            client_id,
                        )
                else:
                    logger.debug(
                        "Client %s not in guild %s, skipping",
                        client_id,
                        discord_guild_id,
                    )

            except Exception as e:
                logger.warning(
                    "Failed to check guild membership for client %s: %s",
                    client_id,
                    e,
                )

        for client_id in disconnected_clients:
            self.connections.pop(client_id, None)


_sse_bridge: SSEGameUpdateBridge | None = None


def get_sse_bridge() -> SSEGameUpdateBridge:
    """Get or create SSE bridge singleton."""
    global _sse_bridge  # noqa: PLW0603
    if _sse_bridge is None:
        _sse_bridge = SSEGameUpdateBridge()
    return _sse_bridge
