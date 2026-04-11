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

## Phase 2: role_checker.py — Use In-Memory Cache — COMPLETE

### Modified

- `tests/unit/services/bot/auth/test_role_checker.py` — Added six tests verifying each
  of the five methods (`get_user_role_ids`, `get_guild_roles`, `check_manage_guild_permission`,
  `check_manage_channels_permission`, `check_administrator_permission`, `check_game_host_permission`)
  does not call `fetch_guild()`; updated all existing tests that set up `fetch_guild` as
  `AsyncMock` to instead set up `get_guild` as `MagicMock`.

- `services/bot/auth/role_checker.py` — Replaced `await self.bot.fetch_guild(int(guild_id))`
  with `self.bot.get_guild(int(guild_id))` (synchronous, in-memory, no `await`) in all five
  methods: `get_user_role_ids` (line 78), `get_guild_roles` (line 114),
  `check_manage_guild_permission` (line 151), `check_manage_channels_permission` (line 177),
  `check_administrator_permission` (line 203). Eliminates at least one REST call per role
  check that misses the `user_roles` Redis cache.
