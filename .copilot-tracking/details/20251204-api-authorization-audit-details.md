<!-- markdownlint-disable-file -->
# Task Details: REST API Authorization Audit and Security Fixes

## Research Reference

**Source Research**: #file:../research/20251204-api-authorization-audit-research.md

## Phase 1: Create Authorization Helper Functions

### Task 1.1: Create require_bot_manager dependency

Create reusable FastAPI dependency for bot manager authorization to eliminate duplicated code across template endpoints.

- **Files**:
  - services/api/dependencies/permissions.py - Add require_bot_manager dependency function
- **Success**:
  - New dependency function similar to require_manage_guild and require_manage_channels
  - Accepts guild_id parameter (extracted from path or resource)
  - Calls RoleVerificationService.check_bot_manager_permission
  - Returns CurrentUser if authorized
  - Raises HTTPException(403) if not authorized
  - Properly typed and documented
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 230-252) - Centralization approach
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 89-102) - Template endpoints with duplicated code
- **Dependencies**:
  - RoleVerificationService from services/api/auth/roles.py
  - Existing require_manage_guild dependency as pattern reference

### Task 1.2: Create verify_guild_membership helper function

Create helper function to verify user is member of a guild, returning appropriate status codes for information disclosure prevention.

- **Files**:
  - services/api/dependencies/permissions.py - Add verify_guild_membership helper function
- **Success**:
  - Accepts user_discord_id, guild_id, access_token
  - Uses Discord OAuth2 API (oauth2.get_user_guilds) to check membership
  - Returns True if user is member, False otherwise
  - Does NOT raise exceptions - lets caller decide on 404 vs 403
  - Caches results for performance
  - Properly typed and documented
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 pattern
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 103-117) - Template visibility issue requiring guild checks
- **Dependencies**:
  - Discord OAuth2 API for guild membership verification

### Task 1.3: Create verify_template_access helper function

Create helper function to verify user can access a template based on guild membership.

- **Files**:
  - services/api/dependencies/permissions.py - Add verify_template_access helper function
- **Success**:
  - Accepts template, user_discord_id, access_token
  - Calls verify_guild_membership to check user is in template's guild
  - Raises HTTPException(404) if user not in guild (prevents information disclosure)
  - Returns template if authorized
  - Properly typed and documented with clear rationale for 404
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 103-117) - Template visibility security issue
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 explanation
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership)
  - Template model with guild_id field

### Task 1.4: Create verify_game_access helper function

Create helper function to verify user can access a game based on guild membership and template player role restrictions.

- **Files**:
  - services/api/dependencies/permissions.py - Add verify_game_access helper function
- **Success**:
  - Accepts game, user_discord_id, access_token, db session
  - Loads game's template with role restrictions
  - Calls verify_guild_membership to check user is in game's guild
  - Raises HTTPException(404) if user not in guild (prevents information disclosure)
  - If template has allowed_player_role_ids, verifies user has required roles
  - Returns game if authorized
  - Properly typed and documented
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 130-139) - Game detail security issue
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 118-129) - Game list filtering issue
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 usage
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership)
  - RoleVerificationService for role checks
  - Template model with allowed_player_role_ids

### Task 1.5: Add unit tests for authorization helpers

Create comprehensive unit tests for all authorization helper functions.

- **Files**:
  - tests/services/api/dependencies/test_permissions.py - Add tests for new helpers
- **Success**:
  - Test require_bot_manager with authorized and unauthorized users
  - Test verify_guild_membership with member and non-member
  - Test verify_template_access returns 404 for non-members
  - Test verify_game_access returns 404 for non-members
  - Test verify_game_access checks player roles when configured
  - Tests use mocked Discord API and RoleVerificationService
  - All edge cases covered
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 230-252) - Helper implementation details
- **Dependencies**:
  - Tasks 1.1-1.4 completion

## Phase 2: Fix Template Authorization Using Helpers

### Task 2.1: Add guild membership check to GET /templates/{template_id}

Fix critical security vulnerability using verify_template_access helper.

- **Files**:
  - services/api/routes/templates.py - Update get_template endpoint
- **Success**:
  - Endpoint fetches template
  - Calls verify_template_access helper (raises 404 if unauthorized)
  - Returns template data if authorized
  - Clean, simple code using helper
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 103-117) - Template visibility security issue
- **Dependencies**:
  - Task 1.3 completion (verify_template_access helper)

### Task 2.2: Refactor template management routes to use require_bot_manager

Replace duplicated bot manager authorization code in 6 template endpoints with the dependency.

- **Files**:
  - services/api/routes/templates.py - Refactor create_template, update_template, delete_template, set_default_template, reorder_templates, list_templates
- **Success**:
  - All 6 endpoints use Depends(require_bot_manager) in function signature
  - Removes 30+ lines of duplicated authorization code
  - Behavior remains identical (tests still pass)
  - Cleaner, more maintainable code
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 230-252) - Centralization approach
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 89-102) - Template endpoints with duplication
- **Dependencies**:
  - Task 1.1 completion (require_bot_manager dependency)

### Task 2.3: Add integration tests for template authorization

Create tests verifying template authorization enforcement.

- **Files**:
  - tests/integration/test_api_authorization.py - New test file for authorization tests
- **Success**:
  - Test verifies guild member can view template
  - Test verifies non-member receives 404 (not 403)
  - Test verifies unauthenticated user receives 401
  - Test verifies bot manager can manage templates
  - Test verifies non-bot-manager receives 403
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 103-117) - Security issue details
- **Dependencies**:
  - Tasks 2.1-2.2 completion

## Phase 3: Fix Game Authorization Using Helpers

### Task 3.1: Fix game list filtering with helper functions

Fix critical security vulnerability where GET /games returns all games regardless of authorization.

- **Files**:
  - services/api/routes/games.py - Update list_games endpoint
  - services/api/services/games.py - Update GameService.list_games
- **Success**:
  - Fetch user's guilds via Discord API
  - Filter games to only those in user's guilds
  - For each game, use verify_game_access helper (catch 404 exceptions)
  - Only return games user is authorized to see
  - No information disclosure about other guilds
  - Clean implementation using helpers
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 118-129) - Game list filtering security issue
- **Dependencies**:
  - Task 1.4 completion (verify_game_access helper)

### Task 3.2: Fix game detail authorization with helper functions

Fix critical security vulnerability using verify_game_access helper.

- **Files**:
  - services/api/routes/games.py - Update get_game endpoint
- **Success**:
  - Endpoint fetches game
  - Calls verify_game_access helper (raises 404 if unauthorized)
  - Returns game data if authorized
  - Clean, simple code using helper
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 130-139) - Game detail security issue
- **Dependencies**:
  - Task 1.4 completion (verify_game_access helper)

### Task 3.3: Fix game join authorization with helper functions

Fix critical security vulnerability where users can join games without proper verification.

- **Files**:
  - services/api/routes/games.py - Update join_game endpoint
- **Success**:
  - Endpoint fetches game
  - Calls verify_guild_membership (raises 404 if not member)
  - Loads template and verifies user has allowed_player_role_ids if configured
  - Returns 403 if user in guild but lacks required roles
  - Proceeds with join logic if authorized
  - Clean implementation using helpers
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 140-151) - Game join authorization issue
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 usage
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership)
  - RoleVerificationService for role checks

### Task 3.4: Add integration tests for game authorization

Create comprehensive tests verifying game authorization enforcement.

- **Files**:
  - tests/integration/test_api_authorization.py - Add game authorization tests
- **Success**:
  - Test game list only returns authorized games
  - Test guild member with proper roles can view game
  - Test non-member receives 404 for game detail
  - Test user with proper roles can join game
  - Test user without proper roles receives 403 for join
  - Test non-member receives 404 for join
  - All authorization paths covered
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 118-151) - Security issues details
- **Dependencies**:
  - Tasks 3.1-3.3 completion

## Phase 4: Information Leak Audit

### Task 4.1: Audit all endpoints for proper 404 vs 403 usage

Systematically review all API endpoints to ensure proper HTTP status codes prevent information disclosure.

- **Files**:
  - services/api/routes/guilds.py - Verify guild endpoints use 404 for non-members
  - services/api/routes/channels.py - Verify channel endpoints use 404 for non-members
  - services/api/routes/export.py - Verify export endpoint uses 404 appropriately
- **Success**:
  - All endpoints return 404 when user is not guild member
  - 403 only used when user is guild member but lacks permissions
  - No information leakage about guild/resource existence
  - Consider using verify_guild_membership helper where appropriate
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 pattern explanation
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 254-260) - Information leak audit approach
- **Dependencies**:
  - Phase 3 completion provides pattern examples

### Task 4.2: Add comprehensive negative authorization tests

Create integration tests verifying users cannot access resources they shouldn't.

- **Files**:
  - tests/integration/test_api_authorization.py - Expand with negative test cases
- **Success**:
  - Tests verify non-members receive 404 for all resource types
  - Tests verify guild members without roles receive 403 (not 404)
  - Tests verify unauthenticated users receive 401
  - Tests cover all major endpoint categories
  - Tests verify no information disclosure
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 254-260) - Information leak audit approach
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Documentation and Prevention

### Task 5.1: Document authorization patterns

Create comprehensive documentation for authorization patterns to guide future development.

- **Files**:
  - .github/instructions/api-authorization.instructions.md - New instruction file
- **Success**:
  - Documents when to use 404 vs 403 with clear examples
  - Explains FastAPI dependency pattern for authorization
  - Provides code examples using helper functions
  - Lists all available authorization dependencies and helpers
  - Explains guild membership verification requirement
  - Covers template and game role restrictions
  - References security rationale
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 153-180) - Authorization architecture
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 pattern
- **Dependencies**:
  - All implementation phases completed

### Task 5.2: Create authorization checklist for new endpoints

Create a checklist template for developers adding new API endpoints.

- **Files**:
  - .github/instructions/api-authorization.instructions.md - Add checklist section
- **Success**:
  - Checklist covers authentication requirements
  - Checklist covers guild membership verification
  - Checklist covers role-based authorization
  - Checklist covers 404 vs 403 usage
  - Checklist mentions available helper functions
  - Checklist covers test requirements
  - Easy to reference during development
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 262-288) - Prevention approach
- **Dependencies**:
  - Task 5.1 completion

## Dependencies

- FastAPI dependency injection framework
- RoleVerificationService for Discord role checks
- Discord OAuth2 API for guild membership verification
- SQLAlchemy for database queries
- pytest for integration tests

## Success Criteria

- Authorization helper functions created and tested
- All 4 critical authorization vulnerabilities fixed using helpers
- Template detail endpoint requires guild membership
- Game list filtered by guild membership and player roles
- Game detail endpoint requires guild membership
- Game join endpoint verifies player roles
- Bot manager authorization centralized in dependency
- All guild endpoints migrated to use helpers
- All channel endpoints migrated to use helpers
- All game management endpoints migrated to use helpers
- All export endpoints migrated to use helpers
- Zero bespoke authorization code remains in route handlers
- All authorization logic centralized in helpers/dependencies
- All endpoints use appropriate HTTP status codes
- Comprehensive authorization tests pass
- Authorization patterns documented
- No duplicated authorization code
- Documentation prohibits inline authorization code

## Phase 4: Migrate All Remaining Endpoints to Use Helpers

### Task 4.1: Audit and migrate guild endpoints

Systematically review all guild endpoints and migrate any bespoke authorization code to use helpers.

- **Files**:
  - services/api/routes/guilds.py - Review all guild endpoints
- **Success**:
  - GET /{guild_id} endpoint uses verify_guild_membership helper to return 404 for non-members
  - GET /{guild_id}/channels endpoint uses verify_guild_membership helper
  - GET /{guild_id}/roles endpoint uses verify_guild_membership helper
  - POST /{guild_id}/validate-mention endpoint uses verify_guild_membership helper
  - No inline authorization code remains in guild route handlers
  - All authorization logic uses helpers or dependencies
  - Tests pass with no behavior changes
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 83-97) - Guild endpoints matrix
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership helper)

### Task 4.2: Audit and migrate channel endpoints

Systematically review all channel endpoints and migrate any bespoke authorization code to use helpers.

- **Files**:
  - services/api/routes/channels.py - Review all channel endpoints
- **Success**:
  - GET /{channel_id} endpoint uses verify_guild_membership helper (fetch channel's guild first)
  - Returns 404 if user not in guild containing the channel
  - No inline authorization code remains in channel route handlers
  - All authorization logic uses helpers or dependencies (require_manage_channels already used)
  - Tests pass with no behavior changes
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 99-108) - Channel endpoints matrix
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership helper)

### Task 4.3: Audit and migrate game management endpoints

Systematically review game update/delete endpoints and migrate to use helpers consistently.

- **Files**:
  - services/api/routes/games.py - Review update_game, delete_game, leave_game endpoints
  - services/api/dependencies/permissions.py - Review can_manage_game, can_export_game helpers
- **Success**:
  - Existing can_manage_game and can_export_game helpers migrated to use verify_guild_membership
  - Both helpers return 404 if user not in guild (not 403)
  - Update/delete endpoints continue using can_manage_game helper
  - Leave endpoint continues using self-service authorization pattern
  - No inline authorization code remains
  - Tests pass with no behavior changes
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 130-151) - Game endpoints with existing helpers
- **Dependencies**:
  - Task 1.2 completion (verify_guild_membership helper)
  - Phases 1-3 completion

### Task 4.4: Audit and migrate export endpoints

Systematically review export endpoints and ensure they use helpers consistently.

- **Files**:
  - services/api/routes/export.py - Review export endpoints
- **Success**:
  - Export endpoint uses can_export_game helper (already correct)
  - Verify can_export_game returns 404 for non-guild-members
  - No inline authorization code remains
  - Tests pass with no behavior changes
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 144-151) - Export endpoint analysis
- **Dependencies**:
  - Task 4.3 completion (can_export_game helper updated)

### Task 4.5: Verify no bespoke auth code remains in route handlers

Perform final audit to ensure all authorization code uses helpers or dependencies.

- **Files**:
  - services/api/routes/*.py - All route files
- **Success**:
  - Search all route files for direct RoleVerificationService calls (should only be in helpers)
  - Search for direct Discord API calls for guild membership (should only be in helpers)
  - Search for inline permission checks (should use dependencies or helpers)
  - Document any remaining bespoke code with clear justification
  - Generate report of authorization patterns used across all endpoints
  - All endpoints use consistent authorization approach
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 153-180) - Authorization architecture
- **Dependencies**:
  - Tasks 4.1-4.4 completion

## Phase 5: Information Leak Audit

### Task 5.1: Audit all endpoints for proper 404 vs 403 usage

Verify all endpoints using helpers properly return 404 for non-guild-members.

- **Files**:
  - All route files - Verify error response patterns
- **Success**:
  - All endpoints return 404 when user is not guild member
  - 403 only used when user is guild member but lacks permissions
  - No information leakage about guild/resource existence
  - Helper functions consistently implement 404 pattern
  - Document any exceptions with clear justification
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 pattern explanation
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Add comprehensive negative authorization tests

Create integration tests verifying users cannot access resources they shouldn't.

- **Files**:
  - tests/integration/test_api_authorization.py - Expand with negative test cases for all endpoints
- **Success**:
  - Tests verify non-members receive 404 for all resource types
  - Tests verify guild members without roles receive 403 (not 404)
  - Tests verify unauthenticated users receive 401
  - Tests cover all endpoint categories (guilds, channels, templates, games, export)
  - Tests verify no information disclosure
  - Tests verify helpers are being used correctly
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 254-260) - Information leak audit approach
- **Dependencies**:
  - Task 5.1 completion

## Phase 6: Documentation and Prevention

### Task 6.1: Document authorization patterns

Create comprehensive documentation for authorization patterns to guide future development.

- **Files**:
  - .github/instructions/api-authorization.instructions.md - New instruction file
- **Success**:
  - Documents when to use 404 vs 403 with clear examples
  - Explains FastAPI dependency pattern for authorization
  - Provides code examples using helper functions
  - Lists all available authorization dependencies and helpers
  - Explains guild membership verification requirement
  - Covers template and game role restrictions
  - References security rationale
  - Mandates use of helpers for all new endpoints
  - Prohibits inline authorization code in route handlers
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 153-180) - Authorization architecture
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 316-326) - 404 vs 403 pattern
- **Dependencies**:
  - All implementation phases completed

### Task 6.2: Create authorization checklist for new endpoints

Create a checklist template for developers adding new API endpoints.

- **Files**:
  - .github/instructions/api-authorization.instructions.md - Add checklist section
- **Success**:
  - Checklist covers authentication requirements
  - Checklist covers guild membership verification
  - Checklist covers role-based authorization
  - Checklist covers 404 vs 403 usage
  - Checklist mandates use of helper functions (no inline code)
  - Checklist covers test requirements (positive and negative cases)
  - Easy to reference during development
- **Research References**:
  - #file:../research/20251204-api-authorization-audit-research.md (Lines 262-288) - Prevention approach
- **Dependencies**:
  - Task 6.1 completion
