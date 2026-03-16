---
applyTo: '.copilot-tracking/changes/20260316-01-coverage-gaps-update-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Coverage Infrastructure Fix and Gap Analysis Update

## Overview

Fix the hidden coverage file bug that silently excludes test-runner coverage data from combined reports, then add unit tests for the highest-priority coverage gaps.

## Objectives

- Rename two `COVERAGE_FILE` env vars to non-hidden names so `coverage/*` glob includes them automatically
- Verify combined coverage reaches ≥87.69% after the rename
- Add unit tests bringing `notification_service.py` to 100% coverage
- Add unit tests bringing `events/handlers.py` to ≥85% coverage

## Research Summary

### Project Files

- `compose.int.yaml` (line 112) — integration test runner `COVERAGE_FILE` is `.coverage.integration` (dotfile, silently excluded by glob)
- `compose.e2e.yaml` (line 130) — e2e test runner `COVERAGE_FILE` is `.coverage.e2e` (dotfile, silently excluded by glob)
- `scripts/coverage-report.sh` — uses `coverage/*` glob; no changes needed after rename
- `services/scheduler/services/notification_service.py` — 0% coverage, 30 statements
- `services/bot/events/handlers.py` — 69% coverage, 169 missing statements

### External References

- #file:../research/20260316-01-coverage-gaps-update-research.md — full root-cause analysis, impact table, fix specification, and gap prioritization

## Implementation Checklist

### [ ] Phase 1: Fix Coverage Infrastructure

- [x] Task 1.1: Rename test runner COVERAGE_FILE in `compose.int.yaml`
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 11–25)

- [x] Task 1.2: Rename test runner COVERAGE_FILE in `compose.e2e.yaml`
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 26–39)

- [x] Task 1.3: Remove hidden coverage files from `coverage/` if present
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 40–53)

- [ ] Task 1.4: Verify combined coverage reaches ≥87.69%
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 54–69)
  - Note: Requires fresh integration + e2e test runs against updated compose files

### [x] Phase 2: Unit Test `notification_service.py`

- [x] Task 2.1: Write unit tests for `NotificationService.send_game_reminder_due()`
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 72–92)

### [ ] Phase 3: Unit Test `events/handlers.py`

- [ ] Task 3.1: Unit tests for game-created and game-updated handler error paths
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 96–112)

- [ ] Task 3.2: Unit tests for notification, player-removal, and cancellation handler paths
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 113–127)

- [ ] Task 3.3: Unit tests for remaining handler error paths to reach ≥85%
  - Details: .copilot-tracking/planning/details/20260316-01-coverage-gaps-update-details.md (Lines 128–142)

## Dependencies

- `uv` and `pytest` for running tests and coverage
- `coverage.py` for measurement
- Docker for integration/e2e test runs (Phase 1 verification only)

## Success Criteria

- `scripts/coverage-report.sh` reports ≥87.69% total without manual hidden-file inclusion
- `join_game.py`, `leave_game.py`, `button_handler.py` show correct (≥96%) coverage in terminal report
- `notification_service.py` reaches 100% with new unit tests
- `events/handlers.py` reaches ≥85% with new unit tests
- All new tests pass in the full unit suite
