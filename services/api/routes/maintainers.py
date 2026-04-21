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


"""Maintainer privilege endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from services.api import dependencies
from services.api.auth import oauth2
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import ttl as cache_ttl
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/maintainers", tags=["maintainers"])


@router.post("/toggle")
async def toggle_maintainer_mode(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
) -> dict[str, bool]:
    """Toggle maintainer mode for the current user.

    Requires can_be_maintainer in session. When enabling, re-validates against
    Discord application info (cached). When disabling, clears the flag directly.
    """
    redis = await cache_client.get_redis_client()
    session_key = f"api:session:{current_user.session_token}"
    session_data = await redis.get_json(session_key)

    if not session_data or not session_data.get("can_be_maintainer"):
        err_msg = "Not eligible for maintainer mode"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)

    discord_id = str(session_data.get("user_id", ""))
    currently_enabled = bool(session_data.get("is_maintainer"))

    if currently_enabled:
        session_data["is_maintainer"] = False
        await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)
        logger.info("Maintainer mode disabled for user %s", discord_id)
        return {"is_maintainer": False}

    if not await oauth2.is_app_maintainer(discord_id):
        err_msg = "User is not in the application team"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)

    session_data["is_maintainer"] = True
    await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)

    logger.info("Maintainer mode enabled for user %s", discord_id)
    return {"is_maintainer": True}


@router.post("/refresh")
async def refresh_maintainers(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
) -> dict[str, str]:
    """Revoke all other elevated maintainer sessions and flush the app info cache.

    Requires is_maintainer in session. Scans all session:* Redis keys and
    deletes those with is_maintainer=True (excluding the caller's session).
    Also deletes the discord:app_info cache key so the next login or
    elevation picks up the latest Discord team membership.
    """
    redis = await cache_client.get_redis_client()
    session_key = f"api:session:{current_user.session_token}"
    session_data = await redis.get_json(session_key)

    if not session_data or not session_data.get("is_maintainer"):
        err_msg = "Maintainer mode required"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)

    async for key in redis._client.scan_iter("api:session:*"):
        if key == session_key:
            continue
        data = await redis.get_json(key)
        if data and data.get("is_maintainer"):
            await redis.delete(key)
            logger.info("Revoked elevated session %s", key)

    await redis.delete(cache_keys.CacheKeys.app_info())
    logger.info("Flushed app_info cache; refresh initiated by %s", current_user.session_token)

    return {"status": "ok"}
