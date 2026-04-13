---
applyTo: '.copilot-tracking/changes/20260413-01-discord-member-fetch-performance-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Member Fetch Performance

## Overview

Eliminate ~27s cold-cache load on the game list by skipping participant Discord lookups in `list_games`, parallelizing remaining member fetches with `asyncio.gather`, and exposing a higher rate-limit budget for interactive requests.

## Objectives

- `GET /api/v1/games` cold-cache completes in ~2s (host resolution only, no participant Discord calls)
- `GET /api/v1/games/{id}` cold-cache completes in ~1.5s (parallel gather at up to 45 req/s)
- No Discord 429s under normal load
- All existing unit tests pass; new tests cover `global_max` threading and gather error handling

## Research Summary

### Project Files

- `shared/cache/client.py` (lines 106, 414, 460) - Lua rate limit script and claim functions to parameterize
- `shared/discord/client.py` (lines 198, 764, 790) - `_make_api_request`, `get_guild_member`, `get_guild_members_batch` to update
- `services/api/routes/games.py` (lines 403, 456, 897) - `list_games`, `get_game`, `_build_game_response` call sites
- `services/api/services/display_names.py` (lines 102, ~280) - display name service functions to thread `global_max` through
- `shared/cache/ttl.py` - add rate limit constants here

### External References

- #file:../research/20260413-01-discord-member-fetch-performance-research.md - full research with root cause analysis, recommended fixes, and implementation guidance

## Implementation Checklist

### [x] Phase 1: Add Rate Limit Constants

- [x] Task 1.1 (Tests): Write tests for rate limit constants
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 11-23)

- [x] Task 1.2 (Implement): Add constants to shared/cache/ttl.py
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 24-37)

### [x] Phase 2: Parameterize global_max in Rate Limit Infrastructure

- [x] Task 2.1 (Tests): Write failing tests for global_max parameter in claim functions
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 40-54)

- [x] Task 2.2 (Implement): Parameterize Lua script and cache client functions
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 55-73)

### [x] Phase 3: Thread global_max and Parallelize Discord Client

- [x] Task 3.1 (Tests): Write failing tests for global_max threading and asyncio.gather in Discord client
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 76-95)

- [x] Task 3.2 (Implement): Thread global_max and replace serial loop with asyncio.gather
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 96-112)

### [ ] Phase 4: Skip Participant Resolution in list_games and Use Interactive Budget in get_game

- [ ] Task 4.1 (Tests): Write failing tests for resolve_participants flag and interactive budget
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 115-141)

- [ ] Task 4.2 (Implement): Add resolve_participants flag and wire interactive budget
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 142-164)

### [ ] Phase 5: Parallel Host Fetch in list_games

- [ ] Task 5.1 (Tests): Write failing tests for prefetched_display_data and parallel host gathering
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 179-202)

- [ ] Task 5.2 (Implement): Pre-batch host IDs and gather responses in list_games
  - Details: .copilot-tracking/planning/details/20260413-01-discord-member-fetch-performance-details.md (Lines 204-232)

## Dependencies

- `asyncio` already imported in `shared/discord/client.py`
- `asyncio` and `collections.defaultdict` need to be imported in `services/api/routes/games.py`
- No new packages required

## Success Criteria

- `GET /api/v1/games` cold-cache completes in ~2s (host resolution only)
- `GET /api/v1/games/{id}` cold-cache completes in ~1.5s
- No 429s from Discord under normal load
- All existing unit tests pass; new tests cover gather error handling and `global_max` threading
- A host appearing in multiple games in `list_games` is fetched exactly once (deduplication)
