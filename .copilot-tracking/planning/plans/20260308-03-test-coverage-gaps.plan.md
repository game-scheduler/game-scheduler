---
applyTo: '.copilot-tracking/changes/20260308-03-test-coverage-gaps-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Test Coverage Gaps

## Overview

Write tests to close the top 10 prioritized coverage gaps identified after the
coverage collection infrastructure fix, targeting bot handlers, bot auth, API
routes, and service layer code.

## Objectives

- Cover `button_handler.py`, `join_game.py`, and `leave_game.py` uncovered paths via e2e/integration tests
- Cover `role_checker.py` Discord API error paths with unit tests (security impact)
- Cover `channels.py` and `templates.py` write endpoints via integration tests
- Cover `guilds.py` admin routes via integration tests
- Cover `utils.py` and `cache.py` error paths with unit tests
- Cover `games.py`, `permissions.py`, and `guild_queries.py` scattered error paths

## Research Summary

### Project Files

- `services/bot/handlers/button_handler.py` — lines 55–78 uncovered; gateway for join/leave flows
- `services/bot/handlers/join_game.py` — lines 63–118, 143–162 uncovered; 42 missed stmts
- `services/bot/handlers/leave_game.py` — lines 59–93, 116–143 uncovered; 37 missed stmts
- `services/bot/auth/role_checker.py` — lines 85–86, 96–101, 117–206 uncovered; security impact
- `services/api/routes/channels.py` — lines 73–84, 104–118, 137 uncovered; write endpoints
- `services/api/routes/templates.py` — lines 123–128, 254, 282, 297, 311–354 uncovered; mutation endpoints
- `services/bot/handlers/utils.py` — lines 78–81, 91–94 uncovered
- `services/api/routes/guilds.py` — lines 88, 158, 242, 255, 293, 377–415 uncovered
- `services/bot/auth/cache.py` — lines 51, 140–142, 158–159 uncovered
- `services/api/services/games.py` — 41 scattered missed lines
- `services/api/dependencies/permissions.py` — lines 316, 524–525, 564, 627, 719 uncovered
- `shared/data_access/guild_queries.py` — lines 512–513 uncovered

### External References

- #file:../research/20260308-03-test-coverage-gaps-research.md — validated post-fix
  coverage gap analysis with prioritized gap table (Lines 170–186) and missing-line
  ranges (Lines 187–201)

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — writing
  tests for already-implemented code
- #file:../../.github/instructions/integration-tests.instructions.md — integration
  and e2e test patterns

## Implementation Checklist

### [x] Phase 1: Bot Handler E2E/Integration Tests (Priorities 1–3)

- [x] Task 1.1: Write e2e/integration tests for `button_handler.py` (lines 55–78)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 13-37)

- [x] Task 1.2: Write e2e/integration tests for `join_game.py` (lines 63–118, 143–162)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 38-64)

- [x] Task 1.3: Write e2e/integration tests for `leave_game.py` (lines 59–93, 116–143)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 65-90)

### [ ] Phase 2: Bot Auth and Utility Unit Tests (Priorities 4, 7, 9)

- [ ] Task 2.1: Write unit tests for `role_checker.py` (lines 85–86, 96–101, 117–206)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 93-115)

- [ ] Task 2.2: Write unit tests for `utils.py` (lines 78–81, 91–94)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 116-135)

- [ ] Task 2.3: Write unit tests for `cache.py` (lines 51, 140–142, 158–159)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 136-158)

### [ ] Phase 3: API Route Integration Tests (Priorities 5, 6, 8)

- [ ] Task 3.1: Write integration tests for `channels.py` (lines 73–84, 104–118, 137)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 161-184)

- [ ] Task 3.2: Write integration tests for `templates.py` (lines 123–128, 254, 282, 297, 311–354)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 185-209)

- [ ] Task 3.3: Write integration tests for `guilds.py` (lines 88, 158, 242, 255, 293, 377–415)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 210-235)

### [ ] Phase 4: Service Layer and Permissions Tests (Priority 10 + Extras)

- [ ] Task 4.1: Write integration/unit tests for `games.py` scattered error paths
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 238-260)

- [ ] Task 4.2: Write integration/unit tests for `permissions.py` (lines 316, 524–525, 564, 627, 719)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 261-282)

- [ ] Task 4.3: Write unit tests for `guild_queries.py` (lines 512–513)
  - Details: .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md (Lines 283-302)

## Dependencies

- Coverage collection infrastructure fix already applied (no action needed)
- Existing test fixtures in `tests/e2e/conftest.py`, `tests/integration/conftest.py`, `tests/unit/conftest.py`
- `scripts/run-integration-tests.sh` and `scripts/run-e2e-tests.sh` for post-phase validation

## Success Criteria

- All 10 prioritized modules show measurably increased combined coverage
- All new tests pass without modifying production code
- `scripts/coverage-report.sh` produces an updated combined report confirming improvements
