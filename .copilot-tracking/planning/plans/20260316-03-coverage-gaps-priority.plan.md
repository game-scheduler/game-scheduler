---
applyTo: '.copilot-tracking/changes/20260316-03-coverage-gaps-priority-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Coverage Gap Priority Improvements

## Overview

Fix a coverage-reporting bug that hides real test results, then add targeted unit and integration
tests for the correctness-critical and security-critical code paths identified by coverage analysis.

## Objectives

- Restore accurate coverage reporting for `notification_service.py` by fixing the signal test bug
- Reach 100% coverage on `auth.py` dependency, `status_transitions.py`, `guild_queries.py`, and `event_builders.py`
- Reach ≥85% coverage on `generic_scheduler_daemon.py`
- Close error-branch gaps in Redis client, guild sync, Discord client, auth/games/templates routes, and utility modules
- Raise combined project coverage from 88.89% to ≥92%

## Research Summary

### Project Files

- `tests/unit/services/scheduler/test_daemon_runner_run.py` — contains the signal test with the coverage-stopping bug
- `services/api/dependencies/auth.py` — four `401` branches uncovered (76%)
- `shared/utils/status_transitions.py` — invalid-input branches and `get_next_status` body uncovered (74%)
- `shared/data_access/guild_queries.py` — all empty-input guards uncovered (75%)
- `services/scheduler/event_builders.py` — TTL calculation branches uncovered (42%)
- `services/scheduler/generic_scheduler_daemon.py` — nearly entirely untested (16%)
- `shared/cache/client.py` — all exception branches uncovered (64%)
- `services/bot/guild_sync.py` — `_refresh_guild_channels` and `_expand_rls_context_for_guilds` uncovered (71%)
- `shared/discord/client.py` — HTTP error branches in ~17 methods uncovered (85%)
- `services/api/routes/auth.py`, `games.py`, `templates.py` — error response paths uncovered

### External References

- #file:../research/20260316-03-coverage-gaps-priority-research.md — full coverage analysis with root causes and implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — test methodology (writing tests for already-implemented code)

## Implementation Checklist

### [ ] Phase 1: Fix Signal Test Coverage Bug

- [ ] Task 1.1: Fix `test_signal_sets_shutdown_flag` to stop corrupting coverage
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 13-37)

### [ ] Phase 2: High-Priority Unit Tests (P1–P5)

- [ ] Task 2.1: Add `get_current_user` error branch tests (`auth.py` → 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 38-57)

- [ ] Task 2.2: Cover `status_transitions.py` invalid-input branches (→ 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 58-75)

- [ ] Task 2.3: Cover `guild_queries.py` empty-input validation guards (→ 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 76-94)

- [ ] Task 2.4: Cover `event_builders.py` TTL calculation branches (→ 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 95-113)

- [ ] Task 2.5: Cover `generic_scheduler_daemon.py` error paths (→ ≥85%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 114-138)

### [ ] Phase 3: Redis and Infrastructure Error Paths (P7–P9)

- [ ] Task 3.1: Cover `cache/client.py` exception branches (→ ≥90%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 139-158)

- [ ] Task 3.2: Cover `guild_sync.py` refresh channel scenarios (→ ≥90%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 159-178)

- [ ] Task 3.3: Cover `shared/discord/client.py` HTTP error branches (→ ≥95%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 179-200)

### [ ] Phase 4: Integration Tests (P6, P10, P11)

- [ ] Task 4.1: Cover `services/api/routes/auth.py` error paths (→ ≥90%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 201-220)

- [ ] Task 4.2: Cover `services/api/routes/games.py` error responses (→ ≥93%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 221-239)

- [ ] Task 4.3: Cover `services/api/routes/templates.py` error paths (→ ≥93%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 240-260)

### [ ] Phase 5: Utility and Minor Gap Fill (P12–P19)

- [ ] Task 5.1: Cover `shared/utils/timezone.py` functions (→ 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 261-277)

- [ ] Task 5.2: Cover `shared/utils/discord.py` utility functions (→ ≥95%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 278-294)

- [ ] Task 5.3: Cover `bot/utils/discord_format.py` error branches (→ ≥92%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 295-311)

- [ ] Task 5.4: Cover `sync_publisher.py` and `consumer.py` error paths (→ ≥93% each)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 312-330)

- [ ] Task 5.5: Cover `postgres_listener.py` and `scheduler_daemon_wrapper.py` gaps
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 331-349)

- [ ] Task 5.6: Cover `shared/utils/discord_tokens.py` error paths (→ 100%)
  - Details: .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md (Lines 350-365)

## Dependencies

- `uv` with `pytest-cov` for running tests and coverage
- `scripts/coverage-report.sh` for combined coverage validation
- `scripts/run-integration-tests.sh` for Phase 4
- All mock libraries already in the project (`unittest.mock`, `pytest-mock`)

## Success Criteria

- `services/api/dependencies/auth.py` → 100%
- `shared/utils/status_transitions.py` → 100%
- `shared/data_access/guild_queries.py` → 100%
- `services/scheduler/event_builders.py` → 100%
- `services/scheduler/generic_scheduler_daemon.py` → ≥85%
- `services/scheduler/services/notification_service.py` → ≥95% (restored by Phase 1)
- Combined project coverage → ≥92%
