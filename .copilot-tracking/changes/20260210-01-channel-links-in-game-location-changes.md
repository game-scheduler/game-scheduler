<!-- markdownlint-disable-file -->

# Release Changes: Discord Channel Links in Game Location Field

**Related Plan**: 20260210-01-channel-links-in-game-location-plan.instructions.md
**Implementation Date**: 2026-02-10

## Summary

Enable users to reference Discord channels in game location field using `#channel-name` format, with backend validation that converts mentions to clickable Discord channel links (`<#channel_id>`) in game announcements.

## Changes

### Added

- services/api/services/channel_resolver.py - Created ChannelResolver service stub with resolve_channel_mentions method raising NotImplementedError
- tests/services/api/services/test_channel_resolver.py - Created comprehensive unit tests testing actual desired behavior (7 test cases: single match returns `<#id>` format, disambiguation returns errors with suggestions, not found returns errors with suggestions, special characters work, mixed content resolves, empty text handled, plain text unchanged) - Tests properly fail with NotImplementedError (TDD RED phase)

### Modified

- services/api/services/channel_resolver.py - Implemented resolve_channel_mentions with regex pattern r'#([\w-]+)', Discord API channel lookup, single match conversion to <#id>, multiple match disambiguation errors, not found errors with fuzzy suggestions (TDD GREEN phase - all tests passing). Fixed line length formatting (E501).
- tests/services/api/services/test_channel_resolver.py - Added 8 edge case tests: multiple mentions in one location, channel at text start/end, adjacent mentions, empty guild channel list, filtering non-text channels, case-insensitive matching, mixed valid/invalid channels. Total 15 tests, 100% code coverage.
- services/api/services/games.py - Added ChannelResolver import and parameter to GameService.**init**, added channel_resolver field initialization, integrated channel mention resolution in create_game method (after resolving template fields, before participant resolution) with ValidationError raised for invalid channel mentions
- services/api/routes/games.py - Added channel_resolver_module import, instantiated ChannelResolver in get_game_service dependency and passed to GameService
- tests/services/api/services/conftest.py - Added channel_resolver_module import, created mock_channel_resolver fixture (AsyncMock of ChannelResolver), updated game_service fixture to include mock_channel_resolver parameter
- tests/integration/test_games_route_guild_isolation.py - Updated 6 GameService instantiations to include channel_resolver=MagicMock() parameter
- tests/integration/services/api/services/test_game_image_integration.py - Updated 6 GameService instantiations to include channel_resolver=MagicMock() parameter
- tests/services/api/services/test_games.py - Added 4 integration tests for channel resolution: test_create_game_with_valid_channel_mention (verifies <#id> format in database), test_create_game_with_invalid_channel_raises_validation_error (verifies ValidationError with suggestions), test_create_game_with_ambiguous_channel_raises_validation_error (verifies disambiguation error), test_create_game_with_plain_text_location_unchanged (verifies backward compatibility). Updated test_create_game_with_where_field to include mock_channel_resolver parameter and setup.

**Note on Task 2.3**: No code changes needed. ValidationError from ChannelResolver is already handled by existing \_handle_game_operation_errors function in services/api/routes/games.py (returns HTTP 422 with invalid_mentions field). Existing tests verify error propagation works correctly.

- frontend/src/components/ChannelValidationErrors.tsx - Created ChannelValidationErrors component displaying channel validation errors with type/input/reason/suggestions structure, clickable Chip suggestions for channel names
- frontend/src/components/**tests**/ChannelValidationErrors.test.tsx - Created comprehensive unit tests for ChannelValidationErrors component (8 test cases: renders alert title, displays error details, shows suggestions, renders chips, handles clicks, multiple errors, no suggestions case, clickable chips, 100% code coverage)
- frontend/src/components/GameForm.tsx - Added ChannelValidationErrors import, added channelValidationErrors and onChannelValidationErrorClick props to GameFormProps interface, added component destructuring parameters, added ChannelValidationErrors display after ValidationErrors component, updated getLocationHelperText function to display "Location of the game. Type #channel-name to link to a Discord channel" when field is empty, maintaining character count display when text is present
- frontend/src/pages/CreateGame.tsx - Added ChannelValidationError interface with type/input/reason/suggestions fields, added channelValidationErrors state, updated invalid_mentions error handling to separate participant and channel errors based on 'type' field presence, added handleChannelSuggestionClick function, passed channelValidationErrors and onChannelValidationErrorClick props to GameForm, fixed early return condition to check both validationErrors and channelValidationErrors before hiding form
- frontend/src/pages/**tests**/CreateGame.test.tsx - Added test 'handles channel validation errors from API' that mocks UNPROCESSABLE_ENTITY response with channel validation errors, verifies ChannelValidationErrors component displays with correct error details and suggestion chips
- tests/e2e/test_game_announcement.py - Added plain text location "Local Game Store, 123 Main St" to game creation, updated embed verification to include expected_location parameter, updated docstring to document backward compatibility verification (Task 4.2: verifies plain text locations work unchanged in Discord embeds)
- tests/e2e/test_channel_mentions.py - Created E2E test for channel mention resolution (Task 4.1): fetches guild channels via REST API, creates game with location containing #channel-name, verifies Discord embed Where field contains <#channel_id> format, confirms channel ID matches actual guild channel, validates text preservation around mention

### Removed
