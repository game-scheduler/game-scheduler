---
applyTo: '.copilot-tracking/changes/20260421-03-redis-acl-key-ownership-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Redis ACL Key Ownership

## Overview

Enforce Redis key ownership at the server level by renaming API-owned keys under an `api:` prefix, removing the bot's shared write access to `user_roles:*`, and wiring per-service ACL users so the API cannot write gateway data and the bot cannot write API session/auth data.

## Objectives

- Rename all API-owned keys to an `api:` prefix in `shared/cache/keys.py` and every caller
- Remove the bot's `user_roles:*` write path and delete the dead `guild_config:*` cache code
- Confirm `discord:member:*` ownership after the bot REST plan is complete, then rename to `api:member:*`
- Create a Redis ACL file granting `bot` and `api` users distinct key permissions and disable the `default` user
- Update compose files, env templates, and test fixtures to use per-service credentials

## Research Summary

### Project Files

- `shared/cache/keys.py` — all key prefix definitions; source of truth for namespace layout
- `shared/cache/client.py` — `RedisClient`/`SyncRedisClient`; single `REDIS_URL` env var; no per-service auth today
- `services/api/auth/tokens.py` — writes/reads/deletes `session:{id}`
- `services/api/auth/oauth2.py` — writes/deletes `oauth_state:{state}`
- `services/api/auth/roles.py` — reads/writes/deletes `user_roles:*`; reads `discord:guild_roles:*`
- `services/api/services/display_names.py` — writes `display:{guild_id}:{user_id}`
- `services/api/routes/maintainers.py` — scans/deletes `session:*`; deletes `discord:app_info`
- `shared/discord/client.py` — REST+Redis cache for `user_guilds:*`, `discord:app_info`, `discord:member:*`
- `services/bot/auth/cache.py` — `RoleCache`: reads/writes `user_roles:*` and dead `guild_config:*`
- `services/bot/auth/role_checker.py` — reads then writes `user_roles:*` after projection lookup
- `compose.yaml` — Valkey service; ACL file injected via `REDIS_COMMAND`/`--aclfile`

### External References

- #file:../research/20260421-03-redis-acl-key-ownership-research.md — full key ownership analysis and ACL topology

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow

## Implementation Checklist

### [x] Phase 1: Rename API-owned session/auth/display keys to `api:` prefix

- [x] Task 1.1: Update `CacheKeys` constants for session, oauth, display, user_guilds, and app_info
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 13-32)

- [x] Task 1.2: Update all callers of the renamed keys
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 33-51)

- [x] Task 1.3: Update test fixtures and assertions that reference the old key strings
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 52-64)

### [x] Phase 2: Transfer `user_roles:*` ownership to API; remove bot write path

- [x] Task 2.1: Rename `user_roles` key to `api:user_roles` and update `roles.py`
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 69-84)

- [x] Task 2.2: Remove bot `user_roles:*` write path from `role_checker.py`
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 85-105)

- [x] Task 2.3: Delete dead `guild_config:*` code from `cache.py` and `keys.py`
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 106-123)

### [x] Phase 3: Rename `discord:member:*` to `api:member:*` (prerequisite: bot REST plan complete)

- [x] Task 3.1: Verify `discord_format.py` has been migrated to `proj:member:*` projection reads
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 130-144)

- [x] Task 3.2: Rename `CacheKeys.member` and update `shared/discord/client.py` callers
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 145-160)

### [ ] Phase 4: ACL infrastructure wiring (prerequisite: bot REST plan complete)

- [ ] Task 4.1: Create `config/redis/users.acl` with `bot` and `api` user definitions
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 167-202)

- [ ] Task 4.2: Update compose files to mount ACL file and inject `--aclfile` flag
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 203-215)

- [ ] Task 4.3: Update `REDIS_URL` in env templates and compose overrides to include credentials
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 216-228)

- [ ] Task 4.4: Update test infrastructure to provision ACL users or use a privileged connection
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 229-242)

- [ ] Task 4.5: Verify ACL enforcement: `NOPERM` for cross-service writes; full integration suite passes
  - Details: .copilot-tracking/planning/details/20260421-03-redis-acl-key-ownership-details.md (Lines 243-255)

## Dependencies

- Bot REST elimination plan must be complete before Phase 3 and Phase 4
- Valkey 9.0.1 (already in `compose.yaml`) — Redis 7.x ACL support confirmed
- `redis://user:password@host:port/db` URL format supported by existing `RedisClient`

## Success Criteria

- All key constants and callers use `api:` prefix for API-owned data
- Bot `role_checker.py` reads directly from `proj:member:*` with no `user_roles:*` write path
- `valkey-cli ACL LIST` shows exactly `bot` and `api` users; `default` user disabled
- `SET discord:guild:any` as the `api` user returns `NOPERM`
- `SET api:session:any` as the `bot` user returns `NOPERM`
- All integration and e2e test suites pass
