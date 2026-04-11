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

---

## Phase 3: Remove Redundant fetch_channel in handlers.py — COMPLETE

### Modified

- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — Added three tests verifying
  `_validate_discord_channel` does not call `discord_api.fetch_channel`, returns `False`
  when `get_channel()` returns `None`, and returns `True` when `get_channel()` returns a
  valid channel.

- `services/bot/events/handlers.py` — Replaced `_validate_discord_channel` body: removed
  `get_discord_client()` / `await discord_api.fetch_channel(channel_id)` pre-check and
  replaced with `self.bot.get_channel(int(channel_id))`. This eliminates one REST call per
  `game.created` event that previously validated the channel before processing.

---

## Phase 4: Gateway Event Handlers — COMPLETE

### Added

- `tests/unit/bot/test_bot_events.py` — Nine unit tests verifying the six new gateway
  event handlers correctly write/invalidate Redis keys:
  - `on_guild_channel_create`: writes `discord:channel:{id}` and deletes `discord:guild_channels:{guild_id}`
  - `on_guild_channel_update`: updates `discord:channel:{id}` and deletes `discord:guild_channels:{guild_id}`
  - `on_guild_channel_delete`: deletes both `discord:channel:{id}` and `discord:guild_channels:{guild_id}`
  - `on_guild_role_create`, `on_guild_role_update`, `on_guild_role_delete`: each deletes `discord:guild_roles:{guild_id}`

### Modified

- `services/bot/bot.py` — Added six new gateway event handler methods between
  `_rebuild_redis_from_gateway` and `on_disconnect`. Channel handlers use
  `redis.set_json(..., None)` (no TTL) for individual channel keys and `redis.delete` for
  the guild channel list. Role handlers use invalidation-only (`redis.delete`) so the next
  `fetch_guild_roles` call rebuilds from Discord rather than storing stale role data.
