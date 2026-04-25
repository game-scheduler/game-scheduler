<!-- markdownlint-disable-file -->

# Task Details: Remove Obsolete and Deprecated Function Parameters

## Research Reference

**Source Research**: #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md

## Phase 1: Remove `_access_token` from `check_bot_manager_permission`

### Task 1.1: Remove parameter from `check_bot_manager_permission` in `roles.py`

Remove `_access_token: str | None = None` from the signature of `check_bot_manager_permission`. The parameter is documented as "Retained for API compatibility; no longer used" and the function body never references it.

- **Files**:
  - `services/api/auth/roles.py` (line ~250) — remove `_access_token` parameter from signature and its docstring entry
- **Success**:
  - `check_bot_manager_permission` accepts no `access_token`/`_access_token` argument
  - Function body unchanged
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-60) — audit table entry for this function
- **Dependencies**:
  - None (leaf of the access-token call chain)

### Task 1.2: Update 4 production call sites

Remove the `access_token` argument from every production call to `check_bot_manager_permission`. Callers are in `permissions.py` (×3) and `games.py` (×1).

- **Files**:
  - `services/api/dependencies/permissions.py` — 3 call sites passing `access_token` or `token`
  - `services/api/routes/games.py` (line ~158) — 1 call site
- **Success**:
  - `grep -r "check_bot_manager_permission" services/` shows no remaining argument passed
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-60) — caller count breakdown
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Update ~5 test call sites

Remove the `access_token` argument from every test call to `check_bot_manager_permission`.

- **Files**:
  - `tests/unit/` — locate all test files calling `check_bot_manager_permission`
- **Success**:
  - All tests in `tests/unit/` pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-60) — ~5 test callers
- **Dependencies**:
  - Task 1.2 complete

## Phase 2: Remove `access_token` from `check_game_host_permission`

### Task 2.1: Remove parameter from `check_game_host_permission` in `roles.py`

Remove `access_token: str | None = None` (or equivalent) from the signature of `check_game_host_permission`. The parameter was only forwarded to `check_bot_manager_permission`, which no longer accepts it after Phase 1.

- **Files**:
  - `services/api/auth/roles.py` (line ~206) — remove `access_token` parameter from signature and docstring
- **Success**:
  - `check_game_host_permission` accepts no `access_token` argument
  - The internal call to `check_bot_manager_permission` passes no token argument
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-63) — audit table entry
- **Dependencies**:
  - Phase 1 complete (otherwise internal call to `check_bot_manager_permission` would still forward a token)

### Task 2.2: Update 3 production call sites

Remove the `access_token` argument from calls to `check_game_host_permission` in `permissions.py`, `games.py`, and `template_service.py`.

- **Files**:
  - `services/api/dependencies/permissions.py` (line ~632)
  - `services/api/routes/games.py` (line ~633)
  - `services/api/services/template_service.py` (line ~89)
- **Success**:
  - `grep -r "check_game_host_permission" services/` shows no remaining `access_token` argument
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-63)
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Update ~5 test call sites

Remove the `access_token` argument from every test call to `check_game_host_permission`.

- **Files**:
  - `tests/unit/` — locate all test files calling `check_game_host_permission`
- **Success**:
  - All tests in `tests/unit/` pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-63)
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Remove `_access_token` from `require_guild_by_id`

### Task 3.1: Remove parameter from `require_guild_by_id` in `queries.py`

Remove `_access_token: str` from the signature of `require_guild_by_id`. The docstring explicitly marks it "Deprecated, no longer used (kept for API compatibility)" and the function body never references it.

- **Files**:
  - `services/api/database/queries.py` (line ~123) — remove `_access_token` parameter from signature and docstring
- **Success**:
  - `require_guild_by_id` accepts no token argument
  - Function body unchanged
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54) — audit table entry
- **Dependencies**:
  - None (the function body was already independent of the token)

### Task 3.2: Update ~11 production callers

Remove the `access_token` positional argument from all production calls to `require_guild_by_id`.

- **Files**:
  - `services/api/dependencies/permissions.py` — 3 call sites (from `_require_permission` / `_resolve_guild_id`)
  - `services/api/routes/guilds.py` — 6 call sites
  - `services/api/routes/templates.py` — 2 call sites
- **Success**:
  - `grep -r "require_guild_by_id" services/` shows no remaining token argument at any call site
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54)
- **Dependencies**:
  - Task 3.1 complete

### Task 3.3: Update ~20 test callers

Remove the `access_token` positional argument from all test calls to `require_guild_by_id`.

- **Files**:
  - `tests/unit/` and `tests/integration/` — all test files calling `require_guild_by_id`
- **Success**:
  - All tests pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54) — ~20 test callers noted
- **Dependencies**:
  - Task 3.2 complete

## Phase 4: Remove `access_token` from `verify_template_access`

### Task 4.1: Remove parameter from `verify_template_access` in `permissions.py`

Remove `access_token: str` from the signature of `verify_template_access`. The docstring explicitly marks it "deprecated, no longer used".

- **Files**:
  - `services/api/dependencies/permissions.py` (line ~157) — remove `access_token` parameter from signature and docstring
- **Success**:
  - `verify_template_access` accepts no `access_token` argument
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54)
- **Dependencies**:
  - Phase 3 complete (the internal call to `require_guild_by_id` no longer passes a token)

### Task 4.2: Update 1 production caller and ~12 test callers

Remove the `access_token` argument from `templates.py` and all test callers.

- **Files**:
  - `services/api/routes/templates.py` (line ~192)
  - `tests/unit/` — ~12 test call sites
- **Success**:
  - `grep -r "verify_template_access" services/` shows no remaining token argument
  - All tests pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54)
- **Dependencies**:
  - Task 4.1 complete

## Phase 5: Remove `access_token` from `verify_game_access`

### Task 5.1: Remove parameter from `verify_game_access` in `permissions.py`

Remove `access_token: str` from the signature of `verify_game_access`. The docstring explicitly marks it "deprecated, no longer used for guild checks".

- **Files**:
  - `services/api/dependencies/permissions.py` (line ~205) — remove `access_token` parameter from signature and docstring
- **Success**:
  - `verify_game_access` accepts no `access_token` argument
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54)
- **Dependencies**:
  - Phase 3 complete (the internal call to `require_guild_by_id` no longer passes a token)

### Task 5.2: Update 3 production callers and ~19 test callers

Remove the `access_token` argument from `games.py` call sites and all test callers.

- **Files**:
  - `services/api/routes/games.py` (lines ~448, ~514, ~721)
  - `tests/unit/` — ~19 test call sites
- **Success**:
  - `grep -r "verify_game_access" services/` shows no remaining token argument
  - All tests pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54)
- **Dependencies**:
  - Task 5.1 complete

## Phase 6: Remove `_role_service` from `_require_permission`

### Task 6.1: Remove `_role_service` and update 3 call sites in `permissions.py`

Remove `_role_service` from the `_require_permission` function signature (line ~321) and remove the argument from the 3 call sites (lines ~416, ~460, ~554) in the same file. The parameter is never referenced in the function body; all permission logic uses the `permission_checker` closure argument.

- **Files**:
  - `services/api/dependencies/permissions.py` — 1 definition + 3 call sites (all in the same file)
- **Success**:
  - `grep "_role_service" services/api/dependencies/permissions.py` returns no matches
  - All tests pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 47-54) — audit table entry
- **Dependencies**:
  - None (independent of the access-token chain)

## Phase 7: Remove `_process_dlq` from `GenericSchedulerDaemon.__init__`

### Task 7.1: Remove `_process_dlq` and update 3 callers in `scheduler_daemon_wrapper.py`

Remove `_process_dlq: bool = False` from `GenericSchedulerDaemon.__init__` in `generic_scheduler_daemon.py` (line ~69) and remove `_process_dlq=False` from the 3 call sites in `scheduler_daemon_wrapper.py` (lines ~73, ~84, ~95). The parameter is documented as "Deprecated parameter, kept for backwards compatibility" and the constructor body never references it.

- **Files**:
  - `services/scheduler/generic_scheduler_daemon.py` (line ~69) — remove parameter from `__init__` signature and docstring
  - `services/scheduler/scheduler_daemon_wrapper.py` (lines ~73, ~84, ~95) — remove `_process_dlq=False` keyword argument
- **Success**:
  - `grep "_process_dlq" services/scheduler/` returns no matches
  - All tests pass
- **Research References**:
  - #file:../research/20260425-01-unused-underscore-prefixed-parameters-research.md (Lines 55-63) — audit table entry
- **Dependencies**:
  - None (independent of the access-token chain)

## Dependencies

- Python with pytest for unit test verification after each phase

## Success Criteria

- No function in production code accepts a parameter documented as deprecated or never referenced in its body
- All callers (production and test) updated to omit removed arguments
- `uv run pytest tests/unit` passes after all phases complete
