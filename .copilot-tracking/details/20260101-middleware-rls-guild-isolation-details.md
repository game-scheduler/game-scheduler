<!-- markdownlint-disable-file -->

# Task Details: Middleware-Based Guild Isolation with RLS

## Research Reference

**Source Research**: #file:../research/20260101-middleware-rls-guild-isolation-research.md

## Phase 0: Database User Configuration (Prerequisites)

### Task 0.1: Create two-user database architecture

Create separate database users for migrations (superuser) and application runtime (non-superuser with RLS enforcement).

- **Files**:
  - `alembic/env.py` or init container scripts - Add user creation logic
  - Database initialization scripts - Create both users with correct privileges
- **Success**:
  - Two database users exist: `gamebot_admin` (superuser) and `gamebot_app` (non-superuser)
  - `gamebot_app` has SELECT, INSERT, UPDATE, DELETE permissions on all tables
  - `gamebot_app` has USAGE, SELECT on all sequences
  - Default privileges set for future tables
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 115-175) - Database user configuration requirements
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 98-113) - RLS validation test results showing superuser bypass
- **Dependencies**:
  - None (this is the first step)
- **SQL Pattern**:
  ```sql
  CREATE USER gamebot_admin WITH PASSWORD 'admin_password' SUPERUSER;
  CREATE USER gamebot_app WITH PASSWORD 'app_password' LOGIN;
  GRANT CONNECT ON DATABASE game_scheduler TO gamebot_app;
  GRANT USAGE ON SCHEMA public TO gamebot_app;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gamebot_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gamebot_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gamebot_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO gamebot_app;
  ```

### Task 0.2: Update environment variables for both users

Update all environment files to use separate credentials for migrations vs runtime.

- **Files**:
  - `config/env.dev` - Add admin and app user credentials
  - `config/env.int` - Add admin and app user credentials
  - `config/env.e2e` - Add admin and app user credentials
  - `config/env.staging` - Add admin and app user credentials
  - `config/env.prod` - Add admin and app user credentials
  - `alembic/env.py` - Update to use ADMIN_DATABASE_URL
  - Service configuration files - Update to use DATABASE_URL with gamebot_app
- **Success**:
  - All environment files have both ADMIN_DATABASE_URL and DATABASE_URL
  - Alembic uses gamebot_admin credentials
  - All services (API, bot, daemons) use gamebot_app credentials
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 177-192) - Environment variable configuration
- **Dependencies**:
  - Task 0.1 completion (users must exist)

### Task 0.3: Verify RLS enforcement with non-superuser

Run validation tests to confirm RLS policies work correctly with non-superuser role.

- **Files**:
  - Integration test environment with `gamebot_app` user
- **Success**:
  - RLS correctly filters rows when context set to 2 guild IDs → Returns 2 rows
  - RLS correctly filters rows when context set to 1 guild ID → Returns 1 row
  - RLS correctly filters rows when context is empty → Returns 0 rows
  - RLS correctly blocks access when no context set → Returns 0 rows
  - Admin user (`gamebot_admin`) bypasses RLS (expected for migrations)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 98-113) - RLS validation test results
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 194-236) - Verification test SQL commands
- **Dependencies**:
  - Task 0.1 and 0.2 completion (users and env vars configured)
- **Test Commands**:
  ```bash
  docker compose --env-file config/env.int exec postgres psql -U gamebot_app -d game_scheduler_integration
  # Run validation SQL from research file
  ```

## Phase 1: Infrastructure + Tests (Week 1)

### Task 1.1: Write unit tests for ContextVar functions

Create comprehensive unit tests for ContextVar management functions before implementation.

- **Files**:
  - `tests/shared/data_access/test_guild_isolation.py` (NEW) - Unit tests for set/get/clear functions
- **Success**:
  - Tests written for set_current_guild_ids
  - Tests written for get_current_guild_ids (with and without set)
  - Tests written for clear_current_guild_ids
  - Tests written for async task isolation
  - Tests initially fail (module doesn't exist)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 269-325) - Unit test examples
- **Dependencies**:
  - Phase 0 completion

### Task 1.2: Implement ContextVar functions

Implement thread-safe, async-safe ContextVar functions for guild ID storage.

- **Files**:
  - `shared/data_access/guild_isolation.py` (NEW) - ContextVar functions
- **Success**:
  - All unit tests from Task 1.1 pass
  - Functions are thread-safe and async-safe
  - No global state or race conditions
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 327-369) - ContextVar implementation
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 46-59) - ContextVar architecture overview
- **Dependencies**:
  - Task 1.1 completion (tests exist)
- **Test Command**: `uv run pytest tests/shared/data_access/test_guild_isolation.py -v`

### Task 1.3: Write integration tests for event listener

Create integration tests for SQLAlchemy event listener before implementation.

- **Files**:
  - `tests/integration/test_guild_isolation_rls.py` (NEW) - Integration tests
- **Success**:
  - Test for event listener setting RLS context on transaction begin
  - Test for handling empty guild list
  - Test for no-op when guild_ids not set
  - Tests initially fail (event listener not implemented)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 371-402) - Integration test examples
- **Dependencies**:
  - Task 1.2 completion (ContextVar functions exist)

### Task 1.4: Implement SQLAlchemy event listener

Implement event listener that sets PostgreSQL session variable on transaction begin.

- **Files**:
  - `shared/data_access/guild_isolation.py` (UPDATE) - Add event listener
- **Success**:
  - All integration tests from Task 1.3 pass
  - Event listener registered on AsyncSession
  - PostgreSQL session variable set correctly
  - Transparent to application code
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 404-457) - Event listener implementation
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 69-80) - Event listener architecture
- **Dependencies**:
  - Task 1.3 completion (integration tests exist)
- **Test Command**: `uv run scripts/run-integration-tests.sh -- tests/integration/test_guild_isolation_rls.py -v`

### Task 1.5: Write tests for enhanced database dependency

Create tests for `get_db_with_user_guilds()` dependency function.

- **Files**:
  - `tests/services/api/test_database_dependencies.py` (NEW) - Dependency tests
- **Success**:
  - Test for setting guild_ids in ContextVar
  - Test for clearing ContextVar on normal exit
  - Test for clearing ContextVar on exception
  - Tests initially fail (function doesn't exist)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 459-608) - Database dependency tests and implementation
- **Dependencies**:
  - Task 1.4 completion (event listener exists)
- **Mock Pattern**: Mock CurrentUser and user guilds from Discord API

### Task 1.6: Implement enhanced database dependency

Implement `get_db_with_user_guilds()` that wraps existing `get_db()` with guild context.

- **Files**:
  - `shared/database.py` (UPDATE) - Add new dependency function
- **Success**:
  - All tests from Task 1.5 pass
  - Fetches user's guilds from Discord
  - Sets guild_ids in ContextVar
  - Yields session (existing behavior)
  - Cleans up ContextVar in finally block
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 610-669) - Database dependency implementation
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 61-68) - Enhanced dependency architecture
- **Dependencies**:
  - Task 1.5 completion (tests exist)
- **Test Command**: `uv run pytest tests/services/api/test_database_dependencies.py -v`

### Task 1.7: Register event listener in application startup

Import guild_isolation module in app.py to register event listener at startup.

- **Files**:
  - `services/api/app.py` (UPDATE) - Add import to register listener
- **Success**:
  - Application starts without errors
  - Event listener registered (verify in logs)
  - No behavior changes (RLS still disabled)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 671-713) - Application startup registration
- **Dependencies**:
  - Task 1.4 completion (event listener implemented)
- **Test Command**: `docker compose up api` (check logs)

### Task 1.8: Create Alembic migration for RLS policies (disabled)

Create migration that adds RLS policies but leaves them disabled for testing.

- **Files**:
  - `alembic/versions/NNNN_add_rls_policies_disabled.py` (NEW via alembic revision)
- **Success**:
  - Migration runs successfully
  - Policies created on game_sessions, game_templates, participants
  - Indexes created on guild_id columns
  - RLS still disabled (ALTER TABLE ... DISABLE ROW LEVEL SECURITY)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 715-816) - RLS migration SQL
- **Dependencies**:
  - Task 1.4 completion (event listener ready to set context)
- **Commands**:
  ```bash
  docker compose exec api uv run alembic revision -m "add_rls_policies_disabled"
  docker compose exec api uv run alembic upgrade head
  docker compose exec postgres psql -U gamebot_app -d game_scheduler -c "\d game_sessions"
  ```

### Task 1.9: Full test suite validation (Phase 1)

Run all tests to verify infrastructure added without breaking existing functionality.

- **Files**:
  - All test files
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All E2E tests pass
  - Zero behavior changes (RLS disabled, context set but not enforced)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 818-835) - Test suite validation
- **Dependencies**:
  - Tasks 1.1-1.8 completion
- **Commands**:
  ```bash
  uv run pytest tests/shared/ tests/services/ -v
  uv run scripts/run-integration-tests.sh
  uv run scripts/run-e2e-tests.sh
  ```

## Phase 2: Service Factory Migration (Week 2)

### Task 2.1: Write integration tests for game service RLS

Create integration tests for game service guild isolation before migrating service factory.

- **Files**:
  - `tests/integration/test_game_service_guild_isolation.py` (NEW) - Game service tests
- **Success**:
  - Test for list_games filtering by user guilds
  - Test for get_game returning None for other guild's game
  - Test for direct SQLAlchemy query respecting RLS context
  - Tests pass with current `get_db` (will continue passing after migration)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 898-1004) - Game service integration tests
- **Dependencies**:
  - Phase 1 completion (infrastructure ready)
- **Test Command**: `uv run scripts/run-integration-tests.sh -- tests/integration/test_game_service_guild_isolation.py -v`

### Task 2.2: Migrate game service factory

Change single line in `_get_game_service()` to use enhanced dependency.

- **Files**:
  - `services/api/routes/games.py` (UPDATE) - Line 88, change get_db to get_db_with_user_guilds
- **Success**:
  - All game route tests still pass
  - All integration tests still pass
  - All E2E game tests still pass
  - RLS context now set for all game service queries
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1006-1035) - Game service factory migration
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 852-887) - Service factory migration pattern
- **Dependencies**:
  - Task 2.1 completion (tests exist)
- **Commands**:
  ```bash
  uv run pytest tests/services/api/routes/test_games*.py -v
  uv run scripts/run-integration-tests.sh
  uv run scripts/run-e2e-tests.sh -- tests/e2e/test_game*.py -v
  ```

### Task 2.3: Write integration tests for template routes RLS

Create integration tests for template routes guild isolation.

- **Files**:
  - `tests/integration/test_template_routes_guild_isolation.py` (NEW) - Template route tests
- **Success**:
  - Test for list_templates filtering by user guilds
  - Test for get_template returning 404 for other guild's template
  - Tests pass after route migrations
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1037-1090) - Template routes integration tests
- **Dependencies**:
  - Task 2.2 completion (game service migrated)
- **Test Command**: `uv run scripts/run-integration-tests.sh -- tests/integration/test_template*.py -v`

### Task 2.4: Migrate template route dependencies (7 functions)

Change dependency in 7 template route handler functions to use enhanced dependency.

- **Files**:
  - `services/api/routes/templates.py` (UPDATE) - Lines 47, 128, 178, 242, 296, 328, 378
    - list_templates
    - get_template
    - create_template
    - update_template
    - delete_template
    - duplicate_template
    - reorder_templates
- **Success**:
  - All template route tests pass
  - All integration tests pass
  - RLS context now set for all template queries
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1092-1171) - Template route migrations
- **Dependencies**:
  - Task 2.3 completion (tests exist)
- **Commands**:
  ```bash
  uv run pytest tests/services/api/routes/test_templates.py -v
  uv run scripts/run-integration-tests.sh -- tests/integration/test_template*.py -v
  ```

### Task 2.5: Migrate guild routes dependency

Change dependency in list_guilds route handler to use enhanced dependency.

- **Files**:
  - `services/api/routes/guilds.py` (UPDATE) - Line 46, list_guilds function
- **Success**:
  - All guild route tests pass
  - RLS context set for guild queries
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1173-1190) - Guild route migration
- **Dependencies**:
  - Task 2.4 completion (template routes migrated)
- **Test Command**: `uv run pytest tests/services/api/routes/test_guilds.py -v`

### Task 2.6: Migrate export route dependency

Change dependency in export_game_to_ical route handler to use enhanced dependency.

- **Files**:
  - `services/api/routes/export.py` (UPDATE) - Line 92, export_game_to_ical function
- **Success**:
  - All export route tests pass
  - RLS context set for export queries
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1192-1208) - Export route migration
- **Dependencies**:
  - Task 2.5 completion (guild routes migrated)
- **Test Command**: `uv run pytest tests/services/api/routes/test_export.py -v`

### Task 2.7: Full test suite validation (Phase 2)

Run all tests after all service factory migrations complete.

- **Files**:
  - All test files
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All E2E tests pass
  - 8 locations migrated (1 service factory + 7 route handlers)
  - RLS context set on every query but not enforced yet (RLS disabled)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1210-1228) - Phase 2 validation
- **Dependencies**:
  - Tasks 2.1-2.6 completion
- **Commands**:
  ```bash
  uv run pytest tests/shared/ tests/services/ -v
  uv run scripts/run-integration-tests.sh
  uv run scripts/run-e2e-tests.sh
  ```

## Phase 3: Enable RLS + E2E Validation (Week 3)

### Task 3.1: Write E2E tests for cross-guild isolation

Create comprehensive E2E tests for guild isolation across full request flow.

- **Files**:
  - `tests/e2e/test_guild_isolation_e2e.py` (NEW) - E2E isolation tests
- **Success**:
  - Test for user cannot see games from other guilds
  - Test for user cannot access other guild game by ID (404)
  - Test for user cannot join other guild game
  - Test for template isolation across guilds
  - Tests initially fail (RLS disabled), will pass after RLS enabled
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1230-1314) - E2E test examples
- **Dependencies**:
  - Phase 2 completion (all routes migrated)
- **Test Command**: `uv run scripts/run-e2e-tests.sh -- tests/e2e/test_guild_isolation_e2e.py -v` (expected to fail initially)

### Task 3.2: Enable RLS on game_sessions table

Create migration to enable RLS enforcement on game_sessions table.

- **Files**:
  - `alembic/versions/MMMM_enable_rls_game_sessions.py` (NEW via alembic revision)
- **Success**:
  - Migration runs successfully
  - RLS active on game_sessions table
  - Existing policies now enforced
  - Application queries automatically filtered by guild
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1316-1351) - RLS enablement migration
- **Dependencies**:
  - Task 3.1 completion (E2E tests written)
- **Commands**:
  ```bash
  docker compose exec api uv run alembic revision -m "enable_rls_game_sessions"
  docker compose exec api uv run alembic upgrade head
  docker compose exec postgres psql -U gamebot_app -d game_scheduler -c "\d game_sessions"
  # Should show "Row-level security: ENABLED"
  ```

### Task 3.3: Run E2E tests and validate game isolation

Execute E2E tests to verify game_sessions isolation works end-to-end.

- **Files**:
  - E2E test suite for games
- **Success**:
  - E2E guild isolation tests pass (previously failing)
  - User A cannot see User B's games from different guild
  - User A cannot access User B's game by ID (404)
  - User A cannot join User B's game
  - All existing game E2E tests still pass
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1230-1314) - E2E test specifications
- **Dependencies**:
  - Task 3.2 completion (RLS enabled on game_sessions)
- **Commands**:
  ```bash
  uv run scripts/run-e2e-tests.sh -- tests/e2e/test_guild_isolation_e2e.py -v
  uv run scripts/run-e2e-tests.sh -- tests/e2e/test_game*.py -v
  ```

### Task 3.4: Enable RLS on game_templates table

Create migration to enable RLS enforcement on game_templates table.

- **Files**:
  - `alembic/versions/OOOO_enable_rls_game_templates.py` (NEW via alembic revision)
- **Success**:
  - Migration runs successfully
  - RLS active on game_templates table
  - Template queries automatically filtered by guild
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1316-1351) - RLS enablement pattern (same for game_templates)
- **Dependencies**:
  - Task 3.3 completion (game_sessions RLS validated)
- **Commands**:
  ```bash
  docker compose exec api uv run alembic revision -m "enable_rls_game_templates"
  docker compose exec api uv run alembic upgrade head
  docker compose exec postgres psql -U gamebot_app -d game_scheduler -c "\d game_templates"
  ```

### Task 3.5: Run E2E tests and validate template isolation

Execute E2E tests to verify game_templates isolation works end-to-end.

- **Files**:
  - E2E test suite for templates
- **Success**:
  - Template isolation E2E tests pass
  - User A cannot see User B's templates from different guild
  - User A cannot access User B's template by ID (404)
  - All existing template E2E tests still pass
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1294-1313) - Template isolation E2E tests
- **Dependencies**:
  - Task 3.4 completion (RLS enabled on game_templates)
- **Test Command**: `uv run scripts/run-e2e-tests.sh -- tests/e2e/test_template*.py -v`

### Task 3.6: Enable RLS on participants table

Create migration to enable RLS enforcement on participants table.

- **Files**:
  - `alembic/versions/PPPP_enable_rls_participants.py` (NEW via alembic revision)
- **Success**:
  - Migration runs successfully
  - RLS active on participants table
  - Participant queries automatically filtered by game's guild
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1316-1351) - RLS enablement pattern (same for participants)
- **Dependencies**:
  - Task 3.5 completion (game_templates RLS validated)
- **Commands**:
  ```bash
  docker compose exec api uv run alembic revision -m "enable_rls_participants"
  docker compose exec api uv run alembic upgrade head
  docker compose exec postgres psql -U gamebot_app -d game_scheduler -c "\d participants"
  ```

### Task 3.7: Full test suite validation (Phase 3)

Run complete test suite with all RLS policies enabled.

- **Files**:
  - All test files
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All E2E tests pass
  - Guild isolation working end-to-end
  - Zero false positives (legitimate queries still work)
  - Zero false negatives (cross-guild queries blocked)
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1210-1228) - Test suite validation pattern
- **Dependencies**:
  - Tasks 3.1-3.6 completion (all RLS policies enabled)
- **Commands**:
  ```bash
  uv run pytest tests/shared/ tests/services/ -v
  uv run scripts/run-integration-tests.sh
  uv run scripts/run-e2e-tests.sh
  ```

### Task 3.8: Production readiness verification

Perform final checks before production deployment.

- **Files**:
  - All production configuration files
  - Staging environment
- **Success**:
  - Staging deployment successful with RLS enabled
  - Performance testing shows no significant regression
  - Monitoring configured for RLS policy violations
  - Rollback plan documented and tested
  - Production deployment checklist complete
- **Research References**:
  - #file:../research/20260101-middleware-rls-guild-isolation-research.md (Lines 1-39) - Executive summary and benefits
- **Dependencies**:
  - Task 3.7 completion (all tests pass)
- **Verification Steps**:
  1. Deploy to staging environment
  2. Run full test suite in staging
  3. Monitor for errors/warnings in logs
  4. Verify guild isolation in staging with real Discord data
  5. Test rollback procedure
  6. Document production deployment steps
  7. Schedule production deployment with team

## Dependencies

- PostgreSQL 15+ for RLS support
- SQLAlchemy 2.0+ for async event listeners
- FastAPI dependency injection system
- Non-superuser database role (gamebot_app) for RLS enforcement
- Existing authentication system (CurrentUser, OAuth)
- Discord API for guild membership

## Success Criteria

- Phase 0: Database users configured, RLS enforcement validated with non-superuser
- Phase 1: Infrastructure complete, event listener active, RLS policies created (disabled), all tests pass
- Phase 2: All tenant-scoped routes migrated to use enhanced dependency, all tests pass
- Phase 3: RLS enabled on all tables, E2E guild isolation verified, production ready
- Overall: Zero breaking changes, database-level defense against cross-guild queries, 3.5 week delivery
