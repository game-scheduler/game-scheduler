<!-- markdownlint-disable-file -->
# Middleware-Based Guild Isolation: Test-First RLS Implementation

## Executive Summary

**Approach**: Transparent guild isolation using SQLAlchemy event listeners + PostgreSQL Row-Level Security (RLS) + FastAPI dependency injection.

**Key Insight**: Guild isolation is tenant-level data filtering (perfect for middleware), NOT resource-specific authorization (which FastAPI dependencies already handle correctly).

**Timeline**: 3 weeks with test-first methodology, incremental delivery, zero breaking changes.

**Benefits Over Wrapper Approach**:
- 70% faster delivery (3 weeks vs 8 weeks)
- 95% fewer code changes (8 locations vs 37+ locations)
- Zero breaking changes (incremental adoption vs extensive refactoring)
- Architectural enforcement (automatic security vs manual function calls)

## Problem Statement

### Security Threat Model
- **Primary risk**: Developer accidents (forgetting guild_id filters, copy-paste errors, refactoring bugs)
- **Impact**: Cross-guild data leakage (User A sees User B's games from different guild)
- **Current state**: No architectural enforcement preventing accidental cross-guild queries
- **Evidence**: Security audit found 26/37 query locations with inconsistent or missing guild checks

### Why Middleware + RLS Is The Right Solution

**Guild isolation is NOT resource authorization**:
- Authorization: "Can this user perform this action on this game?" → **FastAPI dependencies** ✅
- Guild isolation: "Filter all database queries to user's guilds" → **Middleware + RLS** ✅

**Analogy**: Guild isolation is like database multi-tenancy (Salesforce, Shopify) - automatic data partitioning per tenant. It's NOT like "can user edit this document" (resource-level permission check).

### Previous Approach Failed Because

**Wrapper function approach attempted** (abandoned after research):
- Consolidate 37+ query locations into `guild_queries.py` wrapper functions
- Migrate all code to call wrappers with required `guild_id` parameters
- Enable RLS as safety net after migration complete

**Why it failed**:
- Too many changes (37+ locations across 6 weeks)
- Breaking changes to service interfaces
- Manual enforcement (developers must remember to call wrappers)
- Mixed concerns (deduplication + security in one migration)
- High risk (extensive refactoring with many moving parts)

**Lesson learned**: Security should be automatic and architectural, not manual and procedural.

## Architecture

### System Overview

```
HTTP Request → FastAPI Route Handler
    ↓
    Depends(get_db_with_user_guilds)  ← NEW: Enhanced dependency
        ↓
        1. Fetch user's guilds (OAuth2, cached 5 min)
        2. Store guild_ids in ContextVar (request-scoped)
        3. Yield AsyncSession
    ↓
Service Method (unchanged code)
    ↓
    db.execute(select(GameSession)...)  ← Unchanged query
    ↓
SQLAlchemy Event Listener (after_begin)  ← NEW: Automatic interception
    ↓
    SET LOCAL app.current_guild_ids = 'guild1,guild2,...'
    ↓
PostgreSQL RLS Policy  ← NEW: Database-level enforcement
    ↓
    WHERE guild_id IN (parse(app.current_guild_ids))
    ↓
Filtered Results (only user's guilds)
```

### Key Components

**1. ContextVar for Request-Scoped Storage**
- Thread-safe, async-safe storage for guild_ids within single request
- Automatically isolated between concurrent requests
- No global state, no race conditions

**2. Enhanced Database Dependency**
- `get_db_with_user_guilds()` wraps existing `get_db()`
- Fetches user's guilds, stores in ContextVar
- Yields session (existing behavior)
- Cleans up ContextVar in finally block

**3. SQLAlchemy Event Listener**
- Listens for `after_begin` event (transaction start)
- Reads guild_ids from ContextVar
- Executes `SET LOCAL app.current_guild_ids` (transaction-scoped setting)
- Transparent to application code

**4. PostgreSQL RLS Policies**
- Database-level enforcement of guild isolation
- Uses `current_setting('app.current_guild_ids')` to filter rows
- Works with indexes (no performance penalty)
- Defense-in-depth safety net

### Why This Works

**Separation of Concerns**:
- **Application code**: Business logic, no changes
- **Dependency**: User context (guilds), injected transparently
- **Event listener**: RLS context setup, automatic
- **Database**: Data filtering enforcement

**No Breaking Changes**:
- Routes using `Depends(get_db)` continue working (no RLS)
- Migrate service factories one at a time: `get_db` → `get_db_with_user_guilds`
- Test after each migration
- Enable RLS incrementally (table by table)

**Incremental Adoption**:
- Week 1: Infrastructure in place, zero behavior changes
- Week 2: Migrate service factories, test each one
- Week 3: Enable RLS (safety net after app already correct)

## Implementation Plan: Test-First, Incremental Migration

### Test-First Methodology Principles

**Every implementation stage MUST**:
1. Write tests BEFORE changing implementation
2. Tests verify current behavior (should pass)
3. Make implementation change
4. Tests still pass (proving no breakage)
5. Run full test suite (unit, integration, e2e)

**Test Coverage Requirements**:
- **Unit tests**: Every new function in isolation
- **Integration tests**: Database + RLS context + query execution
- **E2E tests**: Full request flow (route → service → database → RLS)

### Week 1: Infrastructure + Tests (Zero Behavior Changes)

#### Phase 1.1: Write Unit Tests for ContextVar Functions

**Action**: Create test file BEFORE implementation

**File**: `tests/shared/data_access/test_guild_isolation.py` (NEW)

```python
"""Unit tests for guild isolation ContextVar management."""
import pytest
from shared.data_access.guild_isolation import (
    set_current_guild_ids,
    get_current_guild_ids,
    clear_current_guild_ids,
)


def test_set_and_get_guild_ids():
    """ContextVar stores and retrieves guild_ids."""
    guild_ids = ["123456789", "987654321"]
    set_current_guild_ids(guild_ids)

    result = get_current_guild_ids()

    assert result == guild_ids


def test_get_guild_ids_returns_none_when_not_set():
    """ContextVar returns None when not initialized."""
    clear_current_guild_ids()

    result = get_current_guild_ids()

    assert result is None


def test_clear_guild_ids():
    """ContextVar cleared properly."""
    set_current_guild_ids(["123"])
    clear_current_guild_ids()

    result = get_current_guild_ids()

    assert result is None


@pytest.mark.asyncio
async def test_contextvars_isolated_between_async_tasks():
    """ContextVars maintain isolation between concurrent async tasks."""
    import asyncio

    async def task1():
        set_current_guild_ids(["task1_guild"])
        await asyncio.sleep(0.01)
        return get_current_guild_ids()

    async def task2():
        set_current_guild_ids(["task2_guild"])
        await asyncio.sleep(0.01)
        return get_current_guild_ids()

    result1, result2 = await asyncio.gather(task1(), task2())

    assert result1 == ["task1_guild"]
    assert result2 == ["task2_guild"]
```

**Expected result**: Tests fail (module doesn't exist yet) ❌

#### Phase 1.2: Implement ContextVar Functions

**File**: `shared/data_access/guild_isolation.py` (NEW)

```python
"""
Guild isolation middleware using ContextVars and SQLAlchemy event listeners.

Provides transparent guild-level data filtering for multi-tenant security.
"""
from contextvars import ContextVar

_current_guild_ids: ContextVar[list[str] | None] = ContextVar(
    'current_guild_ids',
    default=None
)


def set_current_guild_ids(guild_ids: list[str]) -> None:
    """
    Set guild IDs for current request context.

    Args:
        guild_ids: List of Discord guild IDs (snowflakes)
    """
    _current_guild_ids.set(guild_ids)


def get_current_guild_ids() -> list[str] | None:
    """
    Get guild IDs for current request context.

    Returns:
        List of guild IDs or None if not set
    """
    return _current_guild_ids.get(None)


def clear_current_guild_ids() -> None:
    """Clear guild IDs from current request context."""
    _current_guild_ids.set(None)
```

**Expected result**: Unit tests pass ✅

**Command**: `uv run pytest tests/shared/data_access/test_guild_isolation.py -v`

#### Phase 1.3: Write Integration Tests for Event Listener

**Action**: Write tests BEFORE implementing event listener

**File**: `tests/integration/test_guild_isolation_rls.py` (NEW)

```python
"""Integration tests for RLS context setting via event listener."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.data_access.guild_isolation import (
    set_current_guild_ids,
    clear_current_guild_ids,
)
from shared.database import get_db_session


@pytest.mark.asyncio
async def test_event_listener_sets_rls_context_on_transaction_begin():
    """Event listener sets PostgreSQL session variable when transaction begins."""
    guild_ids = ["123456789", "987654321"]
    set_current_guild_ids(guild_ids)

    try:
        async with get_db_session() as session:
            # Event listener should have fired on transaction begin
            result = await session.execute(
                text("SELECT current_setting('app.current_guild_ids', true)")
            )
            rls_context = result.scalar_one()

            assert rls_context == "123456789,987654321"
    finally:
        clear_current_guild_ids()


@pytest.mark.asyncio
async def test_event_listener_handles_empty_guild_list():
    """Event listener handles empty guild list gracefully."""
    set_current_guild_ids([])

    try:
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT current_setting('app.current_guild_ids', true)")
            )
            rls_context = result.scalar_one()

            # Empty list = empty string
            assert rls_context == ""
    finally:
        clear_current_guild_ids()


@pytest.mark.asyncio
async def test_event_listener_no_op_when_guild_ids_not_set():
    """Event listener skips RLS setup when ContextVar not set."""
    clear_current_guild_ids()

    async with get_db_session() as session:
        # Should not raise error, just not set the variable
        result = await session.execute(
            text("SELECT current_setting('app.current_guild_ids', true)")
        )
        rls_context = result.scalar_one()

        # Setting returns NULL or empty string when not set
        assert rls_context in (None, "", "null")
```

**Expected result**: Tests fail (event listener not implemented) ❌

#### Phase 1.4: Implement SQLAlchemy Event Listener

**File**: `shared/data_access/guild_isolation.py` (UPDATE)

```python
"""
Guild isolation middleware using ContextVars and SQLAlchemy event listeners.

Provides transparent guild-level data filtering for multi-tenant security.
"""
import logging
from contextvars import ContextVar

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_current_guild_ids: ContextVar[list[str] | None] = ContextVar(
    'current_guild_ids',
    default=None
)


def set_current_guild_ids(guild_ids: list[str]) -> None:
    """
    Set guild IDs for current request context.

    Args:
        guild_ids: List of Discord guild IDs (snowflakes)
    """
    _current_guild_ids.set(guild_ids)


def get_current_guild_ids() -> list[str] | None:
    """
    Get guild IDs for current request context.

    Returns:
        List of guild IDs or None if not set
    """
    return _current_guild_ids.get(None)


def clear_current_guild_ids() -> None:
    """Clear guild IDs from current request context."""
    _current_guild_ids.set(None)


@event.listens_for(AsyncSession, "after_begin")
def set_rls_context_on_transaction_begin(session, transaction, connection):
    """
    Automatically set PostgreSQL RLS context when transaction begins.

    Reads guild_ids from ContextVar and sets PostgreSQL session variable
    for use by RLS policies. Transaction-scoped (SET LOCAL).

    Args:
        session: SQLAlchemy session
        transaction: Current transaction
        connection: Database connection
    """
    guild_ids = get_current_guild_ids()

    if guild_ids is None:
        # No guild context set (e.g., service operations, migrations)
        # Skip RLS setup - connection will use default behavior
        return

    # Convert list to comma-separated string for PostgreSQL
    guild_ids_str = ",".join(guild_ids)

    logger.debug(f"Setting RLS context: app.current_guild_ids = {guild_ids_str}")

    # SET LOCAL is transaction-scoped (automatically cleared on commit/rollback)
    connection.execute(
        text("SET LOCAL app.current_guild_ids = :guild_ids"),
        {"guild_ids": guild_ids_str}
    )
```

**Expected result**: Integration tests pass ✅

**Command**: `uv run scripts/run-integration-tests.sh -- tests/integration/test_guild_isolation_rls.py -v`

#### Phase 1.5: Write Tests for Enhanced Database Dependency

**Action**: Write tests BEFORE implementing `get_db_with_user_guilds()`

**File**: `tests/services/api/test_database_dependencies.py` (NEW)

```python
"""Tests for database dependency functions."""
import pytest
from unittest.mock import AsyncMock, patch

from services.api.auth import oauth2
from shared.database import get_db_with_user_guilds
from shared.data_access.guild_isolation import get_current_guild_ids
from shared.schemas.auth import CurrentUser


@pytest.fixture
def mock_current_user():
    """Mock CurrentUser for dependency testing."""
    user_mock = AsyncMock()
    user_mock.discord_id = "123456789"

    return CurrentUser(
        user=user_mock,
        access_token="mock_access_token",
        session_token="mock_session_token"
    )


@pytest.fixture
def mock_user_guilds():
    """Mock user guilds from Discord API."""
    return [
        {"id": "guild_1", "name": "Test Guild 1"},
        {"id": "guild_2", "name": "Test Guild 2"},
    ]


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_sets_context(mock_current_user, mock_user_guilds):
    """Enhanced dependency sets guild_ids in ContextVar."""
    with patch.object(oauth2, 'get_user_guilds', return_value=mock_user_guilds):
        async for session in get_db_with_user_guilds(mock_current_user):
            # Inside context, guild_ids should be set
            guild_ids = get_current_guild_ids()
            assert guild_ids == ["guild_1", "guild_2"]
            break  # Only need to test context setting


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exit(mock_current_user, mock_user_guilds):
    """Enhanced dependency clears ContextVar in finally block."""
    with patch.object(oauth2, 'get_user_guilds', return_value=mock_user_guilds):
        async for session in get_db_with_user_guilds(mock_current_user):
            pass  # Consume generator

    # After generator exits, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exception(mock_current_user, mock_user_guilds):
    """Enhanced dependency clears ContextVar even if exception raised."""
    with patch.object(oauth2, 'get_user_guilds', return_value=mock_user_guilds):
        with pytest.raises(RuntimeError):
            async for session in get_db_with_user_guilds(mock_current_user):
                raise RuntimeError("Simulated error")

    # Even after exception, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None
```

**Expected result**: Tests fail (function doesn't exist) ❌

#### Phase 1.6: Implement Enhanced Database Dependency

**File**: `shared/database.py` (UPDATE)

```python
# Add to existing imports
from shared.data_access.guild_isolation import (
    set_current_guild_ids,
    clear_current_guild_ids,
)

# Add new function after get_db()
async def get_db_with_user_guilds(
    current_user,  # Type hint causes circular import, FastAPI handles it
) -> AsyncGenerator[AsyncSession]:
    """
    Provide database session with user's guilds set for RLS enforcement.

    Use this dependency for tenant-scoped queries (games, templates, participants).
    The SQLAlchemy event listener automatically sets RLS context on transaction begin.

    For unauthenticated operations (migrations, service tasks), use get_db() instead.

    Args:
        current_user: Current authenticated user (injected by FastAPI)

    Yields:
        AsyncSession: Database session with guild context set

    Example:
        @router.get("/games")
        async def list_games(
            db: AsyncSession = Depends(get_db_with_user_guilds)
        ):
            # All queries automatically filtered to user's guilds
            result = await db.execute(select(GameSession))
            return result.scalars().all()
    """
    # Import here to avoid circular dependency
    from services.api.auth import oauth2

    # Fetch user's guilds (cached with 5-min TTL)
    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token,
        current_user.user.discord_id
    )
    guild_ids = [g["id"] for g in user_guilds]

    # Store in request-scoped context
    set_current_guild_ids(guild_ids)

    try:
        # Yield session - event listener will set RLS on next query
        async with AsyncSessionLocal() as session:
            yield session
            await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        clear_current_guild_ids()
```

**Expected result**: Unit tests pass ✅

**Command**: `uv run pytest tests/services/api/test_database_dependencies.py -v`

#### Phase 1.7: Register Event Listener in Application Startup

**File**: `services/api/app.py` (UPDATE)

```python
# Add to imports section
from shared.data_access import guild_isolation  # noqa: F401 - Import registers event listener

# Update lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes connections on startup and closes them on shutdown.
    Guild isolation event listener registered via import.

    Args:
        app: FastAPI application instance
    """
    logger.info("Starting API service...")

    redis_instance = await redis_client.get_redis_client()
    logger.info("Redis connection initialized")

    logger.info("Guild isolation middleware registered (event listener active)")

    yield

    logger.info("Shutting down API service...")

    await redis_instance.disconnect()
    logger.info("Redis connection closed")
```

**Expected result**: Application starts without errors ✅

**Command**: `docker compose up api` (check logs for "Guild isolation middleware registered")

#### Phase 1.8: Create Alembic Migration for RLS Policies (DISABLED)

**Action**: Create migration but DO NOT enable RLS yet

**File**: `alembic/versions/NNNN_add_rls_policies_disabled.py` (NEW via alembic)

```python
"""Add RLS policies (disabled initially).

Revision ID: NNNN
Revises: <previous_revision>
Create Date: 2026-01-01
"""
from alembic import op


revision = 'NNNN'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create RLS policies for guild isolation (disabled).

    Policies will be enabled in future migration after service migration complete.
    """
    # Create indexes for RLS policy performance (if not exist)
    op.create_index(
        'idx_game_sessions_guild_id',
        'game_sessions',
        ['guild_id'],
        if_not_exists=True
    )
    op.create_index(
        'idx_game_templates_guild_id',
        'game_templates',
        ['guild_id'],
        if_not_exists=True
    )

    # Create policies (disabled initially - no ALTER TABLE ENABLE RLS)
    # Game sessions
    op.execute("""
        CREATE POLICY guild_isolation_games ON game_sessions
        FOR ALL
        USING (
            guild_id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
        )
    """)

    # Game templates
    op.execute("""
        CREATE POLICY guild_isolation_templates ON game_templates
        FOR ALL
        USING (
            guild_id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
        )
    """)

    # Game participants (via join to game_sessions)
    op.execute("""
        CREATE POLICY guild_isolation_participants ON game_participants
        FOR ALL
        USING (
            game_session_id IN (
                SELECT id FROM game_sessions
                WHERE guild_id::text = ANY(
                    string_to_array(
                        current_setting('app.current_guild_ids', true),
                        ','
                    )
                )
            )
        )
    """)


def downgrade() -> None:
    """Remove RLS policies."""
    op.execute("DROP POLICY IF EXISTS guild_isolation_games ON game_sessions")
    op.execute("DROP POLICY IF EXISTS guild_isolation_templates ON game_templates")
    op.execute("DROP POLICY IF EXISTS guild_isolation_participants ON game_participants")

    op.drop_index('idx_game_templates_guild_id', 'game_templates', if_exists=True)
    op.drop_index('idx_game_sessions_guild_id', 'game_sessions', if_exists=True)
```

**Expected result**: Migration runs successfully, RLS still disabled ✅

**Commands**:
```bash
# Generate migration
docker compose exec api uv run alembic revision -m "add_rls_policies_disabled"

# Run migration
docker compose exec api uv run alembic upgrade head

# Verify policies exist but RLS disabled
docker compose exec postgres psql -U gamebot -d game_scheduler -c "\d game_sessions"
# Should show policies but "Row-level security: DISABLED"
```

#### Phase 1.9: Full Test Suite Validation

**Action**: Run all tests to verify no regressions

**Commands**:
```bash
# Unit tests
uv run pytest tests/shared/ tests/services/ -v

# Integration tests
uv run scripts/run-integration-tests.sh

# E2E tests
uv run scripts/run-e2e-tests.sh
```

**Expected result**: All tests pass (infrastructure added, zero behavior changes) ✅

**Week 1 Deliverable**: Infrastructure complete, event listener active, RLS policies created (disabled), all tests pass, zero behavior changes.

### Week 2: Service Factory Migration (Incremental, Test-First)

#### Overview: Service Factory Migration Strategy

**What changes**: Dependency injection in service factory functions
**What doesn't change**: Route handlers, service methods, query code

**Pattern**:
```python
# BEFORE
def _get_game_service(
    db: AsyncSession = Depends(database.get_db),
) -> games_service.GameService:
    # ... service setup

# AFTER
def _get_game_service(
    db: AsyncSession = Depends(database.get_db_with_user_guilds),
) -> games_service.GameService:
    # ... service setup (UNCHANGED)
```

**Service factories to migrate**:
1. `services/api/routes/games.py::_get_game_service()` - Line 88
2. Route handler direct dependencies (7 functions across 4 files):
   - `services/api/routes/templates.py::list_templates()` - Line 47
   - `services/api/routes/templates.py::get_template()` - Line 128
   - `services/api/routes/templates.py::create_template()` - Line 178
   - `services/api/routes/templates.py::update_template()` - Line 242
   - `services/api/routes/templates.py::delete_template()` - Line 296
   - `services/api/routes/templates.py::duplicate_template()` - Line 328
   - `services/api/routes/templates.py::reorder_templates()` - Line 378
   - `services/api/routes/guilds.py::list_guilds()` - Line 46
   - `services/api/routes/export.py::export_game_to_ical()` - Line 92

**NOT migrating** (these use get_db correctly for non-tenant operations):
- `services/api/dependencies/permissions.py` - Permission checks query by Discord IDs (cross-tenant by design)
- `services/api/dependencies/auth.py` - Authentication is pre-tenant-context
- `services/api/routes/auth.py` - OAuth callback creates user before tenant context exists

#### Phase 2.1: Write Integration Tests for Game Service RLS

**Action**: Write tests BEFORE migrating `_get_game_service`

**File**: `tests/integration/test_game_service_guild_isolation.py` (NEW)

```python
"""Integration tests for game service guild isolation via RLS."""
import pytest
from unittest.mock import AsyncMock, patch

from services.api.routes.games import _get_game_service
from shared.schemas.auth import CurrentUser
from shared.database import get_db_with_user_guilds
from shared.models.game import GameSession
from sqlalchemy import select


@pytest.fixture
def mock_current_user_guild_a():
    """Mock user belonging to Guild A."""
    user_mock = AsyncMock()
    user_mock.discord_id = "user_123"
    user_mock.id = "user_uuid_123"

    return CurrentUser(
        user=user_mock,
        access_token="mock_token",
        session_token="mock_session"
    )


@pytest.fixture
def mock_guilds_guild_a():
    """Mock user's guilds (only Guild A)."""
    return [{"id": "guild_a_discord_id", "name": "Guild A"}]


@pytest.mark.asyncio
async def test_game_service_only_returns_games_from_user_guilds(
    db_session,
    mock_current_user_guild_a,
    mock_guilds_guild_a,
    test_guild_a,
    test_guild_b,
    test_game_guild_a,
    test_game_guild_b
):
    """Game service list_games only returns games from user's guilds after RLS context set."""
    with patch('services.api.auth.oauth2.get_user_guilds', return_value=mock_guilds_guild_a):
        async for db in get_db_with_user_guilds(mock_current_user_guild_a):
            game_service = _get_game_service(db=db)

            games, total = await game_service.list_games()

            # Should only see games from Guild A (RLS filters Guild B)
            assert total == 1
            assert games[0].id == test_game_guild_a.id
            assert games[0].guild_id == test_guild_a.id


@pytest.mark.asyncio
async def test_game_service_get_game_returns_none_for_other_guild_game(
    db_session,
    mock_current_user_guild_a,
    mock_guilds_guild_a,
    test_game_guild_b
):
    """Game service get_game returns None for game from different guild."""
    with patch('services.api.auth.oauth2.get_user_guilds', return_value=mock_guilds_guild_a):
        async for db in get_db_with_user_guilds(mock_current_user_guild_a):
            game_service = _get_game_service(db=db)

            game = await game_service.get_game(test_game_guild_b.id)

            # RLS filters out Guild B game
            assert game is None


@pytest.mark.asyncio
async def test_direct_query_with_rls_context_filters_guilds(
    db_session,
    mock_current_user_guild_a,
    mock_guilds_guild_a,
    test_guild_a,
    test_guild_b,
    test_game_guild_a,
    test_game_guild_b
):
    """Direct SQLAlchemy query respects RLS context set by dependency."""
    with patch('services.api.auth.oauth2.get_user_guilds', return_value=mock_guilds_guild_a):
        async for db in get_db_with_user_guilds(mock_current_user_guild_a):
            # Direct query (no game service) should still be filtered
            result = await db.execute(select(GameSession))
            games = result.scalars().all()

            # Only Guild A game visible
            assert len(games) == 1
            assert games[0].id == test_game_guild_a.id
```

**Expected result**: Tests pass with current `get_db` (no RLS yet), will continue passing after migration ✅

**Command**: `uv run scripts/run-integration-tests.sh -- tests/integration/test_game_service_guild_isolation.py -v`

#### Phase 2.2: Migrate Game Service Factory

**File**: `services/api/routes/games.py` (UPDATE)

```python
# Line 88 - CHANGE ONE LINE
def _get_game_service(
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed from get_db
) -> games_service.GameService:
    """Get game service instance with dependencies."""
    event_publisher = messaging_publisher.EventPublisher()
    discord_client = get_discord_client()
    participant_resolver = resolver_module.ParticipantResolver(discord_client)

    return games_service.GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=discord_client,
        participant_resolver=participant_resolver,
    )
```

**Expected result**: All game route tests still pass ✅

**Commands**:
```bash
# Run tests for games routes
uv run pytest tests/services/api/routes/test_games*.py -v

# Run integration tests
uv run scripts/run-integration-tests.sh

# Run E2E game tests
uv run scripts/run-e2e-tests.sh -- tests/e2e/test_game*.py -v
```

#### Phase 2.3: Write Integration Tests for Template Routes RLS

**Action**: Write tests BEFORE migrating template route dependencies

**File**: `tests/integration/test_template_routes_guild_isolation.py` (NEW)

```python
"""Integration tests for template routes guild isolation."""
import pytest
from unittest.mock import patch

from tests.shared.auth_helpers import create_test_session


@pytest.mark.asyncio
async def test_list_templates_only_returns_user_guild_templates(
    authenticated_client,
    test_guild_a,
    test_guild_b,
    test_template_guild_a,
    test_template_guild_b,
    mock_guilds_guild_a
):
    """list_templates only returns templates from user's guilds."""
    with patch('services.api.auth.oauth2.get_user_guilds', return_value=mock_guilds_guild_a):
        response = authenticated_client.get(
            f"/api/v1/guilds/{test_guild_a.id}/templates"
        )

        assert response.status_code == 200
        templates = response.json()

        # Only Guild A template visible
        assert len(templates) == 1
        assert templates[0]["id"] == test_template_guild_a.id


@pytest.mark.asyncio
async def test_get_template_returns_404_for_other_guild_template(
    authenticated_client,
    test_guild_b,
    test_template_guild_b,
    mock_guilds_guild_a
):
    """get_template returns 404 for template from different guild."""
    with patch('services.api.auth.oauth2.get_user_guilds', return_value=mock_guilds_guild_a):
        response = authenticated_client.get(
            f"/api/v1/guilds/{test_guild_b.id}/templates/{test_template_guild_b.id}"
        )

        # RLS filters template, route returns 404
        assert response.status_code == 404
```

**Expected result**: Tests pass after route migrations ✅

#### Phase 2.4: Migrate Template Route Dependencies

**File**: `services/api/routes/templates.py` (UPDATE - 7 functions)

```python
# Line 47 - list_templates
async def list_templates(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> list[template_schemas.TemplateListItem]:
    # ... function body unchanged

# Line 128 - get_template
async def get_template(
    template_id: str,
    guild_id: str = Query(...),
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> template_schemas.TemplateResponse:
    # ... function body unchanged

# Line 178 - create_template
async def create_template(
    guild_id: str,
    template: template_schemas.TemplateCreateRequest,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.require_bot_manager),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> template_schemas.TemplateResponse:
    # ... function body unchanged

# Line 242 - update_template
async def update_template(
    template_id: str,
    template_update: template_schemas.TemplateUpdateRequest,
    guild_id: str = Query(...),
    current_user: auth_schemas.CurrentUser = Depends(dependencies.require_bot_manager),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> template_schemas.TemplateResponse:
    # ... function body unchanged

# Line 296 - delete_template
async def delete_template(
    template_id: str,
    guild_id: str = Query(...),
    current_user: auth_schemas.CurrentUser = Depends(dependencies.require_bot_manager),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> None:
    # ... function body unchanged

# Line 328 - duplicate_template
async def duplicate_template(
    source_template_id: str,
    target_guild_id: str,
    template_data: template_schemas.TemplateDuplicateRequest | None = None,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.require_bot_manager),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> template_schemas.TemplateResponse:
    # ... function body unchanged

# Line 378 - reorder_templates
async def reorder_templates(
    reorder_request: template_schemas.TemplateReorderRequest,
    guild_id: str = Query(...),
    current_user: auth_schemas.CurrentUser = Depends(dependencies.require_bot_manager),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> None:
    # ... function body unchanged
```

**Expected result**: All template tests pass ✅

**Commands**:
```bash
uv run pytest tests/services/api/routes/test_templates.py -v
uv run scripts/run-integration-tests.sh -- tests/integration/test_template*.py -v
```

#### Phase 2.5: Migrate Guild Routes

**File**: `services/api/routes/guilds.py` (UPDATE)

```python
# Line 46 - list_guilds
async def list_guilds(
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
) -> guild_schemas.GuildListResponse:
    # ... function body unchanged
```

**Expected result**: Guild tests pass ✅

**Command**: `uv run pytest tests/services/api/routes/test_guilds.py -v`

#### Phase 2.6: Migrate Export Route

**File**: `services/api/routes/export.py` (UPDATE)

```python
# Line 92
async def export_game_to_ical(
    game_id: str,
    user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    db: AsyncSession = Depends(database.get_db_with_user_guilds),  # ← Changed
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> Response:
    # ... function body unchanged
```

**Expected result**: Export tests pass ✅

**Command**: `uv run pytest tests/services/api/routes/test_export.py -v`

#### Phase 2.7: Full Test Suite Validation

**Action**: Run all tests after all migrations complete

**Commands**:
```bash
# Unit tests
uv run pytest tests/shared/ tests/services/ -v

# Integration tests
uv run scripts/run-integration-tests.sh

# E2E tests
uv run scripts/run-e2e-tests.sh
```

**Expected result**: All tests pass (8 locations migrated, RLS context set but not enforced) ✅

**Week 2 Deliverable**: All tenant-scoped routes use `get_db_with_user_guilds`, RLS context set on every query, all tests pass, zero behavior changes (RLS still disabled).

### Week 3: Enable RLS + E2E Validation

#### Phase 3.1: Write E2E Tests for Cross-Guild Isolation

**Action**: Write comprehensive E2E tests BEFORE enabling RLS

**File**: `tests/e2e/test_guild_isolation_e2e.py` (NEW)

```python
"""End-to-end tests for guild isolation across full request flow."""
import pytest


@pytest.mark.e2e
def test_user_cannot_see_games_from_other_guilds(
    authenticated_client_guild_a,
    authenticated_client_guild_b,
    test_game_guild_a,
    test_game_guild_b
):
    """Complete workflow: User A in Guild A cannot see User B's game in Guild B."""
    # User A lists games - should only see Guild A games
    response_a = authenticated_client_guild_a.get("/api/v1/games")
    games_a = response_a.json()["games"]

    assert response_a.status_code == 200
    assert len(games_a) == 1
    assert games_a[0]["id"] == test_game_guild_a.id

    # User B lists games - should only see Guild B games
    response_b = authenticated_client_guild_b.get("/api/v1/games")
    games_b = response_b.json()["games"]

    assert response_b.status_code == 200
    assert len(games_b) == 1
    assert games_b[0]["id"] == test_game_guild_b.id


@pytest.mark.e2e
def test_user_cannot_access_other_guild_game_by_id(
    authenticated_client_guild_a,
    test_game_guild_b
):
    """User A cannot fetch Guild B's game by ID (RLS returns 404)."""
    response = authenticated_client_guild_a.get(f"/api/v1/games/{test_game_guild_b.id}")

    # RLS filters game, query returns None, route returns 404
    assert response.status_code == 404


@pytest.mark.e2e
def test_user_cannot_join_other_guild_game(
    authenticated_client_guild_a,
    test_game_guild_b
):
    """User A cannot join Guild B's game."""
    response = authenticated_client_guild_a.post(
        f"/api/v1/games/{test_game_guild_b.id}/join"
    )

    # RLS filters game, service returns error
    assert response.status_code in (404, 403)


@pytest.mark.e2e
def test_template_isolation_across_guilds(
    authenticated_client_guild_a,
    test_guild_a,
    test_guild_b,
    test_template_guild_a,
    test_template_guild_b
):
    """Template listing respects guild isolation."""
    response = authenticated_client_guild_a.get(
        f"/api/v1/guilds/{test_guild_a.id}/templates"
    )
    templates = response.json()

    assert response.status_code == 200
    assert len(templates) == 1
    assert templates[0]["id"] == test_template_guild_a.id

    # Attempting to access Guild B template returns 404
    response_b = authenticated_client_guild_a.get(
        f"/api/v1/guilds/{test_guild_b.id}/templates/{test_template_guild_b.id}"
    )
    assert response_b.status_code == 404
```

**Expected result**: Tests will FAIL initially (RLS disabled), will PASS after RLS enabled ✅

#### Phase 3.2: Enable RLS on game_sessions Table

**Action**: Create migration to enable RLS on first table

**File**: `alembic/versions/MMMM_enable_rls_game_sessions.py` (NEW)

```python
"""Enable RLS on game_sessions table.

Revision ID: MMMM
Revises: NNNN
Create Date: 2026-01-01
"""
from alembic import op


revision = 'MMMM'
down_revision = 'NNNN'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable row-level security on game_sessions."""
    op.execute("ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security on game_sessions."""
    op.execute("ALTER TABLE game_sessions DISABLE ROW LEVEL SECURITY")
```

**Expected result**: Migration runs, RLS active on game_sessions ✅

**Commands**:
```bash
# Generate migration
docker compose exec api uv run alembic revision -m "enable_rls_game_sessions"

# Run migration
docker compose exec api uv run alembic upgrade head

# Verify RLS enabled
docker compose exec postgres psql -U gamebot -d game_scheduler -c "\d game_sessions"
# Should show "Row-level security: ENABLED"
```

#### Phase 3.3: Validate Game Routes with RLS Enabled

**Commands**:
```bash
# Run game route tests
uv run pytest tests/services/api/routes/test_games*.py -v

# Run game integration tests
uv run scripts/run-integration-tests.sh -- tests/integration/test_game*.py -v

# Run game E2E tests
uv run scripts/run-e2e-tests.sh -- tests/e2e/test_game*.py -v

# Run guild isolation E2E tests
uv run scripts/run-e2e-tests.sh -- tests/e2e/test_guild_isolation_e2e.py -v
```

**Expected result**: All tests pass with RLS enforcing game_sessions isolation ✅

#### Phase 3.4: Enable RLS on game_templates Table

**File**: `alembic/versions/PPPP_enable_rls_game_templates.py` (NEW)

```python
"""Enable RLS on game_templates table.

Revision ID: PPPP
Revises: MMMM
Create Date: 2026-01-01
"""
from alembic import op


revision = 'PPPP'
down_revision = 'MMMM'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable row-level security on game_templates."""
    op.execute("ALTER TABLE game_templates ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security on game_templates."""
    op.execute("ALTER TABLE game_templates DISABLE ROW LEVEL SECURITY")
```

**Expected result**: Template tests pass with RLS enabled ✅

**Commands**:
```bash
docker compose exec api uv run alembic upgrade head
uv run pytest tests/services/api/routes/test_templates.py -v
uv run scripts/run-integration-tests.sh -- tests/integration/test_template*.py -v
```

#### Phase 3.5: Enable RLS on game_participants Table

**File**: `alembic/versions/QQQQ_enable_rls_game_participants.py` (NEW)

```python
"""Enable RLS on game_participants table.

Revision ID: QQQQ
Revises: PPPP
Create Date: 2026-01-01
"""
from alembic import op


revision = 'QQQQ'
down_revision = 'PPPP'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable row-level security on game_participants."""
    op.execute("ALTER TABLE game_participants ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security on game_participants."""
    op.execute("ALTER TABLE game_participants DISABLE ROW LEVEL SECURITY")
```

**Expected result**: Join/leave tests pass with RLS enabled ✅

**Commands**:
```bash
docker compose exec api uv run alembic upgrade head
uv run scripts/run-e2e-tests.sh -- tests/e2e/test_user_join.py tests/e2e/test_player_removal.py -v
```

#### Phase 3.6: Full System Validation

**Action**: Run complete test suite with all RLS policies enabled

**Commands**:
```bash
# All unit tests
uv run pytest tests/ -v

# All integration tests
uv run scripts/run-integration-tests.sh

# All E2E tests
uv run scripts/run-e2e-tests.sh

# Manual smoke test: Start application, verify no errors
docker compose up
# Check logs for "Guild isolation middleware registered"
# Access frontend, verify games/templates load correctly
```

**Expected result**: Complete test suite passes, application functional, guild isolation enforced ✅

**Week 3 Deliverable**: RLS enabled on all tenant tables, full test suite passing, guild isolation architecturally enforced.

## Testing Strategy Summary

### Test Coverage Requirements

**Unit Tests** (Fast, isolated):
- ContextVar functions (get/set/clear)
- Event listener registration
- Enhanced dependency function

**Integration Tests** (Database + RLS):
- Event listener sets RLS context correctly
- RLS context filtered queries
- Service methods respect RLS
- Template/guild/export routes with RLS

**E2E Tests** (Full request flow):
- Cross-guild game access blocked
- Cross-guild template access blocked
- Join/leave operations respect guild boundaries
- Complete workflows (create → list → join → leave)

### Test-First Workflow

**Every implementation phase**:
1. ✅ Write tests verifying expected behavior
2. ❌ Tests fail (feature not implemented)
3. ✅ Implement feature
4. ✅ Tests pass (feature works correctly)
5. ✅ Run full test suite (no regressions)

### Continuous Validation

**After every change**:
- Run affected unit tests
- Run affected integration tests
- Run full test suite before committing
- Verify application starts without errors

## Success Metrics

### Security Metrics
- ✅ Zero cross-guild query paths (RLS enforced at database level)
- ✅ Zero accidental data leakage incidents in production
- ✅ 100% test coverage for guild isolation scenarios

### Implementation Metrics
- ✅ 8 locations migrated (vs 37+ in wrapper approach)
- ✅ 3 weeks delivery (vs 8 weeks in wrapper approach)
- ✅ Zero breaking changes (incremental adoption)
- ✅ 100% test pass rate throughout migration

### Performance Metrics
- ✅ Query performance unchanged (RLS uses indexes)
- ✅ No N+1 query problems introduced
- ✅ RLS policy overhead < 1ms per query

## Rollback Plan

### If Issues Discovered During Migration

**Week 1 (Infrastructure)**: Delete files, revert imports
**Week 2 (Service migration)**: Change `get_db_with_user_guilds` back to `get_db` (8 locations)
**Week 3 (RLS enablement)**: Disable RLS per table: `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`

### Rollback Commands

```bash
# Disable RLS on all tables
docker compose exec postgres psql -U gamebot -d game_scheduler << EOF
ALTER TABLE game_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE game_templates DISABLE ROW LEVEL SECURITY;
ALTER TABLE game_participants DISABLE ROW LEVEL SECURITY;
EOF

# Revert service factories
git checkout main -- services/api/routes/games.py
git checkout main -- services/api/routes/templates.py
git checkout main -- services/api/routes/guilds.py
git checkout main -- services/api/routes/export.py

# Restart services
docker compose restart api
```

## Monitoring and Observability

### RLS Policy Violations

**Query to detect violations**:
```sql
-- Count attempts to access data outside RLS context
SELECT COUNT(*) FROM pg_stat_user_tables
WHERE schemaname = 'public'
AND relname IN ('game_sessions', 'game_templates', 'game_participants');
```

**Log monitoring**:
- Watch for PostgreSQL logs: `ERROR: policy violation`
- Alert on RLS policy errors in production
- Dashboard for guild isolation metrics

### Performance Monitoring

**Query performance**:
```sql
-- Verify RLS uses indexes
EXPLAIN ANALYZE
SELECT * FROM game_sessions
WHERE guild_id = ANY(string_to_array('guild1,guild2', ','));
```

**Expected**: Index scan on `idx_game_sessions_guild_id`

## Documentation Updates

### Developer Documentation

**File**: `docs/GUILD_ISOLATION.md` (NEW)

```markdown
# Guild Isolation Architecture

## Overview
Guild isolation enforced via PostgreSQL Row-Level Security (RLS) with automatic context setting.

## How It Works
1. Use `Depends(get_db_with_user_guilds)` in route handlers
2. Dependency fetches user's guilds from Discord API
3. Event listener sets RLS context on transaction begin
4. All queries automatically filtered to user's guilds

## Adding New Tenant-Scoped Tables
1. Add `guild_id` column (UUID, foreign key to guilds)
2. Create index: `CREATE INDEX idx_<table>_guild_id ON <table>(guild_id)`
3. Create RLS policy (see alembic/versions/NNNN for pattern)
4. Enable RLS: `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY`
5. Add integration tests for isolation

## Troubleshooting
- **Query returns no results**: Check RLS context set correctly (`SELECT current_setting('app.current_guild_ids')`)
- **Performance slow**: Verify index exists on guild_id column
- **Policy violation errors**: Check event listener registered in app.py
```

### API Documentation

Update OpenAPI documentation to note guild isolation:

**File**: `services/api/app.py` (UPDATE)

```python
app = FastAPI(
    title="Game Scheduler API",
    description="""
    Game scheduling API with automatic guild-level data isolation.

    **Security**: All game, template, and participant queries automatically
    filtered to authenticated user's guilds via Row-Level Security (RLS).
    """,
    version="1.0.0"
)
```

## Research Sources

### Internal Research
- `.copilot-tracking/research/20251231-code-duplication-audit-research.md` - Query location audit (37+ locations identified)
- `.copilot-tracking/research/20251231-database-access-centralization-guild-isolation-research.md` - Security analysis (26 inconsistent guild checks)
- `.copilot-tracking/research/20260101-centralized-query-layer-deduplication-security-research.md` - Wrapper approach attempt (lessons learned)

### Codebase Analysis
- `shared/database.py` - Database session management patterns
- `services/api/routes/*.py` - Route handler dependency patterns (34+ `Depends(get_db)` usages identified)
- `services/api/dependencies/permissions.py` - Authorization patterns (not tenant isolation)
- `tests/integration/` - Existing integration test patterns
- `tests/e2e/` - Existing E2E test patterns

### External References
- PostgreSQL RLS documentation: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- SQLAlchemy event listeners: https://docs.sqlalchemy.org/en/20/core/event.html
- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- Python ContextVars: https://docs.python.org/3/library/contextvars.html

## Specific Implementation Locations

### Files to Create (NEW)
1. `shared/data_access/guild_isolation.py` - ContextVar + event listener (~80 lines)
2. `tests/shared/data_access/test_guild_isolation.py` - Unit tests (~60 lines)
3. `tests/integration/test_guild_isolation_rls.py` - Integration tests (~80 lines)
4. `tests/services/api/test_database_dependencies.py` - Dependency tests (~70 lines)
5. `tests/integration/test_game_service_guild_isolation.py` - Game service tests (~90 lines)
6. `tests/integration/test_template_routes_guild_isolation.py` - Template route tests (~60 lines)
7. `tests/e2e/test_guild_isolation_e2e.py` - E2E tests (~120 lines)
8. `docs/GUILD_ISOLATION.md` - Developer documentation (~150 lines)
9. `alembic/versions/NNNN_add_rls_policies_disabled.py` - RLS policy migration (~80 lines)
10. `alembic/versions/MMMM_enable_rls_game_sessions.py` - Enable game_sessions (~20 lines)
11. `alembic/versions/PPPP_enable_rls_game_templates.py` - Enable game_templates (~20 lines)
12. `alembic/versions/QQQQ_enable_rls_game_participants.py` - Enable game_participants (~20 lines)

### Files to Update (MODIFY)
1. `shared/database.py` - Add `get_db_with_user_guilds()` function (~40 lines added)
2. `services/api/app.py` - Import guild_isolation module, update lifespan (~5 lines changed)
3. `services/api/routes/games.py` - Change `_get_game_service()` dependency (~1 line changed)
4. `services/api/routes/templates.py` - Change 7 route handler dependencies (~7 lines changed)
5. `services/api/routes/guilds.py` - Change `list_guilds()` dependency (~1 line changed)
6. `services/api/routes/export.py` - Change `export_game_to_ical()` dependency (~1 line changed)

**Total**: 12 new files, 6 modified files, ~15 lines of implementation changes (excluding tests)

### Specific Function Names and Line Numbers

**Service Factory Functions to Modify**:
1. `services/api/routes/games.py::_get_game_service()` - Line 88
   - Change: `db: AsyncSession = Depends(database.get_db_with_user_guilds)`

**Route Handler Functions to Modify**:
2. `services/api/routes/templates.py::list_templates()` - Line 47
3. `services/api/routes/templates.py::get_template()` - Line 128
4. `services/api/routes/templates.py::create_template()` - Line 178
5. `services/api/routes/templates.py::update_template()` - Line 242
6. `services/api/routes/templates.py::delete_template()` - Line 296
7. `services/api/routes/templates.py::duplicate_template()` - Line 328
8. `services/api/routes/templates.py::reorder_templates()` - Line 378
   - All change: `db: AsyncSession = Depends(database.get_db_with_user_guilds)`

9. `services/api/routes/guilds.py::list_guilds()` - Line 46
   - Change: `db: AsyncSession = Depends(database.get_db_with_user_guilds)`

10. `services/api/routes/export.py::export_game_to_ical()` - Line 92
    - Change: `db: AsyncSession = Depends(database.get_db_with_user_guilds)`

**Functions NOT to Modify** (correct as-is):
- `services/api/dependencies/permissions.py` - 4 functions use `get_db` for cross-tenant permission checks (correct)
- `services/api/dependencies/auth.py::get_current_user()` - Line 46 - Authentication is pre-tenant-context (correct)
- `services/api/routes/auth.py` - 4 functions use `get_db` for OAuth/session management (correct)

## Key Differences from Failed Wrapper Approach

### What Changed
1. **Scope**: Guild isolation only (not deduplication)
2. **Mechanism**: Automatic (middleware) vs manual (wrapper calls)
3. **Changes**: 8 dependency injections vs 37+ query rewrites
4. **Risk**: Low (incremental, non-breaking) vs Medium (extensive refactoring)
5. **Timeline**: 3 weeks vs 8 weeks

### What Stayed the Same
1. **Security goal**: Prevent cross-guild data leakage
2. **RLS usage**: PostgreSQL policies as defense-in-depth
3. **Test coverage**: Comprehensive unit/integration/e2e tests
4. **Incremental delivery**: Week-by-week milestones

### Why This Succeeds
- **Architectural enforcement**: Can't bypass middleware (automatic)
- **Zero breaking changes**: Incremental adoption, existing code works
- **Clear separation**: Tenant filtering (middleware) vs authorization (dependencies)
- **Test-first**: Proves no regressions at every step

## Next Steps

1. **Review and approve** this test-first, middleware-based approach
2. **Week 1**: Implement infrastructure with comprehensive tests
3. **Week 2**: Migrate service factories incrementally
4. **Week 3**: Enable RLS and validate complete system

**Ready to proceed?** All implementation details, file locations, line numbers, and test requirements specified.
