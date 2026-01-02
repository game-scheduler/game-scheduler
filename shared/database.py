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


"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator
from contextlib import contextmanager

from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
    set_current_guild_ids,
)
from shared.schemas.auth import CurrentUser

# Base PostgreSQL URL without driver specification
_raw_database_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/game_scheduler"
)

# Strip any driver specification to get base URL
BASE_DATABASE_URL = _raw_database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql+psycopg2://", "postgresql://"
)

# Build driver-specific URLs by adding driver to base URL
ASYNC_DATABASE_URL = BASE_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
SYNC_DATABASE_URL = BASE_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

# For backward compatibility - services importing DATABASE_URL get async version
DATABASE_URL = ASYNC_DATABASE_URL

# Async engine for API and Bot services
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

# Sync engine for Scheduler service
sync_engine = create_sync_engine(SYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Provide database session for FastAPI dependency injection.

    Use this with FastAPI's Depends() for automatic session lifecycle management.
    FastAPI will handle the async generator properly.

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_with_user_guilds(
    current_user: CurrentUser,
) -> AsyncGenerator[AsyncSession]:
    """
    Provide database session with user's guilds set for RLS enforcement.

    Use this dependency for tenant-scoped queries (games, templates, participants).
    The SQLAlchemy event listener automatically sets RLS context on transaction begin.

    For unauthenticated operations (migrations, service tasks), use get_db() instead.

    IMPORTANT: Routes must explicitly pass current_user dependency:
        @router.get("/games")
        async def list_games(
            current_user: CurrentUser = Depends(get_current_user),
            db: AsyncSession = Depends(get_db_with_user_guilds)
        ):

    Args:
        current_user: Current authenticated user (must be passed via Depends)

    Yields:
        AsyncSession: Database session with guild context set
    """
    from services.api.auth import oauth2

    # Fetch user's guilds (cached with 5-min TTL)
    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    guild_ids = [g["id"] for g in user_guilds]

    # Store in request-scoped context
    set_current_guild_ids(guild_ids)

    # Yield session - event listener will set RLS on next query
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            clear_current_guild_ids()


def get_db_session() -> AsyncSession:
    """
    Get database session for use as async context manager.

    Use this pattern in Discord bot commands and other non-FastAPI code
    where you need to manage the session lifecycle explicitly.

    DO NOT use this with FastAPI Depends() - use get_db() instead.

    Example:
        async with get_db_session() as db:
            result = await db.execute(select(Item))
            await db.commit()

    Returns:
        AsyncSession that must be used with 'async with' statement
    """
    return AsyncSessionLocal()


@contextmanager
def get_sync_db_session():
    """
    Get synchronous database session for use as context manager.

    Use this pattern in Celery tasks and other synchronous code
    where async operations provide no benefit.

    Example:
        with get_sync_db_session() as db:
            result = db.execute(select(Item))
            db.commit()

    Yields:
        Session: Synchronous SQLAlchemy session
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
