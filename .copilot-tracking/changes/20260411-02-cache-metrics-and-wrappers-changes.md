<!-- markdownlint-disable-file -->

# Changes: Cache Metrics and Read-Through Wrapper Consolidation

## Overview

Tracking file for implementation of `shared/cache/operations.py` and per-operation OTel cache metrics.

---

## Added

- `shared/cache/operations.py` — New module with `CacheOperation` StrEnum (16 members) and `cache_get` coroutine with `cache.hits`, `cache.misses`, and `cache.duration` OTel metrics.
- `tests/unit/shared/cache/test_operations.py` — 8 unit tests covering `CacheOperation` membership and `cache_get` hit/miss counter and histogram behaviour.

## Modified

- `shared/discord/client.py` — Added `import time`, `from opentelemetry import metrics`, `from shared.cache.operations import CacheOperation`; three module-level OTel meters (`discord.cache.hits`, `discord.cache.misses`, `discord.cache.duration`); `_get_or_fetch` read-through cache helper method on `DiscordAPIClient`.
- `tests/unit/shared/discord/test_discord_api_client.py` — Added `TestGetOrFetch` class with 5 unit tests covering hit return, miss fetch, Redis write-back, and duration histogram for both hit and miss paths.
- `tests/unit/scripts/test_check_lint_suppressions.py` — Cleared `APPROVED_OVERRIDES` from the environment inside `_run_main_with_args` so tests are isolated from the parent commit environment (out-of-plan bug fix: test failed when commit was run with `APPROVED_OVERRIDES=1`).

## Removed
