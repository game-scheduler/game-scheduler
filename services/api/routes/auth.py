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


"""Authentication routes for Discord OAuth2 flow.

Handles login, callback, refresh, logout, and user info endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from services.api.auth import oauth2, tokens
from services.api.config import get_api_config
from services.api.dependencies import auth as auth_deps
from shared.database import get_db
from shared.models import user as user_model
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/login")
async def login(
    redirect_uri: Annotated[str, Query(...)],
) -> auth_schemas.LoginResponse:
    """
    Initiate Discord OAuth2 login flow.

    Args:
        redirect_uri: URL to redirect to after authorization

    Returns:
        Authorization URL and state token
    """
    try:
        auth_url, state = await oauth2.generate_authorization_url(redirect_uri)
        return auth_schemas.LoginResponse(authorization_url=auth_url, state=state)
    except Exception as e:
        logger.error("Login initiation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login",
        ) from e


@router.get("/callback", response_model=None)
async def callback(
    response: Response,
    code: Annotated[str, Query(...)],
    state: Annotated[str, Query(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool | str]:
    """
    Handle Discord OAuth2 callback.

    Args:
        response: Response object for setting cookies
        code: Authorization code from Discord
        state: State token for CSRF protection
        db: Database session

    Returns:
        JSON response with success status for AJAX calls,
        or redirect to frontend for direct browser navigation
    """
    try:
        redirect_uri = await oauth2.validate_state(state)
    except oauth2.OAuth2StateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        ) from e

    try:
        token_data = await oauth2.exchange_code_for_tokens(code, redirect_uri)
        user_data = await oauth2.get_user_from_token(token_data["access_token"])
    except Exception as e:
        logger.error("OAuth2 callback failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e

    discord_id = user_data["id"]

    result = await db.execute(
        select(user_model.User).where(user_model.User.discord_id == discord_id)
    )
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        new_user = user_model.User(discord_id=discord_id)
        db.add(new_user)
        logger.info("Created new user with Discord ID: %s", discord_id)

    session_token = await tokens.store_user_tokens(
        discord_id,
        token_data["access_token"],
        token_data["refresh_token"],
        token_data["expires_in"],
    )

    config = get_api_config()
    is_production = config.environment == "production"

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=86400,
        domain=config.cookie_domain,
    )

    # Return JSON for modern frontends (development mode with fetch)
    return {"success": True, "message": "Authentication successful"}


@router.post("/refresh")
async def refresh(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
) -> auth_schemas.TokenResponse:
    """
    Refresh expired access token.

    Args:
        current_user: Current authenticated user

    Returns:
        New access token and expiration
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No session found")

    try:
        new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
        await tokens.refresh_user_tokens(
            current_user.session_token,
            new_tokens["access_token"],
            new_tokens["expires_in"],
        )
        return auth_schemas.TokenResponse(
            access_token=new_tokens["access_token"], expires_in=new_tokens["expires_in"]
        )
    except Exception as e:
        logger.error("Token refresh failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token"
        ) from e


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
) -> dict[str, str]:
    """
    Logout user and clear session.

    Args:
        response: Response object for clearing cookies
        current_user: Current authenticated user

    Returns:
        Success message
    """
    config = get_api_config()
    await tokens.delete_user_tokens(current_user.session_token)
    response.delete_cookie(key="session_token", samesite="lax", domain=config.cookie_domain)
    return {"message": "Logged out successfully"}


@router.get("/user", response_model=auth_schemas.UserInfoResponse)
async def get_user_info(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    _db: Annotated[AsyncSession, Depends(get_db)],
) -> auth_schemas.UserInfoResponse:
    """
    Get current user information and guilds.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User info and guild list
    """
    token_data = await tokens.get_user_tokens(current_user.session_token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No session found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        try:
            new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
            await tokens.refresh_user_tokens(
                current_user.session_token,
                new_tokens["access_token"],
                new_tokens["expires_in"],
            )
            access_token = new_tokens["access_token"]
        except Exception as e:
            logger.error("Token refresh in get_user_info failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
            ) from e
    else:
        access_token = token_data["access_token"]

    try:
        user_info = await oauth2.get_user_from_token(access_token)
        guilds = await oauth2.get_user_guilds(access_token, current_user.user.discord_id)

        return auth_schemas.UserInfoResponse(
            id=user_info["id"],
            user_uuid=str(current_user.user.id),
            username=user_info["username"],
            avatar=user_info.get("avatar"),
            guilds=guilds,
        )
    except Exception as e:
        logger.error("Failed to fetch user info: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user info",
        ) from e
