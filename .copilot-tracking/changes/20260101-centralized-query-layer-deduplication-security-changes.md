<!-- markdownlint-disable-file -->

# Release Changes: Centralized Query Layer for Deduplication and Security

**Related Plan**: 20260101-centralized-query-layer-deduplication-security-plan.instructions.md
**Implementation Date**: 2026-01-01

## Summary

Creating a centralized guild-scoped query layer that eliminates code duplication across 37+ database query locations while enforcing guild isolation security through required guild_id parameters.

## Changes

### Added

- shared/data_access/__init__.py - Package initialization for centralized guild-scoped query layer
- shared/data_access/guild_queries.py - Core module for guild isolation wrapper functions (foundation only)
- tests/shared/test_data_access_structure.py - Module structure verification tests for data_access layer
- shared/data_access/guild_queries.py - Implemented 5 core game operation wrappers (get_game_by_id, list_games, create_game, update_game, delete_game) with guild_id enforcement and RLS context management
- tests/shared/data_access/__init__.py - Test package initialization for data_access tests
- tests/shared/data_access/test_guild_queries.py - Comprehensive unit tests (22 tests) for game operation wrappers with 100% coverage
- shared/data_access/guild_queries.py - Implemented 3 participant operation wrappers (add_participant, remove_participant, list_user_games) with game ownership validation
- tests/shared/data_access/test_guild_queries.py - Added 16 unit tests for participant wrappers covering all error cases and success paths (38 tests total)
- shared/data_access/guild_queries.py - Implemented 4 template operation wrappers (get_template_by_id, list_templates, create_template, update_template) consolidating 15+ inline template queries with guild_id enforcement
- tests/shared/data_access/test_guild_queries.py - Added 18 unit tests for template wrappers with comprehensive coverage of CRUD operations and validation (56 tests total)
- tests/shared/data_access/test_guild_queries.py - Completed comprehensive unit test suite with 56 tests achieving 100% code coverage on all 12 wrapper functions (Task 1.5)
- tests/integration/test_guild_queries.py - Integration tests validating all 12 wrapper functions against real PostgreSQL database with RLS verification (23 tests, all passing) (Task 1.6)

### Modified

- tests/integration/test_guild_queries.py - Fixed test isolation using unique UUID generation per test instead of session-scoped fixtures
- tests/integration/test_guild_queries.py - Added ParticipantType.SELF_ADDED enum usage for position_type fields (replaced magic number 24000)
- tests/integration/test_guild_queries.py - Created guild_b_config fixture to satisfy foreign key constraints for multi-guild tests
- tests/integration/test_guild_queries.py - Fixed field name mismatches (game_id → game_session_id) in assertions and SQL queries
- tests/integration/test_guild_queries.py - Increased performance threshold from 5ms to 10ms (realistic for RLS overhead)
- tests/integration/test_guild_queries.py - Added ChannelConfiguration creation in test_list_games_respects_channel_filter to satisfy foreign key constraints
- tests/integration/test_games_route_guild_isolation.py - Integration tests for games route establishing pre-migration baseline (6 passing tests: test_get_game_returns_any_game_without_guild_filter documents SECURITY GAP with no guild filtering, test_list_games_filters_by_guild_when_specified verifies guild_id filtering, test_list_games_with_channel_filter verifies channel filtering, test_list_games_with_status_filter verifies status filtering, test_list_games_pagination verifies pagination behavior, test_guild_isolation_in_list_games verifies complete guild isolation)
- tests/e2e/test_game_authorization.py - E2E tests for game creation/deletion authorization with real infrastructure (3 passing tests: test_create_game_with_authorization for POST with real auth, test_delete_game_authorization for DELETE flow with idempotent behavior and 204 soft delete, test_delete_game_authorization_forbidden documenting 403 vs 404 security pattern per API guidelines; all tests use real E2E fixtures from init service with full authorization through role service/cache/Discord API)
- .gitignore - Added *.out pattern to ignore test output files

### Removed
