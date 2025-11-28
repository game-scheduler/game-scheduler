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

# Base PostgreSQL URL without driver specification
BASE_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/game_scheduler"
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
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
