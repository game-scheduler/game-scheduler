<!-- markdownlint-disable-file -->

# Release Changes: Multiple Signup Methods

**Related Plan**: 20251226-multiple-signup-methods-plan.instructions.md
**Implementation Date**: 2025-12-27

## Summary

Adding support for multiple signup methods (Self Signup and Host Selected) with template-level configuration controlling which methods are available and the default selection.

## Changes

### Added

- shared/models/signup_method.py - SignupMethod enum with SELF_SIGNUP and HOST_SELECTED values, display_name and description properties
- alembic/versions/b49eb343d5a6_add_signup_methods.py - Database migration adding signup method fields with SELF_SIGNUP backfill
- tests/e2e/test_signup_methods.py - E2E tests for Discord button behavior (5 tests, all passing): SELF_SIGNUP enabled button, HOST_SELECTED disabled button, default SELF_SIGNUP behavior with state persistence verification, edit SELF_SIGNUP to HOST_SELECTED with button state update, edit HOST_SELECTED to SELF_SIGNUP with button state update

### Modified

- shared/models/__init__.py - Exported SignupMethod enum
- shared/models/template.py - Added allowed_signup_methods and default_signup_method fields to GameTemplate
- shared/models/game.py - Added signup_method field to GameSession with SELF_SIGNUP default
- shared/schemas/game.py - Added signup_method field to GameCreateRequest with validation and GameResponse
- shared/schemas/template.py - Added allowed_signup_methods and default_signup_method fields to all template schemas
- services/api/services/games.py - Added signup method resolution and validation logic in create_game method
- services/bot/views/game_view.py - Added signup_method parameter to GameView and updated join button disabled logic
- services/bot/formatters/game_message.py - Added signup_method parameter to format_game_announcement function and passed to GameView
- services/bot/events/handlers.py - Updated _create_game_announcement to pass game.signup_method to format_game_announcement
- tests/services/bot/formatters/test_game_message.py - Added signup_method parameter to all format_game_announcement test calls
- frontend/src/types/index.ts - Added SignupMethod enum, SIGNUP_METHOD_INFO constant, signup_method to GameSession, allowed_signup_methods and default_signup_method to GameTemplate and related interfaces
- frontend/src/components/GameForm.tsx - Added signupMethod to GameFormData, allowedSignupMethods and defaultSignupMethod props, signup method selector dropdown with template-driven defaults
- frontend/src/pages/CreateGame.tsx - Added signup_method to payload submission, passed allowedSignupMethods and defaultSignupMethod from template to GameForm
- frontend/src/pages/GameDetails.tsx - Added signup method display in game details metadata section with formatted display name
- tests/shared/models/test_signup_method.py - Unit tests for SignupMethod enum (7 tests): values, members, display_name, description, string usage, comparisons, dict storage
- tests/shared/models/test_template.py - Unit tests for GameTemplate signup method fields (5 tests): column existence, nullability, JSON/string types, field instantiation
- tests/shared/models/test_game_session.py - Unit tests for GameSession signup_method field (3 tests): column existence, not nullable with default, string type
- tests/services/api/services/test_games.py - Unit tests for game creation signup method logic (6 tests): explicit method, template default, SELF_SIGNUP fallback, validation against allowed list, null/empty list acceptance
- tests/services/bot/views/test_game_view.py - Unit tests for GameView signup method behavior (5 tests): SELF_SIGNUP enables button, HOST_SELECTED disables button, method overrides other states, from_game_data handling
- frontend/src/components/__tests__/GameForm.test.tsx - Frontend unit tests for signup method selector (8 tests): default SELF_SIGNUP, template default, disabled when one method, enabled when multiple, edit mode preservation, description display, description updates, form data inclusion
- tests/shared/auth_helpers.py - Shared authentication helpers for creating test sessions with encrypted tokens in Redis (extracted from e2e conftest for reusability)
- tests/e2e/conftest.py - Refactored authenticated_admin_client fixture to use shared auth helpers
- tests/integration/test_game_signup_methods.py - Integration tests for HTTP API → Database → RabbitMQ flow (3 tests): explicit signup method with message verification, template default with message verification, HOST_SELECTED with initial_participants feature interaction
- alembic/versions/b49eb343d5a6_add_signup_methods.py - Added server_default="SELF_SIGNUP" to signup_method column
- shared/models/game.py - Added server_default to signup_method field in GameSession model
- compose.int.yaml - Added JWT_SECRET environment variable to integration-tests service, added API as dependency of system-ready
- config/env.int - Added fake DISCORD_BOT_TOKEN with correct format for integration tests
- services/api/routes/games.py - Added signup_method Form parameter to create_game endpoint, added to GameCreateRequest, added signup_method to GameResponse in _build_game_response
- services/api/services/games.py - Pass signup_method to GameCreatedEvent
- shared/messaging/events.py - Added signup_method field to GameCreatedEvent
- shared/schemas/game.py - Added signup_method field to GameUpdateRequest to support editing
- services/api/routes/games.py - Added signup_method Form parameter to update_game endpoint
- services/api/services/games.py - Added signup_method handling in _update_game_fields method, included signup_method in GameUpdatedEvent
- shared/messaging/events.py - Added signup_method field to GameUpdatedEvent
- frontend/src/pages/EditGame.tsx - Added signup_method to update payload in handleSubmit
- tests/services/api/services/test_games.py - Fixed 6 test cases by adding signup_method="SELF_SIGNUP" to mock GameSession objects
- services/bot/events/handlers.py - Updated _update_game_announcement to retrieve and pass signup_method to format_game_announcement for proper button state on edit

### Removed
