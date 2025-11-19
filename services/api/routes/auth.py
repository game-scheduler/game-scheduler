# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Authentication routes for Discord OAuth2 flow.

Handles login, callback, refresh, logout, and user info endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import oauth2, tokens
from services.api.config import get_api_config
from services.api.dependencies import auth as auth_deps
from shared.database import get_db
from shared.models import user as user_model
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ruff: noqa: B008


@router.get("/login")
async def login(redirect_uri: str = Query(...)) -> auth_schemas.LoginResponse:
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
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login") from e


@router.get("/callback", response_model=None)
async def callback(
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
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
        raise HTTPException(status_code=400, detail="Invalid or expired state") from e

    try:
        token_data = await oauth2.exchange_code_for_tokens(code, redirect_uri)
        user_data = await oauth2.get_user_from_token(token_data["access_token"])
    except Exception as e:
        logger.error(f"OAuth2 callback failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed") from e

    discord_id = user_data["id"]

    from sqlalchemy import select

    result = await db.execute(
        select(user_model.User).where(user_model.User.discord_id == discord_id)
    )
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        new_user = user_model.User(discord_id=discord_id)
        db.add(new_user)
        await db.commit()
        logger.info(f"Created new user with Discord ID: {discord_id}")

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
    token_data = await tokens.get_user_tokens(current_user.discord_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    try:
        new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
        await tokens.refresh_user_tokens(
            current_user.discord_id,
            new_tokens["access_token"],
            new_tokens["refresh_token"],
            new_tokens["expires_in"],
        )
        return auth_schemas.TokenResponse(
            access_token=new_tokens["access_token"], expires_in=new_tokens["expires_in"]
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Failed to refresh token") from e


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
    await tokens.delete_user_tokens(current_user.session_token)
    response.delete_cookie(key="session_token", samesite="lax")
    return {"message": "Logged out successfully"}


@router.get("/user", response_model=auth_schemas.UserInfoResponse)
async def get_user_info(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> auth_schemas.UserInfoResponse:
    """
    Get current user information and guilds.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User info and guild list
    """
    token_data = await tokens.get_user_tokens(current_user.discord_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        try:
            new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
            await tokens.refresh_user_tokens(
                current_user.discord_id,
                new_tokens["access_token"],
                new_tokens["refresh_token"],
                new_tokens["expires_in"],
            )
            access_token = new_tokens["access_token"]
        except Exception as e:
            logger.error(f"Token refresh in get_user_info failed: {e}")
            raise HTTPException(status_code=401, detail="Session expired") from e
    else:
        access_token = token_data["access_token"]

    try:
        user_info = await oauth2.get_user_from_token(access_token)
        guilds = await oauth2.get_user_guilds(access_token)

        # Get database user record to get UUID
        from sqlalchemy import select

        from shared.models import user as user_model

        stmt = select(user_model.User).where(user_model.User.discord_id == current_user.discord_id)
        result = await db.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found in database")

        return auth_schemas.UserInfoResponse(
            id=user_info["id"],
            user_uuid=str(db_user.id),
            username=user_info["username"],
            avatar=user_info.get("avatar"),
            guilds=guilds,
        )
    except Exception as e:
        logger.error(f"Failed to fetch user info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user info") from e
