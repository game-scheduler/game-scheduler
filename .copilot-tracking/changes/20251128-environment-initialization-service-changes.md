<!-- markdownlint-disable-file -->

# Release Changes: Environment Initialization Service

**Related Plan**: 20251128-environment-initialization-service-plan.instructions.md
**Implementation Date**: 2025-11-28

## Summary

Created a dedicated initialization service that runs database migrations and verifies schema integrity before application services start in all environments. This ensures proper startup order and database readiness across development, integration tests, e2e tests, and production deployments.

Additionally fixed multiple issues discovered during testing: Docker Compose OAuth environment variables, frontend Vite build-time variables, bot guild configuration NOT NULL violation, and database UUID type inconsistency.

## Changes

### Added

- docker/init.Dockerfile - Renamed from migrate.Dockerfile for clarity
- docker/init-entrypoint.sh - Renamed from migrate-entrypoint.sh for clarity
- docker-compose.base.yml - Added init service that runs migrations and verifies schema before application services start
- alembic/versions/013_change_notification_schedule_id_to_string.py - Migration to convert notification_schedule.id from UUID to String(36)

### Modified

- docker/init-entrypoint.sh (renamed from migrate-entrypoint.sh) - Enhanced with timestamped logging, schema verification, and production-ready error handling
- docker-compose.base.yml - Updated bot, api, scheduler, scheduler-beat, and notification-daemon services to depend on init completion; added missing environment variables to api and frontend services for OAuth authentication
- docker/frontend.Dockerfile - Added ARG directives for VITE_DISCORD_CLIENT_ID and VITE_API_URL to support build-time environment variable injection
- services/bot/commands/config_guild.py - Fixed /config-guild command to pass guild_name parameter when creating GuildConfiguration
- shared/models/notification_schedule.py - Changed id column from UUID(as_uuid=False) to String(36) for consistency with other tables
- alembic/env.py - Added DATABASE_URL environment variable support with automatic async driver conversion (outside of plan - needed to fix connection issue)

### Removed

- docker/migrate.Dockerfile - Renamed to init.Dockerfile
- docker/migrate-entrypoint.sh - Renamed to init-entrypoint.sh

## Release Summary

**Total Files Affected**: 7

### Files Created (1)

- alembic/versions/013_change_notification_schedule_id_to_string.py - Migration to convert notification_schedule.id from UUID to String(36) for consistency with all other tables in the schema

### Files Modified (6)

- docker/init-entrypoint.sh (renamed from migrate-entrypoint.sh) - Enhanced with timestamped logging, PostgreSQL connection wait with status messages, migration execution confirmation, schema verification for all critical tables (users, guild_configurations, channel_configurations, game_sessions, game_participants, notification_schedule), and clear success/failure reporting
- docker-compose.base.yml - Added init service that depends only on postgres health check. Added missing environment variables to api service (DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN, FRONTEND_URL, API_URL, JWT_SECRET, ENVIRONMENT, LOG_LEVEL). Added build args to frontend service (VITE_DISCORD_CLIENT_ID, VITE_API_URL). Updated all application services (bot, api, scheduler, scheduler-beat, notification-daemon) to depend on init service completion. Updated to reference docker/init.Dockerfile
- docker/frontend.Dockerfile - Added ARG directives for VITE_DISCORD_CLIENT_ID and VITE_API_URL before npm build step to support build-time environment variable injection required by Vite
- services/bot/commands/config_guild.py - Fixed _get_or_create_guild_config() to accept and use guild_name parameter; updated /config-guild command to pass interaction.guild.name when creating GuildConfiguration
- shared/models/notification_schedule.py - Changed id column type from UUID(as_uuid=False) to String(36) for consistency with all other tables in the schema
- alembic/env.py - Added DATABASE_URL environment variable support with automatic conversion to async driver format (postgresql+asyncpg://). This was required to fix connection issues but was not part of the original plan

### Files Removed (0)

None.

### Dependencies & Infrastructure

- **New Dependencies**: None - renamed existing docker/migrate.Dockerfile to docker/init.Dockerfile
- **Updated Dependencies**: None
- **Infrastructure Changes**: Added init service to docker-compose.base.yml that runs migrations and verifies schema before application services start. Fixed Docker Compose environment variable pass-through for OAuth authentication after refactor removed env_file directive
- **Configuration Updates**: Modified alembic/env.py to read DATABASE_URL from environment variables. Added build-time environment variables to frontend Docker build for Vite

### Bug Fixes

Fixed multiple issues discovered during testing:

1. **Discord OAuth Authentication** - Docker Compose refactor changed from `env_file: .env` to explicit `environment:` variables but incompletely. Added missing DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN, FRONTEND_URL, API_URL, JWT_SECRET to api service environment
2. **Frontend Build Failures** - Vite requires environment variables at build time. Added ARG directives for VITE_DISCORD_CLIENT_ID and VITE_API_URL to frontend.Dockerfile and corresponding build args in docker-compose.base.yml
3. **Guild Configuration NOT NULL Violation** - /config-guild command created GuildConfiguration without required guild_name field. Fixed by passing interaction.guild.name parameter
4. **UUID Type Mismatch** - notification_schedule.id used PostgreSQL UUID type while all other tables use String(36). Created migration 013 to convert column type and updated model for consistency

### Deployment Notes

The init service will run automatically in all environments (development, integration tests, e2e tests, production) when using `docker compose up`. It will:

1. Wait for PostgreSQL to become healthy
2. Run all pending Alembic migrations
3. Verify that all critical database tables exist
4. Exit with code 0 on success or code 1 on failure
5. Application services will only start after init completes successfully

No changes required to existing deployment procedures. The init service is idempotent and safe to run multiple times.
