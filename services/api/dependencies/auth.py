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


"""Authentication dependencies for FastAPI routes.

Provides dependency injection for current user retrieval.
"""

import logging

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette import status

from services.api.auth import tokens
from shared import database
from shared.models import user as user_model
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

# Module-level singleton for database dependency
_db_dependency = Depends(database.get_db)


async def get_current_user(
    session_token: str | None = Cookie(
        default=None, description="Session token from HTTPOnly cookie"
    ),
    db: AsyncSession = _db_dependency,
) -> auth_schemas.CurrentUser:
    """
    Get current authenticated user from cookie.

    Args:
        session_token: Session token from cookie
        db: Database session

    Returns:
        Current user information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_data = await tokens.get_user_tokens(session_token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    # Get user from database by Discord ID
    discord_id = token_data["user_id"]
    result = await db.execute(
        select(user_model.User).where(user_model.User.discord_id == discord_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return auth_schemas.CurrentUser(
        user=user,
        access_token=token_data["access_token"],
        session_token=session_token,
    )
