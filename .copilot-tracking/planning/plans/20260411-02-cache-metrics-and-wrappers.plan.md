---
applyTo: '.copilot-tracking/changes/20260411-02-cache-metrics-and-wrappers-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Cache Metrics and Read-Through Wrapper Consolidation

## Overview

Eliminate copy-pasted read-through cache patterns in `shared/discord/client.py` and add per-operation hit/miss counters and latency histograms for every cache read site across the codebase.

## Objectives

- Create `shared/cache/operations.py` with `CacheOperation` StrEnum, `cache_get` helper, and their OTel meters
- Add `_get_or_fetch` method to `DiscordAPIClient` replacing the 7 copy-pasted read-through sites
- Replace all existence-lookup `redis.get` / `redis.get_json` calls with `cache_get`
- Produce six named OTel metrics: `discord.cache.hits`, `discord.cache.misses`, `discord.cache.duration`, `cache.hits`, `cache.misses`, `cache.duration`
- `RedisClient` remains metrics-free

## Research Summary

### Project Files

- `shared/cache/client.py` — `RedisClient` low-level I/O; no metrics; unchanged
- `shared/discord/client.py` — 7 copy-pasted read-through sites; 1 double-checked-locking site (`get_guilds`)
- `services/api/auth/tokens.py` — 2 existence-lookup reads
- `services/api/auth/oauth2.py` — 1 existence-lookup read
- `services/api/auth/roles.py` — 1 read-through via `get_json`
- `services/api/services/display_names.py` — 2 looped existence reads
- `services/bot/auth/cache.py` — 2 existence reads

### External References

- #file:../research/20260411-02-cache-metrics-and-wrappers-research.md — full research findings

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [x] Phase 1: Create `shared/cache/operations.py`

- [x] Task 1.1: Write failing unit tests for `CacheOperation` and `cache_get`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 13-33)

- [x] Task 1.2: Implement `shared/cache/operations.py`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 34-60)

### [x] Phase 2: Add `_get_or_fetch` to `DiscordAPIClient`

- [x] Task 2.1: Write failing unit tests for `_get_or_fetch`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 63-80)

- [x] Task 2.2: Add OTel meters and `_get_or_fetch` to `shared/discord/client.py`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 81-108)

### [ ] Phase 3: Replace Copy-Pasted Read-Through Sites

- [ ] Task 3.1: Write failing unit tests asserting `_get_or_fetch` is used at all 7 sites
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 111-131)

- [ ] Task 3.2: Replace 7 copy-pasted read-through blocks in `discord/client.py` with `_get_or_fetch`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 132-162)

- [ ] Task 3.3: Fix `get_guilds` inner slow-path to use `_get_or_fetch`; leave pre-lock read raw
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 163-183)

### [ ] Phase 4: Replace Existence-Lookup Reads with `cache_get`

- [ ] Task 4.1: Write failing unit tests for `cache_get` usage at each existence-lookup site
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 186-212)

- [ ] Task 4.2: Replace existence-lookup reads in `tokens.py`, `oauth2.py`, `roles.py`, `display_names.py`, `bot/auth/cache.py`
  - Details: .copilot-tracking/planning/details/20260411-02-cache-metrics-and-wrappers-details.md (Lines 213-254)

## Dependencies

- `opentelemetry-api` (already installed)
- `time` stdlib
- `shared/cache/client.py` `RedisClient` and `get_redis_client` (already exist)
- No new packages required

## Success Criteria

- No bare `redis.get` + `json.loads` pattern remains in `shared/discord/client.py`
- All existence-lookup sites use `cache_get`
- `RedisClient` has zero metrics imports
- `CacheOperation` StrEnum covers all 15 operation names from the research
- `discord.cache.hits`, `discord.cache.misses`, `discord.cache.duration`, `cache.hits`, `cache.misses`, `cache.duration` metrics are produced
- All existing and new unit tests pass
