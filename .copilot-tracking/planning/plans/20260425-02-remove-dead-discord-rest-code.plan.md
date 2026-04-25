---
applyTo: '.copilot-tracking/changes/20260425-02-remove-dead-discord-rest-code-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove Dead Discord REST Methods

## Overview

Delete all dead `DiscordAPIClient` REST methods, their oauth2 wrapper, dead `CacheOperation` enum entries, and all associated unit tests.

## Objectives

- Remove 9 dead methods from `DiscordAPIClient` (guild fetching, guild member fetching, user fetching, and rate-limit helpers)
- Remove 3 dead module-level batch OTEL metric declarations
- Remove `oauth2.get_user_guilds()` wrapper that has no production callers
- Remove 3 dead `CacheOperation` enum entries (`FETCH_USER`, `GET_GUILD_MEMBER`, `GET_USER_GUILDS`)
- Remove ~50 dead unit tests across two test files
- Update 2 active `TestGetOrFetch` tests that reference the removed `CacheOperation.FETCH_USER` entry

## Research Summary

### Project Files

- `shared/discord/client.py` — 9 dead methods and 3 dead batch metric declarations
- `services/api/auth/oauth2.py` — dead `get_user_guilds()` wrapper
- `shared/cache/operations.py` — 3 dead enum entries (`FETCH_USER`, `GET_GUILD_MEMBER`, `GET_USER_GUILDS`)
- `tests/unit/shared/discord/test_discord_api_client.py` — dead test classes and individual test methods
- `tests/unit/services/api/auth/test_oauth2.py` — one dead test in `TestOAuth2Flow`

### External References

- #file:../research/20260425-02-remove-dead-discord-rest-code-research.md — full method-by-method active/dead classification, dead test inventory, and recommended approach

## Implementation Checklist

### [x] Phase 1: Remove dead methods from shared/discord/client.py

- [x] Task 1.1: Remove batch OTEL metric declarations (\_batch_size_histogram, \_batch_not_found_counter, \_batch_duration_histogram)
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 11–21)

- [x] Task 1.2: Remove guild fetching method group (get_guilds, \_handle_rate_limit_response, \_process_guilds_response, \_fetch_guilds_uncached)
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 22–35)

- [x] Task 1.3: Remove user and guild member method group (fetch_user, get_guild_member, get_guild_members_batch, get_current_user_guild_member)
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 36–51)

- [x] Task 1.4: Remove module-level fetch_user_display_name_safe
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 52–61)

### [x] Phase 2: Remove dead code from oauth2.py and cache/operations.py

- [x] Task 2.1: Remove get_user_guilds() from services/api/auth/oauth2.py
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 64–74)

- [x] Task 2.2: Remove FETCH_USER, GET_GUILD_MEMBER, GET_USER_GUILDS from CacheOperation enum
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 75–88)

### [x] Phase 3: Remove dead tests from test_discord_api_client.py

- [x] Task 3.1: Delete TestGuildMethods class (entire)
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 91–100)

- [x] Task 3.2: Delete TestUnifiedTokenFunctionality class (entire)
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 101–110)

- [x] Task 3.3: Remove test_fetch_user_cache_miss and test_fetch_user_cache_hit from TestCachedResourceMethods
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 111–122)

- [x] Task 3.4: Delete standalone test_get_guilds_uses_api_base_url, TestProcessGuildsResponseHttpError, and TestFetchGuildsUncachedSafetyRaise
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 123–133)

- [x] Task 3.5: Remove 3 test*fetch_user_display_name_safe*\* tests from TestHelperFunctions
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 134–146)

- [x] Task 3.6: Remove 2 dead tests from TestReadThroughDelegatesToGetOrFetch; delete TestGetCurrentUserGuildMember
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 147–157)

- [x] Task 3.7: Update 2 active TestGetOrFetch tests — replace CacheOperation.FETCH_USER with CacheOperation.FETCH_GUILD
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 158–169)

### [x] Phase 4: Remove dead tests from test_oauth2.py

- [x] Task 4.1: Remove test_get_user_guilds from TestOAuth2Flow; remove unused import
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 172–181)

### [x] Phase 5: Verify

- [x] Task 5.1: Run unit tests and grep to confirm removed names are gone
  - Details: .copilot-tracking/planning/details/20260425-02-remove-dead-discord-rest-code-details.md (Lines 184–193)

## Dependencies

- No external dependencies — all production callers were removed in prior work

## Success Criteria

- All unit tests pass
- `CacheOperation` enum contains no `FETCH_USER`, `GET_GUILD_MEMBER`, or `GET_USER_GUILDS` entries
- `grep -rn "get_guild_members_batch\|fetch_user_display_name_safe\|CacheOperation\.FETCH_USER\|CacheOperation\.GET_GUILD_MEMBER\|CacheOperation\.GET_USER_GUILDS" services/ shared/ tests/ --include="*.py"` returns zero results
