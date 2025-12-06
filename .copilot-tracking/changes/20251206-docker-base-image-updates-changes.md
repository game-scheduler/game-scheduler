<!-- markdownlint-disable-file -->

# Release Changes: Docker Base Image Version Updates

**Related Plan**: 20251206-docker-base-image-updates-plan.instructions.md
**Implementation Date**: 2025-12-06

## Summary

Updating all Docker base images to their most recent stable LTS versions to
ensure long-term support, security patches, and maintain best practices for
containerization. This includes Python 3.11→3.13, Nginx 1.25→1.28, Redis 7→7.4,
PostgreSQL 15→17, and optionally Node.js 20→22.

## Changes

### Added

- scripts/migrate_postgres_15_to_17.sh - Migration script for safely upgrading
  PostgreSQL from version 15 to 17 using pg_dump/pg_restore with automatic
  backup and rollback support
- tests/integration/test_database_infrastructure.py - Comprehensive integration
  tests for database infrastructure validation including PostgreSQL version
  compatibility, schema completeness, migration status, indexes, triggers, and
  constraints (9 new tests)

### Modified

- docker/api.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  in both base and production stages
- docker/bot.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  in both base and production stages
- docker/init.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/notification-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim in both base and production stages
- docker/status-transition-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim in both base and production stages
- docker/test.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/frontend.Dockerfile - Updated Node.js base image from 20-alpine to
  22-alpine in builder stage for longer LTS support
- docker/frontend.Dockerfile - Updated Nginx base image from 1.25-alpine to
  1.28-alpine in production stage for current stable branch
- docker-compose.base.yml - Updated Redis image from redis:7-alpine to
  redis:7.4-alpine for latest patches in 7.x line
- docker-compose.base.yml - Updated PostgreSQL image from postgres:15-alpine to
  postgres:17-alpine for latest stable version with extended support
- frontend/README.md - Updated Node.js version requirement from 18+ to 22+ to
  match Docker image update
- .github/instructions/python.instructions.md - Updated Python version reference
  from 3.11+ to 3.13+ to match Docker image update
- RUNTIME_CONFIG.md - Added documentation note about current base image versions
  (PostgreSQL 17, Redis 7.4, Python 3.13, Node.js 22, Nginx 1.28)

### Testing and Validation

#### Task 4.1: Rebuild all Docker images

- All Docker images built successfully with updated base versions
- No dependency conflicts encountered
- Build time: ~6.8 minutes for full rebuild
- All services: api, bot, frontend, init, notification-daemon,
  status-transition-daemon built without errors

#### Task 4.2: Run integration tests

- All 43 integration tests passed successfully (34 original + 9 new database
  infrastructure tests)
- Test suite includes:
  - Database infrastructure validation (9 tests):
    - PostgreSQL version compatibility check (17.x)
    - Schema completeness verification (9 tables)
    - Alembic migration status validation
    - Critical indexes existence checks
    - NOTIFY trigger validation for scheduler
    - Foreign key constraint verification
    - Primary key constraint verification
    - Database connection health check
  - PostgreSQL listener and notification daemon integration (7 tests)
  - RabbitMQ DLQ functionality (7 tests)
  - RabbitMQ infrastructure validation (14 tests)
  - Status transition daemon integration (4 tests)
  - Game session workflow end-to-end (2 tests)
- Minor warnings about deprecated datetime methods (not breaking)
- Total test execution time: 25.74 seconds

#### Task 4.3: Verify PostgreSQL migration compatibility

- PostgreSQL 17.7 running successfully on Alpine Linux
- All Alembic migrations applied successfully (version:
  021_add_game_scheduled_at)
- Database schema verified:
  - 9 tables created successfully
  - All indexes properly applied
  - Foreign key constraints functional
  - Database triggers working correctly
- No SQL compatibility issues detected
- RabbitMQ infrastructure initialization completed successfully
- All services can connect and query PostgreSQL 17 without issues

### Removed

## Release Summary

**Total Files Affected**: 14

### Files Created (2)

- scripts/migrate_postgres_15_to_17.sh - PostgreSQL major version upgrade
  migration script with backup and rollback support
- tests/integration/test_database_infrastructure.py - Comprehensive database
  infrastructure validation test suite (9 tests)

### Files Modified (12)

- docker/api.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  (both stages)
- docker/bot.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  (both stages)
- docker/init.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/notification-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim (both stages)
- docker/status-transition-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim (both stages)
- docker/test.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/frontend.Dockerfile - Updated Node.js from 20-alpine to 22-alpine and
  Nginx from 1.25-alpine to 1.28-alpine
- docker-compose.base.yml - Updated PostgreSQL from 15-alpine to 17-alpine and
  Redis from 7-alpine to 7.4-alpine
- frontend/README.md - Updated Node.js version requirement from 18+ to 22+
- .github/instructions/python.instructions.md - Updated Python version reference
  from 3.11+ to 3.13+
- RUNTIME_CONFIG.md - Added documentation note about current base image versions
- .copilot-tracking/plans/20251206-docker-base-image-updates-plan.instructions.md -
  Marked all phases complete

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None - all updates use official Docker Hub images
- **Updated Dependencies**:
  - Python: 3.11-slim → 3.13-slim (active bugfix support until Oct 2029)
  - Node.js: 20-alpine → 22-alpine (maintenance LTS until April 2027)
  - Nginx: 1.25-alpine → 1.28-alpine (current stable branch)
  - PostgreSQL: 15-alpine → 17-alpine (support until Nov 2029)
  - Redis: 7-alpine → 7.4-alpine (latest in 7.x line)
  - RabbitMQ: 4.2-management-alpine (no change - already latest)
- **Infrastructure Changes**:
  - PostgreSQL major version upgrade (15→17) requires data migration
  - Migration script provided: scripts/migrate_postgres_15_to_17.sh
  - All Alembic migrations compatible with PostgreSQL 17
  - Database triggers and LISTEN/NOTIFY functionality verified
- **Configuration Updates**:
  - Documentation updated to reflect new version requirements
  - No environment variable changes required
  - No application code changes required

### Deployment Notes

**PostgreSQL Migration:**

1. The PostgreSQL upgrade from 15 to 17 is a major version change
2. Data migration script provided: `scripts/migrate_postgres_15_to_17.sh`
3. Script performs automatic backup before upgrade with rollback support
4. All database tests pass with PostgreSQL 17.7

**Image Compatibility:**

- All Python services compatible with Python 3.13 (no code changes required)
- All dependency versions compatible with updated base images
- Multi-architecture support maintained (ARM64 and AMD64)

**Testing:**

- 43 integration tests pass successfully (34 original + 9 new database tests)
- All services build successfully with updated images
- No breaking changes in application functionality
- Build time: ~6.8 minutes for full rebuild

**Rollback:**

- To rollback, revert changes to Dockerfiles and docker-compose.base.yml
- For PostgreSQL, use backup created by migration script if needed
- No application code changes required for rollback
