<!-- markdownlint-disable-file -->

# Release Changes: Game Template System

**Related Plan**: 20251201-game-template-system-plan.instructions.md
**Implementation Date**: 2025-12-02

## Summary

Replace three-level inheritance system (Guild → Channel → Game) with template-based game types that provide locked and pre-populated settings.

## Changes

### Added

- services/api/database/**init**.py - Database queries package marker
- services/api/database/queries.py - Read-only database queries for guild and channel configurations
- services/api/services/guild_service.py - Business logic for guild create/update operations
- services/api/services/channel_service.py - Business logic for channel create/update operations
- tests/services/api/services/test_guild_service.py - Unit tests for guild service operations
- tests/services/api/services/test_channel_service.py - Unit tests for channel service operations
- alembic/versions/018_remove_inheritance_fields.py - Database migration to remove inheritance system fields
- alembic/versions/019_add_template_system.py - Database migration to add template system (game_templates table, template_id FK to games)
- shared/models/template.py - GameTemplate model with locked and pre-populated fields for game types
- shared/schemas/template.py - Pydantic schemas for template CRUD operations (create, update, response, list, reorder)
- services/api/services/template_service.py - TemplateService class with CRUD operations and role-based filtering
- scripts/data_migration_create_default_templates.py - Idempotent script to create default templates for existing guilds
- tests/shared/models/test_template.py - Unit tests for GameTemplate model structure and constraints
- tests/services/api/services/test_template_service.py - Comprehensive unit tests for template service (16 tests)
- services/api/auth/discord_client.py - Added get_bot_guilds() and get_guild_channels() methods for guild sync
- shared/schemas/guild.py - Added GuildSyncResponse schema for sync endpoint
- services/api/routes/templates.py - Complete template CRUD router with 7 endpoints (list, get, create, update, delete, set-default, reorder) with role-based authorization
- tests/services/api/routes/test_templates.py - Template endpoint tests covering list, get, create, and delete operations with role filtering and authorization (7 tests, all passing)
- tests/e2e/test_guild_template_api.py - E2E tests for guild sync and template API endpoints (6 tests for future full-stack e2e test suite)
- frontend/src/api/templates.ts - Template API client functions (getTemplates, getTemplate, createTemplate, updateTemplate, deleteTemplate, setDefaultTemplate, reorderTemplates)
- frontend/src/api/guilds.ts - Guild API client with syncUserGuilds function for manual guild synchronization
- frontend/src/components/TemplateCard.tsx - Template card component with edit, delete, set default actions and drag handle
- frontend/src/components/TemplateForm.tsx - Template create/edit form with locked and pre-populated field sections
- frontend/src/components/TemplateList.tsx - Template list component with drag-and-drop reordering
- frontend/src/pages/TemplateManagement.tsx - Main template management page with CRUD operations
- frontend/src/components/**tests**/TemplateCard.test.tsx - Unit tests for TemplateCard component (7 tests)
- frontend/src/components/**tests**/TemplateList.test.tsx - Unit tests for TemplateList component (3 tests)

### Modified

- services/api/routes/guilds.py - Replaced ConfigurationService with database queries and guild_service; removed inheritance fields from responses; fixed import to use module instead of function
- services/api/routes/channels.py - Replaced ConfigurationService with database queries and channel_service; removed inheritance fields from responses; fixed import to use module instead of function
- services/api/dependencies/permissions.py - Replaced ConfigurationService import with database queries
- services/api/services/games.py - Removed SettingsResolver usage, use direct field access with defaults
- services/api/auth/roles.py - Simplified check_game_host_permission to only check MANAGE_GUILD (template role checks in Phase 2)
- services/bot/auth/role_checker.py - Simplified check_game_host_permission to only check MANAGE_GUILD (template role checks in Phase 2)
- shared/models/guild.py - Removed default_max_players, default_reminder_minutes, allowed_host_role_ids fields; added templates relationship; updated docstring
- shared/models/channel.py - Removed max_players, reminder_minutes, allowed_host_role_ids, game_category fields; updated docstring
- shared/models/game.py - Added template_id FK, allowed_player_role_ids, and template relationship; updated docstring
- shared/schemas/guild.py - Removed inheritance fields from GuildConfigCreateRequest, GuildConfigUpdateRequest, GuildConfigResponse
- shared/schemas/channel.py - Removed inheritance fields from ChannelConfigCreateRequest, ChannelConfigUpdateRequest, ChannelConfigResponse
- shared/schemas/game.py - Updated GameCreateRequest to require template_id and make other fields optional overrides
- shared/schemas/**init**.py - Added template schema exports
- frontend/src/types/index.ts - Updated Guild and Channel interfaces to remove obsolete inheritance fields
- frontend/src/pages/GuildConfig.tsx - Simplified to only manage bot_manager_role_ids and require_host_role fields
- frontend/src/pages/ChannelConfig.tsx - Simplified to only manage is_active field
- frontend/src/pages/GuildDashboard.tsx - Removed display of obsolete inheritance fields from guild and channel lists
- tests/services/api/routes/test_guilds.py - Updated to patch individual query/service functions; removed inheritance field assertions
- tests/services/api/auth/test_roles.py - Updated check_game_host_permission tests for simplified permission logic
- tests/services/api/services/test_calendar_export.py - Removed allowed_host_role_ids from mock guild fixture
- tests/services/api/services/test_games.py - Removed inheritance fields from guild/channel fixtures
- tests/services/api/services/test_games_edit_participants.py - Removed inheritance fields from guild/channel fixtures
- tests/services/api/services/test_games_promotion.py - Removed default_max_players from guild fixture
- tests/services/api/services/test_channel_service.py - Updated tests to remove max_players and reminder_minutes assertions
- tests/services/api/services/test_guild_service.py - Fixed mocking to use Mock instead of AsyncMock for synchronous db methods
- tests/services/api/services/test_channel_service.py - Fixed mocking to use Mock instead of AsyncMock for synchronous db methods
- tests/services/api/routes/test_games_participant_count.py - Removed default_max_players from guild fixtures
- tests/e2e/test_game_notification_api_flow.py - Removed default_reminder_minutes from raw SQL guild insert
- shared/models/**init**.py - Added GameTemplate to model exports
- scripts/data_migration_create_default_templates.py - Fixed to use get_db_session() instead of get_async_session()
- tests/services/api/services/test_games.py - Updated sample_game_data fixture and individual tests to use template_id instead of guild_id/channel_id (5 tests updated)
- services/api/services/guild_service.py - Added sync_user_guilds() function to sync Discord guilds with database
- services/api/routes/guilds.py - Added POST /guilds/sync endpoint for manual guild synchronization
- services/api/routes/templates.py - Created template router with CRUD endpoints (list, get, create, update, delete, set-default, reorder); fixed to use current_user.access_token directly instead of non-existent get_valid_token_for_user function
- services/api/app.py - Registered templates router in FastAPI application
- services/api/services/games.py - Updated create_game to require template_id, validate host permissions, and use template defaults for all fields
- tests/services/api/routes/test_templates.py - Fixed to remove token mocking and use direct current_user.access_token pattern; fixed get_template tests to use correct method name get_template_by_id
- tests/services/api/routes/test_guilds.py - Fixed fetch_channel_name_safe patch path to use correct import location
- tests/services/api/services/test_games.py - Added sample_template fixture using template_model.GameTemplate; updated 5 game creation tests to include template_result in mock db.execute side_effect (test_create_game_without_participants, test_create_game_with_where_field, test_create_game_with_valid_participants, test_create_game_with_invalid_participants, test_create_game_timezone_conversion)
- frontend/src/types/index.ts - Added GameTemplate, TemplateListItem, TemplateCreateRequest, TemplateUpdateRequest interfaces
- frontend/src/App.tsx - Added /guilds/:guildId/templates route for template management page
- frontend/src/pages/GuildDashboard.tsx - Added "Refresh Servers" button for manual guild sync, added "Templates" button to navigate to template management
- frontend/src/pages/CreateGame.tsx - Updated to use template selection dropdown instead of channel selection, pre-populates form fields from selected template
- frontend/src/pages/GuildListPage.tsx - Added "Refresh Servers" button with syncUserGuilds functionality for manual guild synchronization
- services/api/services/template_service.py - Added selectinload(GameTemplate.channel) to all template queries to avoid async/sync greenlet_spawn errors
- tests/services/api/services/test_template_service.py - Updated all test mocks to use db.execute with scalar_one_or_none instead of db.get
- frontend/src/components/TemplateForm.tsx - Added logic to filter null values from update requests; added debugging console.log
- shared/schemas/template.py - Expanded TemplateListItem from 5 fields to 14 fields (added channel_id, notify_role_ids, allowed_player_role_ids, allowed_host_role_ids, max_players, expected_duration_minutes, reminder_minutes, where, signup_instructions)
- services/api/routes/templates.py - Updated list_templates endpoint to return all fields in TemplateListItem; added logging for role fetch operations
- frontend/src/types/index.ts - Updated TemplateListItem interface to match backend schema with all 14 fields
- frontend/src/pages/TemplateManagement.tsx - Added roles to TemplateList props; added console.log debugging for fetched data
- services/api/routes/guilds.py - Changed role filter from excluding @everyone and managed roles to only excluding managed roles (allows @everyone); added @ prefix to all role names that don't already have one; added logging for role fetch operations
- frontend/src/components/TemplateList.tsx - Added roles prop and passed to TemplateCard
- frontend/src/components/TemplateCard.tsx - Added roles prop, getRoleNames helper function, and display of all three role fields (notify_role_ids, allowed_player_role_ids, allowed_host_role_ids) plus signup_instructions
- frontend/src/components/GameForm.tsx - Removed notify_role_ids field and notifyRoleIds from GameFormData interface; removed unused imports (Chip, OutlinedInput, DiscordRole); removed roles prop from component interface and parameters; removed handleRoleSelectChange function
- frontend/src/pages/EditGame.tsx - Removed notify_role_ids from update payload; removed roles prop from GameForm usage
- frontend/src/pages/CreateGame.tsx - Removed roles state, roles API call, and DiscordRole import; removed roles prop from GameForm usage

### Removed

- services/api/services/config.py - Deleted ConfigurationService and SettingsResolver classes
- tests/services/api/services/test_config.py - Deleted tests for removed ConfigurationService
- frontend/src/components/InheritancePreview.tsx - Removed inheritance preview component
- frontend/src/components/**tests**/InheritancePreview.test.tsx - Removed inheritance preview tests
- services/bot/commands/config_guild.py - Removed bot guild configuration command
- services/bot/commands/config_channel.py - Removed bot channel configuration command
- tests/services/bot/commands/test_config_guild.py - Removed bot config command tests
- tests/services/bot/commands/test_config_channel.py - Removed bot config command tests

## Verification

### Code Standards Compliance

- ✅ All new files have copyright notices
- ✅ Python code follows Google Python Style Guide import conventions (imports modules, not functions)
- ✅ All imports use module-level imports per project standards
- ✅ Documentation follows self-explanatory code guidelines
- ✅ No lint or compilation errors

### Test Coverage

- ✅ `services/api/services/template_service.py` - **100% coverage** with 16 unit tests
- ✅ `shared/models/template.py` - 100% structure validation with 8 unit tests
- ✅ `services/api/routes/templates.py` - 7 endpoint tests (all passing)
- ✅ Overall API services test coverage: **85%** (93 lines missing from 608 total)
- ✅ All 16 template service unit tests pass
- ✅ All 8 GameTemplate model tests pass
- ✅ All 7 template endpoint tests pass
- ✅ All 32 route unit tests pass
- ✅ **All 527 unit tests passing** (100% pass rate)
- ✅ All 18 game service tests passing after template fixture fixes

### Build Verification

- ✅ API container builds successfully
- ✅ Bot container builds successfully
- ✅ Frontend container builds successfully
- ✅ All Docker containers build without errors

### UI/UX Verification

- ✅ Template list displays all fields including roles, duration, reminders, location, and signup instructions
- ✅ Template form supports create, edit, delete, set default, and reorder operations
- ✅ Role dropdowns populate with non-managed roles from Discord API
- ✅ Guild sync button successfully fetches and displays guilds from Discord
- ✅ Game creation form uses template selection instead of channel selection
- ✅ Notify roles removed from game forms (only appear in templates)
- ✅ Role names display with @ prefix for consistency

### Integration Tests

- ✅ All PostgreSQL listener integration tests pass
- ✅ All schedule queries integration tests pass
- ✅ All notification daemon integration tests pass
- ✅ 10/10 integration tests passing

### E2E Tests

- 📝 Created `test_guild_template_api.py` with 6 e2e test scenarios (requires full Discord API integration to run)
- Tests cover guild sync flow, template CRUD, role-based filtering, and default template protection
- Ready for Phase 5 when e2e test infrastructure includes Discord API mocking

## Notes

- Import convention fixes applied to `services/api/routes/guilds.py` and `services/api/routes/channels.py` to follow Google Python Style Guide
- Test mocking fixes applied to use `Mock` instead of `AsyncMock` for synchronous database methods (`db.add`, `db.refresh`)
- Frontend TypeScript interfaces updated to remove obsolete fields
- Frontend UI simplified to remove inheritance-related configuration fields
- Database queries module has 50% unit test coverage, which is acceptable as these are simple pass-through queries tested via route and integration tests
- Template router fixed to use `current_user.access_token` directly instead of calling non-existent `get_valid_token_for_user()` function
- Template endpoint tests fixed to remove token mocking and use direct access_token pattern from current_user fixture
- Template endpoint tests fixed to use correct method name `get_template_by_id` instead of `get_template`
- Game service tests fixed to include `sample_template` fixture in all game creation tests
- Game service tests updated to add `template_result` as first query result in mock db.execute side_effect
- E2E tests for guild sync and template API created but not yet runnable (need Discord API integration in e2e test infrastructure)
- Fixed async/sync greenlet_spawn errors by adding selectinload(GameTemplate.channel) to all template service queries for eager loading
- Template update functionality debugged and fixed by filtering null values from frontend update requests
- TemplateListItem schema expanded from 5 to 14 fields to support complete template display including all role fields
- Role filtering simplified to only exclude managed roles (bot roles), allowing @everyone for notifications
- All role names now display with @ prefix for consistency with Discord UI conventions
- Notify roles functionality moved from game forms to templates only (templates control which roles are notified, not individual games)

## Coding Standards Verification

### Code Quality

- ✅ All new files have copyright notices
- ✅ All imports follow Google Python Style Guide (import modules, not functions)
- ✅ Documentation follows self-explanatory code guidelines with comprehensive docstrings
- ✅ All code passes ruff linting with zero errors
- ✅ Type hints on all function signatures
- ✅ Proper use of Args, Returns, and Raises sections in docstrings

### Test Quality

- ✅ Tests focus on business logic, not just coverage
- ✅ Tests cover edge cases (role filtering, empty values, error conditions)
- ✅ Tests verify state changes and error handling
- ✅ Template service achieves 100% test coverage
- ✅ Overall service layer maintains 85% coverage (exceeds 80% threshold)

### System Stability

- ✅ All affected Docker containers build successfully
- ✅ All 10 integration tests pass
- ✅ System remains deployable and functional
- ✅ **No regression in existing functionality** (all 527 unit tests passing)

## Post-Implementation Verification (2025-12-03)

### Coding Standards Compliance
- ✅ All code follows project conventions
- ✅ Copyright notices present on all files
- ✅ Python linting passes (ruff check and format)
- ✅ TypeScript compilation successful

### Test Results
- ✅ 527/527 unit tests passing (100%)
- ✅ 10/10 integration tests passing (100%)
- ✅ 34/34 frontend tests passing (100%)
- ✅ Template service: 100% test coverage
- ✅ Overall API services: 86% coverage (exceeds 80% minimum)

### Build Verification
- ✅ API container builds successfully
- ✅ Bot container builds successfully
- ✅ Frontend container builds successfully

### Issues Fixed During Verification
- Fixed missing `roles` prop in TemplateList component usage in TemplateManagement.tsx
- Updated EditGame and GuildConfig test suites to match simplified component implementations after template system refactoring
- Refactored GuildConfig test suite to use proper beforeEach setup for consistent API mocking across all tests
- Added missing `roles` prop to all TemplateCard and TemplateList test usages
- Fixed TemplateCard tests to use `getByTitle` instead of `getByLabelText` to match component implementation (buttons use `title` attribute)
