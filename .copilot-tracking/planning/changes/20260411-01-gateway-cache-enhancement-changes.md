<!-- markdownlint-disable-file -->

# Changes: Gateway-Driven Cache Enhancement

**Plan**: .copilot-tracking/planning/plans/20260411-01-gateway-cache-enhancement.plan.md
**Details**: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md

---

## Phase 1: on_ready Redis Cache Rebuild — COMPLETE

### Added

- `tests/unit/bot/test_bot_ready.py` — Four unit tests verifying `on_ready` writes
  `discord:guild`, `discord:guild_channels`, `discord:channel`, and `discord:guild_roles`
  keys to Redis from the in-memory gateway cache without any REST calls.

### Modified

- `shared/cache/ttl.py` — Added `DISCORD_GUILD_ROLES: int = 300` constant (was missing;
  required by `on_ready` implementation and test assertions).
- `services/bot/bot.py` — Added `CacheKeys` and `CacheTTL` imports; added
  `_rebuild_redis_from_gateway` method that loops over `self.guilds` and writes guild,
  channel-list, per-channel, and role-list keys to Redis; updated `on_ready` to call
  `await self._rebuild_redis_from_gateway()` before `_recover_pending_workers`.

---
