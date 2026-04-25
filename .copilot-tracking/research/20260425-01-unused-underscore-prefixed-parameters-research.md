<!-- markdownlint-disable-file -->

# Task Research Notes: Unused Underscore-Prefixed and Deprecated Function Parameters

## Research Executed

### File Analysis

- `services/api/dependencies/permissions.py`
  - `_require_permission` accepts `_role_service` which is never used inside the function body; all permission work is delegated to the `permission_checker` closure passed as an argument
  - Three inner closures (`check_manage_guild`, `check_manage_channels`, `check_bot_manager`) each accept `_token` as their third positional argument; this is required because `_require_permission` always passes `access_token` as the third arg to `permission_checker`, but these two closures satisfy the permission check through `role_service` captured from the outer scope
  - `verify_template_access(access_token)` — docstring explicitly marks `access_token` as "deprecated, no longer used"; the parameter is still passed to `queries.require_guild_by_id` which also ignores it
  - `verify_game_access(access_token)` — docstring explicitly marks it "deprecated, no longer used for guild checks"; same passthrough to `require_guild_by_id`
- `services/api/database/queries.py`
  - `require_guild_by_id(_access_token)` — docstring explicitly marks it "Deprecated, no longer used (kept for API compatibility)"; the function body never references it; guild resolution now uses RLS and member projection
- `services/api/auth/roles.py`
  - `check_bot_manager_permission(_access_token)` — docstring says "Retained for API compatibility; no longer used"; has default `None`; the function body never references it
  - `check_game_host_permission(access_token)` — no deprecation comment, but it only passes `access_token` down to `check_bot_manager_permission` which ignores it; transitively dead
- `services/scheduler/generic_scheduler_daemon.py`
  - `GenericSchedulerDaemon.__init__(_process_dlq)` — docstring says "Deprecated parameter, kept for backwards compatibility"; has default `False`; the constructor body never references it
- `services/api/app.py`
  - `lifespan(_app)` — FastAPI requires this signature for lifespan context managers
- `services/api/middleware/error_handler.py`
  - `database_exception_handler(_request, exc)` and `general_exception_handler(_request, exc)` — Starlette exception handler protocol requires `(Request, Exception)` signature
- `services/retry/retry_daemon.py`
  - `_observe_dlq_depth(self, _options)` — OpenTelemetry observable callback interface always passes an `options` object
- `services/retry/retry_daemon_wrapper.py`
  - `signal_handler(_signum, _frame)` — Python `signal.signal()` requires this two-argument signature
- `services/scheduler/daemon_runner.py`
  - `_signal_handler(_signum, _frame)` — same OS signal handler requirement
- `services/init/main.py`
  - `_handle_sigterm(_signum, _frame)` — same
- `services/bot/bot.py`
  - `on_guild_role_update(self, _before, after)` — discord.py always passes `(before, after)`; only `after.guild` is needed
  - `on_member_add(self, _member)` — discord.py requires this signature; handler triggers full guild repopulation without inspecting the member
  - `on_member_update(self, _before, _after)` — same pattern; neither value is consulted
  - `on_member_remove(self, _member)` — same
  - `_handle_sweep_request(self, _request)` — aiohttp route handler signature; request body is not used
  - `_handle_sync_guilds_request(self, _request)` — same

### Code Search Results

- `def \w+\([^)]*\b_\w+` across `**/*.py`
  - 29 total matches; all located in `services/`, `tests/`, or `alembic/`
  - All test-file occurrences are intentional mock/stub stubs and not relevant
- `deprecated|DEPRECATED|no.longer.needed` across `**/*.py`
  - 4 matches in production code: `generic_scheduler_daemon.py`, `permissions.py` (×2), `queries.py`
- `_require_permission\(` in `permissions.py`
  - 4 matches: 1 definition (line 321), 3 call sites (lines 416, 460, 554)
- `require_guild_by_id` usages: 31 total — 11 production callers, ~20 test callers (all pass `access_token` positionally)
- `verify_template_access` usages: 13 total — 1 production, ~12 test
- `verify_game_access` usages: 22 total — 3 production, ~19 test
- `check_bot_manager_permission` usages: 6 total — 4 production callers that pass `access_token` or `token` explicitly
- `check_game_host_permission` usages: 4 total — 3 production callers pass `access_token` positionally or by keyword
- `GenericSchedulerDaemon(` / `_process_dlq=` usages: 3 callers in `scheduler_daemon_wrapper.py`, all pass `_process_dlq=False` as keyword

### Project Conventions

- Standards referenced: Python underscore-prefix convention: a single leading `_` on a parameter conventionally signals "intentionally unused, required by interface"
- All occurrences examined against function bodies to distinguish genuine dead parameters from interface-adapter patterns

## Key Discoveries

### Classification of All Occurrences

Parameters fall into four categories:

1. **Genuinely obsolete (unlabeled)** — parameter accepted but never used, no external interface requires it, no deprecation comment
2. **Explicitly deprecated** — documented in docstring as deprecated/no longer used, but the parameter name may not carry a `_` prefix
3. **Interface adapter** — external framework/OS/library mandates the parameter exist in the signature
4. **Closure interface match** — inner function must accept a parameter that the outer caller always provides, even though this particular implementation ignores it

### Access Token Deprecation Chain

Several deprecated parameters form a call chain. The root cause is that guild authorization was migrated to use RLS + member projection, eliminating the need to pass OAuth2 access tokens for guild lookups. The token was removed from the inner logic but not yet stripped from the call stack:

```
verify_template_access(access_token)         # permissions.py — deprecated
verify_game_access(access_token)             # permissions.py — deprecated
  └─→ queries.require_guild_by_id(_access_token)  # queries.py — deprecated, never used
check_game_host_permission(access_token)     # roles.py — transitively dead
  └─→ check_bot_manager_permission(_access_token) # roles.py — deprecated, never used
```

`_require_permission` / `_resolve_guild_id` also collect `access_token` from session and pass it to `require_guild_by_id`, contributing more call sites.

### Complete Audit Table

#### Obsolete/Deprecated Parameters (actionable)

| File                                                | Function                          | Parameter       | Status              | Production callers to modify                                     | Test callers to modify |
| --------------------------------------------------- | --------------------------------- | --------------- | ------------------- | ---------------------------------------------------------------- | ---------------------- |
| `services/api/dependencies/permissions.py:321`      | `_require_permission`             | `_role_service` | Unlabeled obsolete  | **3** (same file: 416, 460, 554)                                 | 0                      |
| `services/api/database/queries.py:123`              | `require_guild_by_id`             | `_access_token` | Explicit deprecated | **~11** (permissions.py ×3, guilds.py ×6, templates.py ×2)       | **~20**                |
| `services/api/dependencies/permissions.py:157`      | `verify_template_access`          | `access_token`  | Explicit deprecated | **1** (templates.py:192)                                         | **~12**                |
| `services/api/dependencies/permissions.py:205`      | `verify_game_access`              | `access_token`  | Explicit deprecated | **3** (games.py: 448, 514, 721)                                  | **~19**                |
| `services/api/auth/roles.py:250`                    | `check_bot_manager_permission`    | `_access_token` | Explicit deprecated | **4** (permissions.py ×3, games.py:158)                          | **~5**                 |
| `services/api/auth/roles.py:206`                    | `check_game_host_permission`      | `access_token`  | Transitively dead   | **3** (permissions.py:632, games.py:633, template_service.py:89) | **~5**                 |
| `services/scheduler/generic_scheduler_daemon.py:69` | `GenericSchedulerDaemon.__init__` | `_process_dlq`  | Explicit deprecated | **3** (scheduler_daemon_wrapper.py: 73, 84, 95)                  | 0                      |

#### Interface-Adapter Parameters (not actionable — required by framework/OS)

| File                                           | Function                          | Parameter(s)        | Required by       |
| ---------------------------------------------- | --------------------------------- | ------------------- | ----------------- |
| `services/api/dependencies/permissions.py:411` | `check_manage_guild` _(inner)_    | `_token`            | Closure interface |
| `services/api/dependencies/permissions.py:455` | `check_manage_channels` _(inner)_ | `_token`            | Closure interface |
| `services/api/app.py:89`                       | `lifespan`                        | `_app`              | FastAPI           |
| `services/api/middleware/error_handler.py:74`  | `database_exception_handler`      | `_request`          | Starlette         |
| `services/api/middleware/error_handler.py:109` | `general_exception_handler`       | `_request`          | Starlette         |
| `services/retry/retry_daemon.py:352`           | `_observe_dlq_depth`              | `_options`          | OpenTelemetry     |
| `services/retry/retry_daemon_wrapper.py:43`    | `signal_handler`                  | `_signum`, `_frame` | OS                |
| `services/scheduler/daemon_runner.py:46`       | `_signal_handler`                 | `_signum`, `_frame` | OS                |
| `services/init/main.py:161`                    | `_handle_sigterm`                 | `_signum`, `_frame` | OS                |
| `services/bot/bot.py:377`                      | `on_guild_role_update`            | `_before`           | discord.py        |
| `services/bot/bot.py:396`                      | `on_member_add`                   | `_member`           | discord.py        |
| `services/bot/bot.py:405`                      | `on_member_update`                | `_before`, `_after` | discord.py        |
| `services/bot/bot.py:414`                      | `on_member_remove`                | `_member`           | discord.py        |
| `services/bot/bot.py:476`                      | `_handle_sweep_request`           | `_request`          | aiohttp           |
| `services/bot/bot.py:483`                      | `_handle_sync_guilds_request`     | `_request`          | aiohttp           |

## Recommended Approach

Address all seven actionable cases. The access-token chain is best cleaned up bottom-up (innermost function first) to keep each step consistent. The `_process_dlq` and `_role_service` cases are independent and can be done in any order.

**Recommended order:**

1. `check_bot_manager_permission` — remove `_access_token` (leaf of the access-token chain; 4 production + ~5 test call sites)
2. `check_game_host_permission` — remove `access_token` (now safe since step 1 is done; 3 production + ~5 test call sites)
3. `require_guild_by_id` — remove `_access_token` (~11 production + ~20 test call sites — largest change)
4. `verify_template_access` — remove `access_token` (1 production + ~12 test)
5. `verify_game_access` — remove `access_token` (3 production + ~19 test)
6. `_require_permission` — remove `_role_service` (3 call sites, all in same file)
7. `GenericSchedulerDaemon.__init__` — remove `_process_dlq` (3 call sites in `scheduler_daemon_wrapper.py`)

## Implementation Guidance

- **Objectives**: Remove all 7 obsolete/deprecated parameters from production code
- **Key Tasks**:
  1. `roles.py`: remove `_access_token: str | None = None` from `check_bot_manager_permission`; remove the argument from 4 production call sites in permissions.py and games.py
  2. `roles.py`: remove `access_token: str | None = None` from `check_game_host_permission`; remove the argument from 3 production call sites; note that `check_game_host_permission` itself can stop being passed `access_token` only after step 1 is done
  3. `queries.py`: remove `_access_token: str` from `require_guild_by_id`; update all ~11 production callers and ~20 test callers
  4. `permissions.py`: remove `access_token: str` from `verify_template_access`; update 1 production caller and ~12 test callers
  5. `permissions.py`: remove `access_token: str` from `verify_game_access`; update 3 production callers and ~19 test callers
  6. `permissions.py`: remove `_role_service` from `_require_permission` and 3 call sites in the same file
  7. `generic_scheduler_daemon.py`: remove `_process_dlq: bool = False` from `__init__`; remove `_process_dlq=False` from 3 call sites in `scheduler_daemon_wrapper.py`
- **Dependencies**: Steps 1 and 2 must be done before step 3 can be clean (otherwise callers of `check_game_host_permission` still need `access_token` to pass through). Steps 4–7 are independent of each other.
- **Success Criteria**: No function in production code accepts a parameter that is documented as deprecated or never referenced in the body; all callers updated; unit tests pass
