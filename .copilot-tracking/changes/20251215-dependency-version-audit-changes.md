# Changes: Dependency Version Audit and Upgrade Strategy

**Plan**: [20251215-dependency-version-audit-plan.instructions.md](../plans/20251215-dependency-version-audit-plan.instructions.md)
**Details**: [20251215-dependency-version-audit-details.md](../details/20251215-dependency-version-audit-details.md)
**Research**: [20251215-dependency-version-audit-research.md](../research/20251215-dependency-version-audit-research.md)

## Phase Status

- [x] **Phase 1: PostgreSQL 18 Upgrade + Alembic Reset** - ✅ Complete
  - [x] Task 1.1: Fix SQLAlchemy models server_default - ✅ Complete
  - [x] Task 1.2: Install alembic-utils - ✅ Complete
  - [x] Task 1.3: Update PostgreSQL to 18-alpine - ✅ Complete
  - [x] Task 1.4: Reset Alembic migrations - ✅ Complete
  - [x] Task 1.5: Verify database schema and services - ✅ Complete
- [ ] **Phase 2: Node.js 24 LTS Upgrade**
- [ ] **Phase 3: Python Dependency Modernization**
- [ ] **Phase 4: NPM Package Updates**

## Changes Log

### Phase 1: PostgreSQL 18 Upgrade + Alembic Reset

#### Task 1.1: Fix SQLAlchemy models server_default ✅

**Purpose**: Add `server_default` declarations to all SQLAlchemy models to prevent Alembic autogenerate from dropping PostgreSQL server defaults during migration reset.

**Files Modified**:
- [shared/models/guild.py](../../../shared/models/guild.py) - Lines 21, 47-52
- [shared/models/channel.py](../../../shared/models/channel.py) - Lines 21, 45-49
- [shared/models/game.py](../../../shared/models/game.py) - Lines 21, 75-84
- [shared/models/template.py](../../../shared/models/template.py) - Lines 21, 51-58
- [shared/models/participant.py](../../../shared/models/participant.py) - Lines 21, 53
- [shared/models/user.py](../../../shared/models/user.py) - Lines 21, 45-51
- [shared/models/notification_schedule.py](../../../shared/models/notification_schedule.py) - Lines 21, 50-53
- [shared/models/game_status_schedule.py](../../../shared/models/game_status_schedule.py) - Lines 21, 48-51

**Changes Made**:
1. **Added SQLAlchemy imports**: Added `func` and `text` imports to all model files
2. **Boolean columns**: Added `server_default=text('false')` or `text('true')` to:
   - `GuildConfiguration.require_host_role`
   - `ChannelConfiguration.is_active`
   - `GameTemplate.is_default`
   - `NotificationSchedule.sent`
   - `GameStatusSchedule.executed`
3. **Integer columns**: Added `server_default=text('0')` to:
   - `GameTemplate.order`
4. **String columns**: Added `server_default=text("'SCHEDULED'")` to:
   - `GameSession.status`
5. **JSON columns**: Added `server_default=text("'{}'")` to:
   - `User.notification_preferences`
6. **Timestamp columns**: Added `server_default=func.now()` to all `created_at` and `updated_at` columns across all models

**Verification**:
- ✅ All models import successfully
- ✅ All model unit tests pass (19 tests)
- ✅ All Python unit tests pass (679 tests, 18.62s)
- ✅ All frontend tests pass (51 tests, 8.78s)
- ✅ All integration tests pass (37 tests, 112.95s)
- ✅ No breaking changes to existing behavior
- ✅ Total: **767 tests passing**

**Key Design Decisions**:
- Used SQLAlchemy's `text()` for literal values (booleans, strings, JSON)
- Used SQLAlchemy's `func.now()` for timestamp defaults (translates to PostgreSQL's `now()`)
- Maintained Python-side `default=` for backward compatibility with existing code
- Server defaults ensure database consistency even when SQLAlchemy is bypassed

#### Task 1.2: Install alembic-utils ✅

**Purpose**: Install alembic-utils package and register PostgreSQL functions and triggers to ensure they are tracked in Alembic migrations.

**Files Modified**:
- [pyproject.toml](../../../pyproject.toml) - Line 17
- [alembic/env.py](../../../alembic/env.py) - Lines 29-31, 58, 80-82, 122-126

**Files Created**:
- [shared/database_objects.py](../../../shared/database_objects.py) - New file defining PostgreSQL functions and triggers

**Changes Made**:
1. **Added alembic-utils dependency**: Added `alembic-utils>=0.8.0` to pyproject.toml dependencies
2. **Created database objects module**: Created `shared/database_objects.py` to define:
   - `notify_schedule_changed()` function for notification_schedule table
   - `notification_schedule_trigger` trigger for notification_schedule changes
   - `notify_game_status_schedule_changed()` function for game_status_schedule table
   - `game_status_schedule_trigger` trigger for game_status_schedule changes
3. **Updated Alembic configuration**: Modified `alembic/env.py` to:
   - Import `PGFunction` and `PGTrigger` from alembic-utils
   - Import `ALL_DATABASE_OBJECTS` from shared.database_objects
   - Add `include_object=ALL_DATABASE_OBJECTS` to all `context.configure()` calls

**Verification**:
- ✅ alembic-utils package installed (version 0.8.8)
- ✅ Database objects module imports successfully
- ✅ All 4 database objects (2 functions, 2 triggers) registered
- ✅ Alembic env.py syntax validated
- ✅ All Python unit tests pass (577 tests, 18.03s)
- ✅ No breaking changes to existing functionality

**Key Design Decisions**:
- Used alembic-utils for automatic detection and management of PostgreSQL functions/triggers
- Centralized all database objects in a single module for maintainability
- Extracted function/trigger definitions from existing migration files (012, 020)
- Functions and triggers will be automatically included in future Alembic autogenerate operations

#### Task 1.3: Update PostgreSQL to 18-alpine ✅

**Purpose**: Update all Docker Compose files and CI/CD workflows to use PostgreSQL 18-alpine image.

**Files Modified**:
- [compose.yaml](../../../compose.yaml) - Line 28
- [.github/workflows/ci-cd.yml](../../../.github/workflows/ci-cd.yml) - Line 62

**Changes Made**:
1. **Updated base compose file**: Changed `postgres:17-alpine` to `postgres:18-alpine` in compose.yaml
2. **Updated GitHub Actions workflow**: Changed `postgres:17-alpine` to `postgres:18-alpine` in ci-cd.yml service definition

**Verification**:
- ✅ All production compose files reference postgres:18-alpine
- ✅ GitHub Actions CI/CD workflow uses postgres:18-alpine
- ✅ No active references to postgres:17-alpine remain (only in historical docs)

**Key Design Decisions**:
- Updated both runtime (compose.yaml) and CI/CD (GitHub Actions) configurations
- PostgreSQL 18 provides latest stable features and will be supported until 2029
- Historical references in documentation and migration scripts intentionally preserved

#### Task 1.4: Reset Alembic migrations ✅

**Purpose**: Consolidate 27 historical migration files into a single initial migration with clean history.

**Files Modified**:
- [alembic/versions/c2135ff3d5cd_initial_schema.py](../../../alembic/versions/c2135ff3d5cd_initial_schema.py) - New consolidated migration
- [alembic/versions/__init__.py](../../../alembic/versions/__init__.py) - New file
- [shared/models/game.py](../../../shared/models/game.py) - Fixed template_id nullability
- [shared/database_objects.py](../../../shared/database_objects.py) - Uncommented triggers
- [tests/integration/test_database_infrastructure.py](../../../tests/integration/test_database_infrastructure.py) - Accept hash revision IDs
- 27 old migration files moved to history/alembic_backup_20251216/ (later removed)

**Changes Made**:
1. **Created consolidated migration**: Single c2135ff3d5cd_initial_schema.py containing:
   - All 8 tables (guilds, channels, games, templates, participants, users, notification_schedule, game_status_schedule)
   - All indexes and constraints
   - 2 PGFunctions with split SQL strings to meet line length requirements
   - 2 triggers created via op.execute()
   - Complete upgrade() and downgrade() functions
2. **Fixed template_id nullability**: Changed from `Mapped[str]` to `Mapped[str | None]` with `nullable=True, index=True`
3. **Uncommented triggers**: Enabled notification_schedule_trigger and game_status_schedule_trigger in database_objects.py
4. **Updated integration tests**: Removed underscore requirement for revision IDs to accept hash format
5. **Archived old migrations**: Moved 27 files to history/alembic_backup_20251216/ then removed from repository

**Verification**:
- ✅ Single migration file with hash-format revision ID
- ✅ All database tables created correctly
- ✅ All indexes and constraints present
- ✅ Functions and triggers working
- ✅ All 679 Python unit tests PASSED
- ✅ All 51 Frontend tests PASSED
- ✅ All 37 Integration tests PASSED

**Key Design Decisions**:
- Used hash-based revision ID (Alembic default for new migrations)
- Split long SQL strings across multiple lines to meet 100-char line limit
- Kept server_default declarations from Task 1.1 to preserve database defaults
- Used alembic-utils for function/trigger management from Task 1.2

#### Task 1.5: Verify database schema and services ✅

**Purpose**: Ensure all services start correctly and database schema matches models.

**Verification Results**:
- ✅ PostgreSQL 18-alpine container starts successfully
- ✅ Alembic migration applies cleanly (single c2135ff3d5cd revision)
- ✅ All 8 tables created with correct schemas
- ✅ All foreign keys and indexes present
- ✅ Functions and triggers operational
- ✅ All services connect to database successfully
- ✅ Integration tests verify complete database infrastructure
- ✅ No errors in service logs

---

**Phase 1 Complete**: 2025-12-16 09:30 UTC
