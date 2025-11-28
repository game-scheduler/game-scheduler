<!-- markdownlint-disable-file -->

# Release Changes: Environment Initialization Service

**Related Plan**: 20251128-environment-initialization-service-plan.instructions.md
**Implementation Date**: 2025-11-28

## Summary

Created a dedicated initialization service that runs database migrations and verifies schema integrity before application services start in all environments. This ensures proper startup order and database readiness across development, integration tests, e2e tests, and production deployments.

## Changes

### Added

- docker/init.Dockerfile - Renamed from migrate.Dockerfile for clarity
- docker/init-entrypoint.sh - Renamed from migrate-entrypoint.sh for clarity
- docker-compose.base.yml - Added init service that runs migrations and verifies schema before application services start

### Modified

- docker/init-entrypoint.sh (renamed from migrate-entrypoint.sh) - Enhanced with timestamped logging, schema verification, and production-ready error handling
- docker-compose.base.yml - Updated bot, api, scheduler, scheduler-beat, and notification-daemon services to depend on init completion
- alembic/env.py - Added DATABASE_URL environment variable support with automatic async driver conversion (outside of plan - needed to fix connection issue)

### Removed

- docker/migrate.Dockerfile - Renamed to init.Dockerfile
- docker/migrate-entrypoint.sh - Renamed to init-entrypoint.sh

## Release Summary

**Total Files Affected**: 3

### Files Created (0)

None - reused existing migration infrastructure.

### Files Modified (3)

- docker/init-entrypoint.sh (renamed from migrate-entrypoint.sh) - Enhanced with timestamped logging, PostgreSQL connection wait with status messages, migration execution confirmation, schema verification for all critical tables (users, guild_configurations, channel_configurations, game_sessions, game_participants, notification_schedule), and clear success/failure reporting
- docker-compose.base.yml - Added init service that depends only on postgres health check (migrations only need database). Updated all application services (bot, api, scheduler, scheduler-beat, notification-daemon) to depend on init service completion instead of directly depending on infrastructure health checks. Updated to reference docker/init.Dockerfile
- alembic/env.py - Added DATABASE_URL environment variable support with automatic conversion to async driver format (postgresql+asyncpg://). This was required to fix connection issues but was not part of the original plan

### Files Removed (0)

None.

### Dependencies & Infrastructure

- **New Dependencies**: None - renamed existing docker/migrate.Dockerfile to docker/init.Dockerfile
- **Updated Dependencies**: None
- **Infrastructure Changes**: Added init service to docker-compose.base.yml that runs migrations and verifies schema before application services start
- **Configuration Updates**: Modified alembic/env.py to read DATABASE_URL from environment variables

### Deployment Notes

The init service will run automatically in all environments (development, integration tests, e2e tests, production) when using `docker compose up`. It will:

1. Wait for PostgreSQL to become healthy
2. Run all pending Alembic migrations
3. Verify that all critical database tables exist
4. Exit with code 0 on success or code 1 on failure
5. Application services will only start after init completes successfully

No changes required to existing deployment procedures. The init service is idempotent and safe to run multiple times.
