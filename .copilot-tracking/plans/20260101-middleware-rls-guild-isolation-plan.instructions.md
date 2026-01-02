---
applyTo: ".copilot-tracking/changes/20260101-middleware-rls-guild-isolation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Middleware-Based Guild Isolation with RLS

## Overview

Implement transparent guild isolation using SQLAlchemy event listeners, PostgreSQL Row-Level Security (RLS), and FastAPI dependency injection to provide automatic database-level tenant filtering with zero breaking changes.

## Objectives

- Implement architectural enforcement of guild isolation preventing accidental cross-guild data leakage
- Enable incremental adoption with zero breaking changes to existing code
- Provide defense-in-depth security at the database layer
- Deliver in 3.5 weeks with test-first methodology and continuous validation

## Research Summary

### Project Files

- [shared/database.py](shared/database.py) - Database session management and dependency injection
- [services/api/routes/games.py](services/api/routes/games.py) - Game service factory requiring migration
- [services/api/routes/templates.py](services/api/routes/templates.py) - Template route handlers requiring migration
- [services/api/routes/guilds.py](services/api/routes/guilds.py) - Guild route handler requiring migration
- [services/api/routes/export.py](services/api/routes/export.py) - Export route handler requiring migration
- [services/api/app.py](services/api/app.py) - Application startup for event listener registration

### External References

- #file:../research/20260101-middleware-rls-guild-isolation-research.md - Complete architecture and implementation research
- #fetch:https://docs.sqlalchemy.org/en/20/orm/session_events.html - SQLAlchemy event listener patterns
- #fetch:https://www.postgresql.org/docs/current/ddl-rowsecurity.html - PostgreSQL RLS documentation

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices
- #file:../../.github/instructions/integration-tests.instructions.md - Integration test patterns

## Implementation Checklist

### [x] Phase 0: Database User Configuration (Prerequisites)

- [x] Task 0.1: Create two-user database architecture
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 21-65)

- [x] Task 0.2: Update environment variables for both users
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 67-83)

- [x] Task 0.3: Verify RLS enforcement with non-superuser
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 85-106)

### [ ] Phase 1: Infrastructure + Tests (Week 1)

**NOTE**: Two test files from previous attempt exist but provide **incomplete coverage**:
- `tests/integration/test_games_route_guild_isolation.py` - Tests current behavior WITHOUT RLS (needs adaptation)
- `tests/e2e/test_game_authorization.py` - Tests authorization, not guild isolation (needs extension)

These files will be useful reference but do NOT cover Phase 1 infrastructure tasks (ContextVars, event listeners, enhanced dependency).

- [x] Task 1.1: Write unit tests for ContextVar functions
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 108-124)
  - **Status**: No existing coverage - must create new test file

- [x] Task 1.2: Implement ContextVar functions
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 126-142)

- [x] Task 1.3: Write integration tests for event listener
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 144-159)
  - **Status**: No existing coverage - must create new test file

- [x] Task 1.4: Implement SQLAlchemy event listener
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 161-179)

- [x] Task 1.5: Write tests for enhanced database dependency
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 181-198)
  - **Status**: No existing coverage - must create new test file

- [x] Task 1.6: Implement enhanced database dependency
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 200-217)

- [x] Task 1.7: Register event listener in application startup
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 219-229)

- [x] Task 1.8: Create Alembic migration for RLS policies (disabled)
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 231-249)

- [x] Task 1.9: Full test suite validation (Phase 1)
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 251-264)

### [ ] Phase 2: Service Factory Migration (Week 2)

**NOTE**: `tests/integration/test_games_route_guild_isolation.py` provides useful game service test patterns but tests **current behavior without RLS**. These tests will need adaptation/extension for Task 2.1.

- [x] Task 2.1: Write integration tests for game service RLS
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 266-283)
  - **Status**: Completed - 10 comprehensive tests created with 7 passing, 3 xfail for RLS-enabled scenarios

- [x] Task 2.2: Migrate game service factory
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 285-300)
  - **Status**: Completed - Changed to async function that fetches guilds and sets context

- [x] Task 2.3: Write integration tests for template routes RLS
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 302-317)

- [x] Task 2.4: Migrate template route dependencies (7 functions)
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 319-338)

- [x] Task 2.5: Migrate guild routes dependency
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 340-351)

- [ ] Task 2.6: Migrate export route dependency
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 353-364)

- [ ] Task 2.7: Full test suite validation (Phase 2)
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 366-379)

### [ ] Phase 3: Enable RLS + E2E Validation (Week 3)

**NOTE**: `tests/e2e/test_game_authorization.py` provides E2E test infrastructure but focuses on **authorization**, not **guild isolation**. Useful as template for Task 3.1 but needs extension.

- [ ] Task 3.1: Write E2E tests for cross-guild isolation
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 381-398)
  - **Status**: Partial infrastructure in `test_game_authorization.py` - needs guild isolation tests

- [ ] Task 3.2: Enable RLS on game_sessions table
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 400-418)

- [ ] Task 3.3: Run E2E tests and validate game isolation
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 420-433)

- [ ] Task 3.4: Enable RLS on game_templates table
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 435-453)

- [ ] Task 3.5: Run E2E tests and validate template isolation
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 455-468)

- [ ] Task 3.6: Enable RLS on participants table
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 470-488)

- [ ] Task 3.7: Full test suite validation (Phase 3)
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 490-505)

- [ ] Task 3.8: Production readiness verification
  - Details: [.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md](../.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md) (Lines 507-524)

## Dependencies

- PostgreSQL 15+ (RLS support)
- SQLAlchemy 2.0+ (async event listeners)
- FastAPI dependency injection
- Non-superuser database role (gamebot_app) for RLS enforcement
- Existing authentication system (CurrentUser, OAuth)

## Success Criteria

- All unit tests pass (ContextVar functions, database dependency)
- All integration tests pass (event listener, RLS context setting, query filtering)
- All E2E tests pass (complete request flow with guild isolation)
- Zero breaking changes to existing route handlers or service methods
- RLS policies active on all tenant-scoped tables (game_sessions, game_templates, participants)
- Database-level defense against accidental cross-guild queries
- Production deployment successful with validated guild isolation
