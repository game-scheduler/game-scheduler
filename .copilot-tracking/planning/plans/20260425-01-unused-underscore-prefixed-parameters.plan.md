---
applyTo: '.copilot-tracking/changes/20260425-01-unused-underscore-prefixed-parameters-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove Obsolete and Deprecated Function Parameters

## Overview

Remove seven deprecated or never-used function parameters from production code and update all callers, including test files.

## Objectives

- Remove all seven obsolete/deprecated parameters identified in the audit
- Update every production and test call site to omit the removed arguments
- Leave interface-adapter parameters (framework/OS-required) untouched
- Ensure all unit tests pass after each step

## Research Summary

### Project Files

- `services/api/auth/roles.py` — contains `check_bot_manager_permission` and `check_game_host_permission` with deprecated `access_token` / `_access_token` parameters
- `services/api/database/queries.py` — contains `require_guild_by_id` with deprecated `_access_token`
- `services/api/dependencies/permissions.py` — contains `verify_template_access`, `verify_game_access`, and `_require_permission` with deprecated/unused parameters
- `services/scheduler/generic_scheduler_daemon.py` — contains `GenericSchedulerDaemon.__init__` with deprecated `_process_dlq`
- `services/scheduler/scheduler_daemon_wrapper.py` — 3 callers of `GenericSchedulerDaemon` passing `_process_dlq=False`

### External References

- #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md — full audit with caller counts, line numbers, and recommended removal order

## Implementation Checklist

### [x] Phase 1: Remove `_access_token` from `check_bot_manager_permission`

- [x] Task 1.1: Remove parameter from `check_bot_manager_permission` signature in `roles.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 18-42)

- [x] Task 1.2: Update all 4 production call sites (permissions.py ×3, games.py ×1)
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 43-60)

- [x] Task 1.3: Update ~5 test call sites
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 61-74)

### [x] Phase 2: Remove `access_token` from `check_game_host_permission`

- [x] Task 2.1: Remove parameter from `check_game_host_permission` signature in `roles.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 77-96)

- [x] Task 2.2: Update all 3 production call sites (permissions.py:632, games.py:633, template_service.py:89)
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 97-113)

- [x] Task 2.3: Update ~5 test call sites
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 114-127)

### [x] Phase 3: Remove `_access_token` from `require_guild_by_id`

- [x] Task 3.1: Remove parameter from `require_guild_by_id` signature in `queries.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 130-149)

- [x] Task 3.2: Update ~11 production callers (permissions.py ×3, guilds.py ×6, templates.py ×2)
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 150-167)

- [x] Task 3.3: Update ~20 test callers
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 168-181)

### [x] Phase 4: Remove `access_token` from `verify_template_access`

- [x] Task 4.1: Remove parameter from `verify_template_access` signature in `permissions.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 184-203)

- [x] Task 4.2: Update 1 production caller (templates.py:192) and ~12 test callers
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 204-218)

### [x] Phase 5: Remove `access_token` from `verify_game_access`

- [x] Task 5.1: Remove parameter from `verify_game_access` signature in `permissions.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 221-240)

- [x] Task 5.2: Update 3 production callers (games.py: 448, 514, 721) and ~19 test callers
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 241-255)

### [x] Phase 6: Remove `_role_service` from `_require_permission`

- [x] Task 6.1: Remove `_role_service` parameter from `_require_permission` in `permissions.py` and update 3 call sites in the same file (lines 416, 460, 554)
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 258-280)

### [x] Phase 7: Remove `_process_dlq` from `GenericSchedulerDaemon.__init__`

- [x] Task 7.1: Remove `_process_dlq: bool = False` from `GenericSchedulerDaemon.__init__` in `generic_scheduler_daemon.py` and remove `_process_dlq=False` from 3 call sites in `scheduler_daemon_wrapper.py`
  - Details: .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md (Lines 283-302)

## Dependencies

- Python (pytest for unit tests)
- All phases must complete in order for Phases 1–3; Phases 4–7 are independent of each other but must follow Phase 3

## Success Criteria

- No function in production code accepts a parameter documented as deprecated or never referenced in its body
- All callers (production and test) updated to omit removed arguments
- `uv run pytest tests/unit` passes after all phases complete
