---
applyTo: '.copilot-tracking/changes/20260421-02-bot-rest-api-elimination-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Bot REST API Elimination

## Overview

Eliminate all non-message REST calls from the Discord bot by replacing `fetch_member`, `fetch_channel`, and `fetch_user` with in-memory gateway equivalents, and by moving guild sync out of `setup_hook` into `on_ready` using gateway-supplied data.

## Objectives

- Replace all `guild.fetch_member()` calls in `role_checker.py` with `guild.get_member()`
- Remove the Redis pre-check and REST fallback from three channel resolution helpers in `handlers.py`
- Replace `bot.fetch_user()` / `discord_api.fetch_user()` with `bot.get_user()` in two DM helpers in `handlers.py`
- Add `sync_guilds_from_gateway` and `sync_single_guild_from_gateway` to `guild_sync.py`
- Fix the broken `setup_hook` guild sync by moving it to `on_ready`; fix `on_guild_join` to use the event-supplied guild object
- Remove the `bot.fetch_channel()` fallback from `_run_sweep_worker`

## Research Summary

### Project Files

- `services/bot/auth/role_checker.py` — 3 `fetch_member` call sites; 14 test mock references
- `services/bot/events/handlers.py` — `_validate_channel_for_refresh`, `_get_bot_channel`, `_fetch_channel_and_message`, `_send_dm`, `_handle_clone_confirmation`
- `services/bot/bot.py` — `setup_hook` broken guild sync, `on_guild_join` unnecessary full fetch, `_run_sweep_worker` REST fallback
- `services/bot/guild_sync.py` — `sync_all_bot_guilds` REST-based; needs two new gateway-aware functions

### External References

- #file:../research/20260421-02-bot-rest-api-elimination-research.md — all key discoveries, recommended approach, implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [x] Phase 1: role_checker.py — Replace `fetch_member` with `get_member`

- [x] Task 1.1: Update unit tests to assert `get_member` is called and `fetch_member` is NOT called
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 13–31)

- [x] Task 1.2: Replace `guild.fetch_member()` with `guild.get_member()` in all three permission-check methods
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 32–47)

### [x] Phase 2: handlers.py — Eliminate Channel REST Fallbacks

- [x] Task 2.1: Update unit tests for `_validate_channel_for_refresh`, `_get_bot_channel`, `_fetch_channel_and_message` to assert no REST calls
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 50–69)

- [x] Task 2.2: Strip `discord_api.fetch_channel()` pre-check and `bot.fetch_channel()` fallback from three channel helpers
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 70–87)

### [x] Phase 3: handlers.py — Eliminate User Fetch REST Calls

- [x] Task 3.1: Update unit tests for `_send_dm` and `_handle_clone_confirmation`; add None-user skip test cases
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 90–113)

- [x] Task 3.2: Replace `bot.fetch_user()` / `discord_api.fetch_user()` with `bot.get_user()` in both DM helpers
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 114–130)

### [ ] Phase 4: guild_sync.py — Add Gateway-Aware Sync Functions

- [ ] Task 4.1: Create stubs for `sync_guilds_from_gateway` and `sync_single_guild_from_gateway`; write xfail tests
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 133–153)

- [ ] Task 4.2: Implement both functions using `guild.channels` from gateway data; remove xfail markers
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 154–182)

### [ ] Phase 5: bot.py — Fix Startup Sync and Remove Remaining REST Fallbacks

- [ ] Task 5.1: Remove `sync_all_bot_guilds` from `setup_hook`; add `sync_guilds_from_gateway` call in `on_ready` after `_rebuild_redis_from_gateway()`
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 185–204)

- [ ] Task 5.2: Replace `sync_all_bot_guilds` in `on_guild_join` with `sync_single_guild_from_gateway(guild=guild, db=db)`
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 205–222)

- [ ] Task 5.3: Remove `bot.fetch_channel()` fallback from `_run_sweep_worker`; log warning and skip on None
  - Details: .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md (Lines 223–239)

## Dependencies

- `discord.Intents(members=True)` and `chunk_guilds_at_startup=True` already present — no config changes needed
- Phase 4 must complete before Phase 5 (Tasks 5.1 and 5.2 depend on the new sync functions)

## Success Criteria

- No `bot.fetch_member`, `bot.fetch_user`, `discord_api.fetch_user`, or `bot.fetch_channel` calls remain in `role_checker.py`, `handlers.py`, or `bot.py`
- `sync_all_bot_guilds` is no longer called from `setup_hook` or `on_guild_join`
- `sync_guilds_from_gateway` and `sync_single_guild_from_gateway` exist in `guild_sync.py` with full unit test coverage
- All unit test suites pass with no skips after changes
