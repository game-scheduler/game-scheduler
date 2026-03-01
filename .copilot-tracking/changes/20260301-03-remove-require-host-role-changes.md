---
applyTo: '.copilot-tracking/changes/20260301-03-remove-require-host-role-changes.md'
---

<!-- markdownlint-disable-file -->

# Changes: Remove `require_host_role` Field

## Summary

Removed the dead `require_host_role` field from the database, ORM model, schemas, API routes, frontend, types, tests, and documentation.

---

## Added

- `alembic/versions/e8f2a91cb3d7_remove_require_host_role.py` — New Alembic migration that drops `require_host_role` from `guild_configurations` table with correct upgrade/downgrade.

---

## Modified

- `shared/models/guild.py` — Removed `require_host_role` mapped column.
- `shared/schemas/guild.py` — Removed `require_host_role` field from `GuildConfigCreateRequest`, `GuildConfigUpdateRequest`, and `GuildConfigResponse`.
- `services/api/routes/guilds.py` — Removed `require_host_role` kwargs from `_build_guild_config_response` and `create_guild_config` call sites.
- `tests/services/api/routes/test_guilds.py` — Removed all 10 `require_host_role` mock assignments and assertions.
- `tests/services/bot/test_guild_sync.py` — Removed `require_host_role` mock assignment and assertion at lines 461 and 480.
- `tests/services/api/services/test_guild_service.py` — Removed `require_host_role` from settings dicts and assertions in all three service test functions. (**Out of plan**: not listed in the original plan but found via grep; cleaned up to satisfy success criteria.)
- `tests/e2e/test_guild_routes_e2e.py` — Removed `"require_host_role" in config` assertion and replaced `{"require_host_role": True}` update payload with `{"bot_manager_role_ids": None}`. (**Out of plan**: not listed in the original plan but found via grep; cleaned up to satisfy success criteria.)
- `frontend/src/pages/GuildConfig.tsx` — Removed `requireHostRole` form state, data-load mapping, PUT payload field, checkbox UI, and unused `FormControlLabel`/`Checkbox` imports; restored missing `</Box>` closing tag for the flex column container.
- `frontend/src/pages/__tests__/GuildConfig.test.tsx` — Removed three explicit `getByRole('checkbox', …)` assertions (including `loads and displays guild configuration` and `handles save successfully` waitFor conditions, and the standalone `renders form fields with initial values` test block); replaced with page-loaded assertions on `'Server Configuration'` and `'Save Configuration'` text.
- `frontend/src/types/index.ts` — Removed `require_host_role: boolean` from `GuildConfigData` interface. (**Out of plan**: the plan did not list this file, but it is inside `frontend/src/` and appears in the grep search; removing it is required to satisfy the success criteria.)
- `docs/developer/database.md` — Removed `boolean require_host_role` from the `guild_configurations` entity in the Mermaid schema diagram. (**Out of plan**: not listed in the original plan but found via grep; cleaned up to satisfy success criteria.)
- `docs/GUILD-ADMIN.md` — Replaced "Require Host Role / Open Hosting" toggle documentation with `@everyone` template role guidance.

---

## Removed

_(No files deleted.)_
