# Changes: Coverage Infrastructure Fix and Gap Analysis Update

## Phase 1: Fix Coverage Infrastructure

### Added

- `.copilot-tracking/changes/20260316-01-coverage-gaps-update-changes.md` — changes tracking file for this task

### Modified

- `compose.int.yaml` (line 112) — renamed `COVERAGE_FILE` from `/app/coverage/.coverage.integration` to `/app/coverage/runner.integration` so the glob `coverage/*` picks it up automatically
- `compose.e2e.yaml` (line 130) — renamed `COVERAGE_FILE` from `/app/coverage/.coverage.e2e` to `/app/coverage/runner.e2e` so the glob `coverage/*` picks it up automatically

### Removed

- No hidden coverage dotfiles were present in `coverage/` at time of implementation; nothing to remove

### Notes

- Task 1.4 (verify ≥87.69%) requires fresh integration and e2e Docker runs against the updated compose files; deferred to manual verification after the next test run

## Phase 2: Unit Test `notification_service.py`

### Added

- `tests/unit/services/scheduler/test_notification_service.py` — 4 unit tests covering `send_game_reminder_due()` happy path, publish exception, connect exception, and `get_notification_service()` factory; brings `notification_service.py` to 100% coverage
