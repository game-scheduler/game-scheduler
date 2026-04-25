<!-- markdownlint-disable-file -->

# Changes: Remove Obsolete and Deprecated Function Parameters

## Status: All Phases Complete

## Overview

Removes five deprecated or never-used `access_token`/`_access_token` function parameters from production code and updates all callers (production + tests). All phases including Phase 6 (`_role_service` from `_require_permission`) and Phase 7 (`_process_dlq` from `GenericSchedulerDaemon.__init__`) are complete.

## Modified

### Phase 1: Removed `_access_token` from `check_bot_manager_permission`

- `services/api/auth/roles.py`: removed `_access_token: str | None = None` from `check_bot_manager_permission` signature and docstring
- `services/api/dependencies/permissions.py`:
  - `check_bot_manager` closure: removed `token` arg from `check_bot_manager_permission` call
  - `can_manage_game`: removed `access_token = token_data[...]` extraction and arg from `check_bot_manager_permission` call
  - `can_export_game`: removed `access_token: str | None = None` param from signature, docstring, and from `check_bot_manager_permission` call
- `services/api/services/games.py`:
  - `_verify_bot_manager_permission`: removed `access_token: str` param and arg from `check_bot_manager_permission` call
  - `_resolve_game_host`: removed `access_token: str` param, docstring entry, and arg from `_verify_bot_manager_permission` call
  - `create_game`: removed `access_token` arg from `_resolve_game_host` call
- `services/api/routes/export.py`: removed `access_token=user.access_token` from `can_export_game` call
- Tests updated: `test_games_service.py`, `test_roles.py`, `test_api_permissions.py`, `test_games.py` (older test file)

### Phase 2: Removed `access_token` from `check_game_host_permission`

- `services/api/auth/roles.py`: removed `access_token: str | None = None` from `check_game_host_permission` signature and docstring; removed from internal `check_bot_manager_permission` call
- `services/api/dependencies/permissions.py`:
  - `require_game_host`: removed `access_token = token_data[...]` and `access_token=access_token` from `check_game_host_permission` call
- `services/api/services/games.py`:
  - `create_game`: removed `access_token: str` param, docstring entry, and arg from `check_game_host_permission` call
- `services/api/routes/games.py`: removed `access_token=current_user.access_token` from `create_game` call
- `services/api/services/template_service.py`:
  - `get_templates_for_user`: removed `access_token: str | None = None` param, docstring entry, and arg from `check_game_host_permission` call
- `services/api/routes/templates.py`: removed `current_user.access_token` positional arg from `get_templates_for_user` call
- Tests updated: `test_games_service.py`, `test_template_service.py`, `test_roles.py`, `test_api_permissions.py`, `tests/unit/api/services/test_games.py`, `tests/integration/services/api/services/test_game_image_integration.py`

### Phase 3: Removed `_access_token` from `require_guild_by_id`

- `services/api/database/queries.py`: removed `_access_token: str` from `require_guild_by_id` signature and docstring
- `services/api/dependencies/permissions.py`:
  - `verify_template_access` caller: removed `access_token` arg
  - `verify_game_access` caller: removed `access_token` arg
  - `_resolve_guild_id`: removed `access_token: str` param and docstring entry
  - `_require_permission`: removed `access_token = token_data[...]`, removed from `_resolve_guild_id` call, removed from `permission_checker` call
  - `check_manage_guild` inner function: removed `_token: str` param
  - `check_manage_channels` inner function: removed `_token: str` param
  - `check_bot_manager` inner function: renamed `token: str` → removed param
- `services/api/routes/guilds.py`: removed `current_user.access_token` from all 6 `require_guild_by_id` calls
- `services/api/routes/templates.py`: removed `current_user.access_token` from 2 `require_guild_by_id` calls
- Tests updated: `test_queries.py`, `test_api_permissions.py`, `test_permissions_migration.py`

### Phase 4: Removed `access_token` from `verify_template_access`

- `services/api/dependencies/permissions.py`: removed `access_token: str` from `verify_template_access` signature and docstring
- `services/api/routes/templates.py`: removed `current_user.access_token` from `verify_template_access` call
- Tests updated: `test_api_permissions.py`, `test_negative_authorization.py`, `test_permissions_migration.py`

### Phase 5: Removed `access_token` from `verify_game_access`

- `services/api/dependencies/permissions.py`: removed `access_token: str` from `verify_game_access` signature and docstring
- `services/api/routes/games.py`: removed `access_token=current_user.access_token` from all 3 `verify_game_access` calls
- Tests updated: `test_api_permissions.py`, `test_negative_authorization.py`, `test_permissions_migration.py`

### Phase 6: Removed `_role_service` from `_require_permission`

- `services/api/dependencies/permissions.py`: removed `_role_service: roles_module.RoleVerificationService` from `_require_permission` signature and docstring; removed `role_service` positional argument from all 3 internal call sites (`require_manage_guild`, `require_manage_channels`, `require_bot_manager`)
- `tests/unit/services/api/dependencies/test_api_permissions.py`: removed `mock_role_service` argument from all 7 direct `_require_permission` call sites

### Phase 7: Removed `_process_dlq` from `GenericSchedulerDaemon.__init__`

- `services/scheduler/generic_scheduler_daemon.py`: removed `_process_dlq: bool = False` from `__init__` signature and its docstring entry
- `services/scheduler/scheduler_daemon_wrapper.py`: removed `_process_dlq=False` keyword argument from all 3 `SchedulerDaemon(...)` call sites (notification, status-transition, participant-action)

## Removed

N/A — parameters removed from function signatures; callers updated in-place.
