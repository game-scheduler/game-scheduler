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


"""Discord webhook endpoints for automated guild synchronization."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from services.api.dependencies.discord_webhook import validate_discord_webhook

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/discord")
async def discord_webhook(
    validated: Annotated[bytes, Depends(validate_discord_webhook)],
) -> Response:
    """
    Discord webhook endpoint for APPLICATION_AUTHORIZED events.

    Args:
        validated: Validated webhook request body

    Returns:
        Response with appropriate status code
    """
    payload = json.loads(validated)
    webhook_type = payload.get("type")

    if webhook_type == 0:
        logger.debug("Received Discord PING webhook")
        return Response(status_code=204)

    if webhook_type == 1:
        event = payload.get("event", {})
        event_type = event.get("type")

        if event_type == "APPLICATION_AUTHORIZED":
            data = event.get("data", {})
            integration_type = data.get("integration_type")

            if integration_type == 0:
                guild = data.get("guild", {})
                guild_id = guild.get("id")
                guild_name = guild.get("name", "Unknown")

                logger.info(
                    "Received APPLICATION_AUTHORIZED webhook for guild %s (%s)",
                    guild_id,
                    guild_name,
                )
                # TODO: Publish sync_guild message to RabbitMQ
                return Response(status_code=204)

            logger.debug(
                "Ignoring APPLICATION_AUTHORIZED for non-guild install (type=%s)",
                integration_type,
            )
            return Response(status_code=204)

    logger.warning("Unhandled webhook type: %s", webhook_type)
    return Response(status_code=204)
