<!-- markdownlint-disable-file -->

# Task Details: Remove guild_name from Database

## Research Reference

**Source Research**: #file:../research/20251130-remove-guild-name-from-database-research.md

## Phase 1: Database Migration

### Task 1.1: Create Alembic migration to drop guild_name column

Create new Alembic migration file to remove the guild_name column from guild_configurations table.

- **Files**:
  - alembic/versions/016_remove_guild_name_column.py - New migration file
- **Success**:
  - Migration file created with upgrade() and downgrade() functions
  - upgrade() drops guild_name column
  - downgrade() adds nullable guild_name column (data cannot be restored)
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 176-194) - Migration strategy
- **Dependencies**:
  - None - first task

## Phase 2: Update Models and Schemas

### Task 2.1: Remove guild_name field from SQLAlchemy model

Remove the guild_name field from the GuildConfiguration model.

- **Files**:
  - shared/models/guild.py - Remove line 45: `guild_name: Mapped[str] = mapped_column(String(100), nullable=False)`
- **Success**:
  - guild_name field removed from model
  - Model still has all other fields (guild_id, default_max_players, etc.)
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 42-50) - SQLAlchemy model current state
- **Dependencies**:
  - Task 1.1 completion (migration created)

### Task 2.2: Verify Pydantic schemas are correct

Verify that Pydantic schemas do NOT require changes - guild_name should remain in GuildConfigResponse only.

- **Files**:
  - shared/schemas/guild.py - No changes needed (verify only)
- **Success**:
  - GuildConfigResponse still has guild_name field (Line 59)
  - GuildConfigCreateRequest does NOT have guild_name
  - GuildConfigUpdateRequest does NOT have guild_name
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 52-63) - Pydantic schemas analysis
- **Dependencies**:
  - None - verification only

## Phase 3: Update Bot Commands

### Task 3.1: Remove guild_name logic from /config-guild command

Remove the guild name fetching and storage logic from the config_guild_command function.

- **Files**:
  - services/bot/commands/config_guild.py - Remove lines 64-75 (guild name fetch logic)
  - services/bot/commands/config_guild.py - Remove lines 81-83 (passing guild_name to helper)
- **Success**:
  - Guild name fetch logic removed (lines 64-75)
  - Call to _get_or_create_guild_config no longer passes guild_name parameter
  - Command still creates/updates guild config successfully
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 76-90) - Bot commands current implementation
- **Dependencies**:
  - Task 2.1 completion (model updated)

### Task 3.2: Update _get_or_create_guild_config helper

Remove guild_name parameter from the helper function and its usage.

- **Files**:
  - services/bot/commands/config_guild.py - Update _get_or_create_guild_config function (Lines 157-195)
- **Success**:
  - Function signature no longer accepts guild_name parameter
  - GuildConfiguration() constructor call does not pass guild_name
  - Function no longer returns guild_name_updated boolean (returns just config)
  - All callers updated to match new signature
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 86-90) - Helper function details
- **Dependencies**:
  - Task 3.1 completion (command updated)

## Phase 4: Update Test Fixtures

### Task 4.1: Remove guild_name from integration test SQL INSERT

Update integration test to remove guild_name from SQL INSERT statement.

- **Files**:
  - tests/integration/test_notification_daemon.py - Lines 95-101
- **Success**:
  - SQL INSERT statement no longer includes guild_name column
  - SQL INSERT statement no longer includes guild_name value
  - Test fixture still creates valid guild configuration
  - Test passes successfully
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 132-140) - Integration test current state
- **Dependencies**:
  - Task 1.1 completion (migration created)

### Task 4.2: Remove guild_name from e2e test SQL INSERT

Update e2e test to remove guild_name from SQL INSERT statement.

- **Files**:
  - tests/e2e/test_game_notification_api_flow.py - Lines 118-126
- **Success**:
  - SQL INSERT statement no longer includes guild_name column
  - SQL INSERT statement no longer includes guild_name value
  - Test fixture still creates valid guild configuration
  - Test passes successfully
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 142-148) - E2E test current state
- **Dependencies**:
  - Task 1.1 completion (migration created)

## Phase 5: Validation and Testing

### Task 5.1: Run database migration

Execute the Alembic migration to drop the guild_name column.

- **Files**:
  - Database schema (updated via Alembic)
- **Success**:
  - Migration executes successfully
  - guild_name column removed from guild_configurations table
  - No migration errors
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 176-194) - Migration details
- **Dependencies**:
  - All code changes complete (Tasks 1.1-4.2)

### Task 5.2: Run all tests and verify passing

Run unit, integration, and e2e tests to ensure all pass with updated schema.

- **Files**:
  - Test suite (all tests)
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All e2e tests pass
  - No errors related to guild_name
  - API responses still include guild_name (fetched from Discord)
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 150-155) - Tests asserting guild_name in responses
- **Dependencies**:
  - Task 5.1 completion (migration run)

### Task 5.3: Manual testing - verify guild names display correctly

Perform manual testing to verify guild names display correctly in the frontend.

- **Files**:
  - Frontend application (manual testing)
- **Success**:
  - Guild list page displays guild names correctly
  - Guild dashboard displays guild name correctly
  - Guild names are fetched from Discord API (not database)
  - Guild name changes in Discord reflect immediately
- **Research References**:
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 65-75) - API routes fetch pattern
  - #file:../research/20251130-remove-guild-name-from-database-research.md (Lines 92-99) - Frontend usage
- **Dependencies**:
  - Task 5.2 completion (tests passing)

## Dependencies

- Alembic
- SQLAlchemy
- Redis (existing caching infrastructure)
- Discord API (via oauth2.get_user_guilds)

## Success Criteria

- Database migration removes guild_name column successfully
- SQLAlchemy model no longer has guild_name field
- Bot commands do not store guild_name
- API responses still include guild_name (fetched from Discord with caching)
- Frontend displays guild names correctly
- All tests pass
- Guild name changes in Discord reflect immediately (no staleness)
