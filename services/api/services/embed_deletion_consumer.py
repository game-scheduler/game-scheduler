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


"""
Embed deletion consumer for auto-cancelling games whose Discord embeds are deleted.

Consumes EMBED_DELETED RabbitMQ events from the bot service and calls
_delete_game_internal to cancel the matching game without HTTP auth.
"""

import logging

from services.api.services.games import GameService
from shared.database import get_bypass_db_session
from shared.messaging.consumer import EventConsumer
from shared.messaging.deferred_publisher import DeferredEventPublisher
from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher
from shared.utils.status_transitions import GameStatus

logger = logging.getLogger(__name__)


class EmbedDeletionConsumer:
    """
    Cancels games when Discord embed deletion events arrive via RabbitMQ.

    Subscribes to embed.deleted routing key. For each event the consumer
    looks up the game by ID and calls _delete_game_internal, which releases
    images, removes the DB row, and publishes game.cancelled — identical to the
    HTTP delete_game path but without an auth check.
    """

    def __init__(self) -> None:
        """Initialize consumer with no active connection."""
        self.consumer: EventConsumer | None = None

    async def start_consuming(self) -> None:
        """Start consuming EMBED_DELETED events from RabbitMQ."""
        self.consumer = EventConsumer(queue_name="api_embed_deletion_events")
        await self.consumer.connect()

        await self.consumer.bind(EventType.EMBED_DELETED)

        self.consumer.register_handler(EventType.EMBED_DELETED, self._handle_embed_deleted)

        await self.consumer.start_consuming()

    async def stop_consuming(self) -> None:
        """Stop consuming events and close the connection."""
        if self.consumer:
            await self.consumer.close()
            self.consumer = None
            logger.info("Embed deletion consumer stopped")

    async def _handle_embed_deleted(self, event: Event) -> None:
        """
        Handle a single EMBED_DELETED event.

        Looks up the game by game_id from the event payload. If found, cancels
        it via _delete_game_internal and commits the transaction. Unknown game
        IDs are logged and silently dropped (idempotent).

        Args:
            event: EMBED_DELETED event with game_id in data
        """
        game_id = event.data.get("game_id")
        if not game_id:
            logger.warning("EMBED_DELETED event missing game_id: %s", event.data)
            return

        async with get_bypass_db_session() as db:
            base_publisher = EventPublisher()
            publisher = DeferredEventPublisher(db=db, event_publisher=base_publisher)
            game_service = GameService(db=db, event_publisher=publisher)

            game = await game_service.get_game(str(game_id))
            if game is None:
                logger.info("EMBED_DELETED: game %s not found, skipping", game_id)
                return

            if game.status == GameStatus.ARCHIVED:
                logger.info("EMBED_DELETED: game %s is already ARCHIVED, skipping", game_id)
                return

            await game_service._delete_game_internal(game)
            await db.commit()

        logger.info("EMBED_DELETED: cancelled game %s", game_id)
