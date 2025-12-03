<!-- markdownlint-disable-file -->

# Task Details: Remove channel_name from Database

## Research Reference

**Source Research**: #file:../research/20251201-remove-channel-name-from-database-research.md

## Phase 1: Database Migration

### Task 1.1: Create Alembic migration to drop channel_name column

Create new Alembic migration file to remove the `channel_name` column from `channel_configurations` table.

- **Files**:
  - alembic/versions/016_remove_channel_name.py - New migration file
- **Success**:
  - Migration file created with proper revision ID
  - upgrade() drops channel_name column
  - downgrade() restores column with server_default
  - Migration applies cleanly to development database
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 200-220) - Migration template
- **Dependencies**:
  - None (first task)

## Phase 2: Update Models and Schemas

### Task 2.1: Remove channel_name field from SQLAlchemy model

Remove `channel_name` field from ChannelConfiguration model and update `__repr__` method.

- **Files**:
  - shared/models/channel.py (Line 46) - Remove channel_name field
  - shared/models/channel.py (Line 62) - Update __repr__ method
- **Success**:
  - channel_name field removed from model
  - __repr__ updated to not reference channel_name
  - No import or type errors
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 17-20) - Current model definition
- **Dependencies**:
  - Task 1.1 completion (migration created)

### Task 2.2: Update Pydantic schemas

Remove `channel_name` from create/update request schemas, keep in response schema.

- **Files**:
  - shared/schemas/channel.py (Line 29) - Remove from ChannelConfigCreateRequest
  - shared/schemas/channel.py (Line 52) - Remove from ChannelConfigUpdateRequest
  - shared/schemas/channel.py (Line 68) - Keep in ChannelConfigResponse (fetched at runtime)
- **Success**:
  - ChannelConfigCreateRequest no longer requires channel_name input
  - ChannelConfigUpdateRequest no longer accepts channel_name
  - ChannelConfigResponse still includes channel_name field (for API responses)
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 22-28) - Schema definitions
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Update API Routes

### Task 3.1: Update get_channel endpoint to fetch channel name dynamically

Inject discord_client dependency and fetch channel name from Discord API with caching.

- **Files**:
  - services/api/routes/channels.py (Lines 40-98) - Update get_channel function
  - services/api/dependencies.py - May need to add get_discord_client dependency
- **Success**:
  - discord_client injected as dependency
  - Channel name fetched using discord_client.fetch_channel()
  - Error handling with fallback to "Unknown Channel"
  - Response includes dynamically fetched channel_name
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 107-130) - Proposed pattern for channels
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 68-87) - Guild pattern reference
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update create_channel_config endpoint

Remove channel_name from request handling and service call, fetch dynamically for response.

- **Files**:
  - services/api/routes/channels.py (Lines 101-147) - Update create_channel_config function
- **Success**:
  - Removed channel_name from request.channel_name usage
  - Service call no longer passes channel_name parameter
  - discord_client injected to fetch channel name for response
  - Response includes dynamically fetched channel_name
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 30-31) - Current implementation
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 107-130) - Dynamic fetch pattern
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update update_channel_config endpoint

Remove channel_name from updates dictionary, fetch dynamically for response.

- **Files**:
  - services/api/routes/channels.py (Lines 150-198) - Update update_channel_config function
- **Success**:
  - channel_name excluded from updates dictionary
  - discord_client injected to fetch channel name for response
  - Response includes dynamically fetched channel_name
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 30-31) - Current implementation
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Update Configuration Service

### Task 4.1: Remove channel_name from create_channel_config service method

Update service method to not accept or store channel_name parameter.

- **Files**:
  - services/api/services/config.py (Lines 254-280) - Update create_channel_config method
- **Success**:
  - channel_name parameter removed from method signature
  - channel_name not passed to ChannelConfiguration constructor
  - Docstring updated to remove channel_name parameter
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 33-34) - Current service implementation
  - #file:../../services/api/services/config.py (Lines 254-280) - Current code
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Remove channel_name from update_channel_config service method

Ensure channel_name is not accepted in updates dictionary.

- **Files**:
  - services/api/services/config.py (Lines 282-302) - Update update_channel_config method
- **Success**:
  - Method properly ignores channel_name if present in updates
  - No database update attempted for channel_name field
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 33-34) - Current service implementation
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Update Bot Commands

### Task 5.1: Remove channel_name logic from /config-channel command

Remove channel_name parameter from helper function call.

- **Files**:
  - services/bot/commands/config_channel.py (Lines 85-95) - Update _get_or_create_channel_config call
- **Success**:
  - Call to _get_or_create_channel_config no longer passes channel_name
  - target_channel.name no longer referenced for database storage
  - Command still functions correctly
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 36-38) - Current bot command
  - #file:../../services/bot/commands/config_channel.py (Lines 85-95) - Current code
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Update _get_or_create_channel_config helper

Remove channel_name parameter and field from ChannelConfiguration constructor.

- **Files**:
  - services/bot/commands/config_channel.py (Lines 180-220) - Update _get_or_create_channel_config function
- **Success**:
  - channel_name parameter removed from function signature
  - ChannelConfiguration() no longer includes channel_name field
  - Docstring updated to remove channel_name
  - Function creates channel configs correctly
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 36-38) - Current implementation
  - #file:../../services/bot/commands/config_channel.py (Lines 180-220) - Current code
- **Dependencies**:
  - Task 5.1 completion

## Phase 6: Update Test Fixtures

### Task 6.1: Remove channel_name from integration test SQL INSERT

Remove channel_name column and value from SQL INSERT statement.

- **Files**:
  - tests/integration/test_notification_daemon.py (Lines 109-117) - Update SQL INSERT
- **Success**:
  - SQL INSERT no longer includes channel_name column
  - SQL INSERT no longer includes channel_name value
  - Test fixture creates channel config correctly
  - Test passes
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 40-41) - Test fixture location
  - #file:../../tests/integration/test_notification_daemon.py (Lines 109-117) - Current code
- **Dependencies**:
  - Phase 5 completion

### Task 6.2: Remove channel_name from e2e test SQL INSERT

Remove channel_name column and value from SQL INSERT statement.

- **Files**:
  - tests/e2e/test_game_notification_api_flow.py (Lines 136-145) - Update SQL INSERT
- **Success**:
  - SQL INSERT no longer includes channel_name column
  - SQL INSERT no longer includes channel_name value
  - Test fixture creates channel config correctly
  - Test passes
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 40-41) - Test fixture location
  - #file:../../tests/e2e/test_game_notification_api_flow.py (Lines 136-145) - Current code
- **Dependencies**:
  - Task 6.1 completion

## Phase 7: Validation and Testing

### Task 7.1: Run database migration

Apply migration to development database and verify schema changes.

- **Files**:
  - alembic/versions/016_remove_channel_name.py - Migration to run
- **Success**:
  - Migration runs without errors using `uv run alembic upgrade head`
  - Database schema no longer contains channel_name column
  - Rollback works correctly if needed
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 200-220) - Migration details
- **Dependencies**:
  - Phase 6 completion

### Task 7.2: Run all tests and verify passing

Run unit, integration, and e2e tests to ensure no regressions.

- **Files**:
  - All test files
- **Success**:
  - Unit tests pass: `uv run pytest tests/services/ tests/shared/`
  - Integration tests pass: `./scripts/run-integration-tests.sh`
  - E2E tests pass: `./scripts/run-e2e-tests.sh`
  - No failures related to channel_name
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 258-272) - Success criteria
- **Dependencies**:
  - Task 7.1 completion

### Task 7.3: Manual testing - verify channel names display correctly

Test that channel names appear correctly in frontend and API responses.

- **Files**:
  - Frontend: Browse games, channel config, guild dashboard pages
  - API: Channel endpoints
- **Success**:
  - Channel names display in frontend (from API responses)
  - API responses include channel_name field with correct values
  - Channel name changes in Discord reflect within 5 minutes
  - Redis cache working (check logs for cache hits)
- **Research References**:
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 43-52) - Frontend usage
  - #file:../research/20251201-remove-channel-name-from-database-research.md (Lines 87-106) - Caching infrastructure
- **Dependencies**:
  - Task 7.2 completion

## Dependencies

- Existing `discord_client.fetch_channel()` method (already implemented)
- Redis caching with `CacheTTL.DISCORD_CHANNEL = 300` seconds
- Bot token with channel read permissions

## Success Criteria

- Database no longer stores channel_name
- API responses still include channel_name (fetched from Discord)
- Frontend displays channel names correctly
- All tests pass
- Channel name changes reflect within 5 minutes (cache TTL)
