# Changes: Coverage Infrastructure Fix and Gap Analysis Update

## Summary

Fix hidden coverage file bug and add unit tests for coverage gaps.

## Added

- `tests/unit/bot/events/__init__.py` — package init for bot events unit tests
- `tests/unit/bot/events/test_handlers_game_events.py` — unit tests for `_handle_game_created` and `_handle_game_updated` error/branch paths (Task 3.1)
- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — unit tests for `_handle_notification_due`, `_handle_player_removed`, and `_handle_game_cancelled` (Task 3.2)
- `tests/unit/bot/events/test_handlers_misc.py` — unit tests for remaining `handlers.py` error paths to reach ≥85% coverage (Task 3.3)

## Modified

- `compose.int.yaml` (line 112) — renamed `COVERAGE_FILE` from `.coverage.integration` to `runner.integration` (Task 1.1)
- `compose.e2e.yaml` (line 130) — renamed `COVERAGE_FILE` from `.coverage.e2e` to `runner.e2e` (Task 1.2)

## Phase Notes

### Phase 1: Fix Coverage Infrastructure

- Tasks 1.1 and 1.2 completed: renamed runner COVERAGE_FILE values to non-hidden names
- Task 1.3 completed: hidden coverage files removed from `coverage/` directory
- Task 1.4: verification requires fresh integration+e2e runs (skipped — deferred to live test run)

### Phase 2: Unit Test `notification_service.py`

- Task 2.1 completed: unit tests for `NotificationService.send_game_reminder_due()` added
  to `tests/unit/scheduler/services/test_notification_service.py`

### Phase 3: Unit Test `events/handlers.py`

- Baseline coverage before Phase 3: 85.14% (already at target due to existing integration tests)
- Task 3.1 completed: 9 tests in `tests/unit/bot/events/test_handlers_game_events.py` cover `_process_event`, `_handle_game_created`, `_handle_game_updated`, and `_delayed_refresh` error/branch paths
- Task 3.2 completed: 13 tests in `tests/unit/bot/events/test_handlers_lifecycle_events.py` cover `_handle_notification_due`, `_handle_game_reminder`, `_handle_join_notification`, `_handle_player_removed`, `_handle_participant_drop_due`, and `_handle_game_cancelled`
- Task 3.3 completed: 15 tests in `tests/unit/bot/events/test_handlers_misc.py` cover `_handle_clone_confirmation`, `_send_dm`, `_update_message_for_player_removal`, `_handle_status_transition_due`, `_is_transition_ready`, `_handle_post_transition_actions`, and `_archive_game_announcement`
- Final unit test coverage for `handlers.py`: 100% (545/545 statements)
- All 1748 unit tests pass
