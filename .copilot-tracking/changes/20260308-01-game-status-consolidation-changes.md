<!-- markdownlint-disable-file -->

# Release Changes: GameStatus Enum Consolidation

**Related Plan**: 20260308-01-game-status-consolidation.plan.md
**Implementation Date**: 2026-03-11

## Summary

Consolidate GameStatus into a single canonical enum in status_transitions and update imports.

## Changes

### Added

- tests/unit/shared/utils/test_status_transitions.py - added xfail unit tests for GameStatus display_name values.

### Modified

- shared/utils/status_transitions.py - added a display_name property stub on GameStatus that raises NotImplementedError.
- shared/utils/status_transitions.py - implemented display_name mapping for all GameStatus values.
- tests/unit/shared/utils/test_status_transitions.py - removed xfail markers after display_name implementation.
- shared/models/game.py - replaced the local GameStatus enum with an import from shared.utils.status_transitions.
- services/bot/formatters/game_message.py - updated GameStatus import to use shared.models.
- tests/integration/test_clone_game_endpoint.py - updated GameStatus import to use shared.models.
- tests/integration/test_games_route_guild_isolation.py - updated GameStatus import to use shared.models.
- tests/e2e/test_game_status_transitions.py - updated GameStatus import to use shared.models.
- tests/services/scheduler/test_event_builders.py - updated GameStatus import to use shared.models.
- tests/services/bot/events/test_handlers.py - updated GameStatus import to use shared.models.
- tests/unit/bot/handlers/test_participant_drop_handler.py - updated GameStatus import to use shared.models.

### Removed

- None.

## Release Summary

**Total Files Affected**: 12

### Files Created (1)

- tests/unit/shared/utils/test_status_transitions.py - added unit coverage for GameStatus display_name values.

### Files Modified (11)

- .copilot-tracking/changes/20260308-01-game-status-consolidation-changes.md - tracked implementation progress and release summary.
- .copilot-tracking/plans/20260308-01-game-status-consolidation.plan.md - updated task and phase completion status.
- shared/models/game.py - switched GameStatus to import from shared.utils.status_transitions.
- shared/utils/status_transitions.py - added display_name property for canonical GameStatus.
- services/bot/formatters/game_message.py - updated GameStatus import to shared.models.
- tests/integration/test_clone_game_endpoint.py - updated GameStatus import to shared.models.
- tests/integration/test_games_route_guild_isolation.py - updated GameStatus import to shared.models.
- tests/e2e/test_game_status_transitions.py - updated GameStatus import to shared.models.
- tests/services/scheduler/test_event_builders.py - updated GameStatus import to shared.models.
- tests/services/bot/events/test_handlers.py - updated GameStatus import to shared.models.
- tests/unit/bot/handlers/test_participant_drop_handler.py - updated GameStatus import to shared.models.

### Files Removed (0)

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: None.
- **Configuration Updates**: None.

### Deployment Notes

None.
