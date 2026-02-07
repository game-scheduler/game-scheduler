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
SSE endpoints for real-time game updates.

Provides Server-Sent Events stream for game state changes.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.api.dependencies.auth import get_current_user
from services.api.services.sse_bridge import get_sse_bridge
from shared.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sse", tags=["sse"])

KEEPALIVE_INTERVAL_SECONDS = 30


@router.get("/game-updates")
async def game_updates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    """
    SSE endpoint for real-time game updates.

    Establishes long-lived connection that receives game_updated events
    for guilds the user is a member of. Events are filtered server-side
    based on cached guild memberships.

    Args:
        current_user: Authenticated user from session cookie

    Returns:
        StreamingResponse with text/event-stream content
    """
    client_id = f"{current_user.user.discord_id}_{uuid.uuid4()}"
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

    bridge = get_sse_bridge()
    bridge.connections[client_id] = (
        queue,
        current_user.session_token,
        current_user.user.discord_id,
    )

    logger.info("SSE connection established: %s", client_id)

    async def event_stream() -> AsyncGenerator[str]:
        """Generate SSE events with keepalive pings."""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(), timeout=KEEPALIVE_INTERVAL_SECONDS
                    )
                    yield f"data: {message}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bridge.connections.pop(client_id, None)
            logger.info("SSE connection closed: %s", client_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
