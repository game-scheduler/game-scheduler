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


"""Database connection and session management."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.data_access.guild_isolation import clear_current_guild_ids
from shared.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

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

# Bot database URL with BYPASSRLS privilege (defaults to same as DATABASE_URL if not set)
_raw_bot_database_url = os.getenv("BOT_DATABASE_URL", _raw_database_url)
_bot_base_url = _raw_bot_database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql+psycopg2://", "postgresql://"
)
BOT_DATABASE_URL = _bot_base_url.replace("postgresql://", "postgresql+asyncpg://")

# For backward compatibility - services importing DATABASE_URL get async version
DATABASE_URL = ASYNC_DATABASE_URL

# Async engine for API and Bot services
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

# Async engine for bot operations that need BYPASSRLS (SSE bridge, daemons)
bot_engine = create_async_engine(BOT_DATABASE_URL, echo=False, pool_pre_ping=True)

# Sync engine for Scheduler service
sync_engine = create_sync_engine(SYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

BotAsyncSessionLocal = async_sessionmaker(
    bot_engine,
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


def get_db_with_user_guilds() -> Any:  # noqa: ANN401
    """
    Factory function that returns a database dependency with user guild context.

    This should be called as: db: AsyncSession = Depends(get_db_with_user_guilds())

    The returned dependency function will automatically receive current_user from
    the route's dependency chain.
    """
    from services.api.dependencies import (  # noqa: PLC0415 - avoid circular dependency
        auth,
    )

    async def _get_db_with_guilds(
        current_user: CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    ) -> AsyncGenerator[AsyncSession]:
        """Inner dependency that receives current_user and provides DB session."""
        from services.api.auth import (  # noqa: PLC0415 - avoid circular dependency
            tokens,
        )
        from services.api.database import queries  # noqa: PLC0415
        from shared.cache import client as cache_client  # noqa: PLC0415
        from shared.cache import projection as member_projection  # noqa: PLC0415

        token_data = await tokens.get_user_tokens(current_user.session_token)
        if not token_data:
            raise HTTPException(status_code=401, detail="No session found")

        redis = await cache_client.get_redis_client()
        discord_guild_ids = (
            await member_projection.get_user_guilds(current_user.user.discord_id, redis=redis) or []
        )

        # Set up RLS context and convert Discord IDs to database UUIDs
        async with AsyncSessionLocal() as temp_session:
            await queries.setup_rls_and_convert_guild_ids(temp_session, discord_guild_ids)

        # Yield session - event listener will automatically set RLS on transaction begin
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

    return _get_db_with_guilds


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


def get_bypass_db_session() -> AsyncSession:
    """
    Get database session with BYPASSRLS privilege for system operations.

    Use this for operations that need to bypass RLS policies, such as:
    - SSE bridge looking up guild configurations
    - Background daemons operating across all guilds
    - System-level operations not tied to a specific user context

    The bypass user (gamebot_bot) has BYPASSRLS privilege but is not a superuser.

    Example:
        async with get_bypass_db_session() as db:
            guild = await db.execute(
                select(GuildConfiguration).where(GuildConfiguration.id == guild_uuid)
            )
            await db.commit()

    Returns:
        AsyncSession that must be used with 'async with' statement
    """
    return BotAsyncSessionLocal()


@contextmanager
def get_sync_db_session() -> Generator[Session]:
    """
    Get synchronous database session for use as context manager.

    Use this pattern in synchronous code where async operations
    provide no benefit.

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


# Event listeners for deferred event publishing


@event.listens_for(AsyncSession.sync_session_class, "after_commit")
def publish_deferred_events_after_commit(session: Session) -> None:
    """
    Publish deferred events after successful transaction commit.

    This ensures events are only sent to consumers after database
    changes are visible, preventing race conditions.

    Args:
        session: SQLAlchemy session that was committed
    """
    from shared.messaging import (  # noqa: PLC0415
        deferred_publisher,
        publisher,
    )

    deferred_events = deferred_publisher.DeferredEventPublisher.get_deferred_events(session)

    if not deferred_events:
        return

    logger.info("Publishing %d deferred events after commit", len(deferred_events))

    event_pub = publisher.EventPublisher()

    async def _publish_all() -> None:
        """Publish all deferred events asynchronously."""
        try:
            await event_pub.connect()

            for deferred_event in deferred_events:
                event = deferred_event["event"]
                routing_key = deferred_event["routing_key"]

                await event_pub.publish(event=event, routing_key=routing_key)

                logger.debug("Published deferred event: %s", event.event_type)

        except Exception:
            logger.exception("Failed to publish deferred events")
        finally:
            await event_pub.close()
            deferred_publisher.DeferredEventPublisher.clear_deferred_events(session)

    task = asyncio.create_task(_publish_all())
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)


@event.listens_for(AsyncSession.sync_session_class, "after_rollback")
def clear_deferred_events_after_rollback(session: Session) -> None:
    """
    Clear deferred events after transaction rollback.

    Events are discarded since the associated database changes
    were rolled back and should not be published.

    Args:
        session: SQLAlchemy session that was rolled back
    """
    from shared.messaging import deferred_publisher  # noqa: PLC0415

    deferred_events = deferred_publisher.DeferredEventPublisher.get_deferred_events(session)

    if deferred_events:
        logger.info("Discarding %d deferred events after rollback", len(deferred_events))
        deferred_publisher.DeferredEventPublisher.clear_deferred_events(session)
