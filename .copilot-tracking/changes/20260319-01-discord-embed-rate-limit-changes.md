<!-- markdownlint-disable-file -->

# Changes: Discord Embed Rate Limit Redesign

## Added

- `alembic/versions/b1d2e3f4a5c6_add_message_refresh_queue.py` — Alembic migration creating the `message_refresh_queue` table, `(channel_id, enqueued_at)` index, `notify_message_refresh_queue_changed` PGFunction, and AFTER INSERT trigger that fires `pg_notify('message_refresh_queue_changed', channel_id)`.
- `shared/models/message_refresh_queue.py` — `MessageRefreshQueue` SQLAlchemy ORM model mapping the new table with `id` (UUID PK), `game_id` (FK → `game_sessions.id` CASCADE), `channel_id` (String 20), and `enqueued_at` (DateTime with timezone).
- `tests/unit/shared/models/test_message_refresh_queue.py` — Unit tests verifying model instantiation, column types, FK target and CASCADE behaviour, and table name (7 tests, all passing).

## Modified

- `shared/models/__init__.py` — Added `MessageRefreshQueue` import and export.

- `shared/cache/client.py` — Added `_CHANNEL_RATE_LIMIT_LUA` module-level Lua script constant and full `claim_channel_rate_limit_slot(channel_id)` implementation: atomic sliding-window sorted-set check using Redis `EVAL`; returns wait_ms (0 = proceed); ZADD + PEXPIRE(5001) happen inside the Lua script when the slot is claimed.
- `tests/unit/shared/cache/test_claim_channel_rate_limit_slot.py` — 10 unit tests covering: empty window returns 0, spacing n=1..4 (1000/1000/1500/1500 ms), full window returns window_wait, key scoped to channel ID, Lua script contains PEXPIRE 5001, independent channels use separate keys, return value is always int.

## Modified (continued)

- `services/bot/events/handlers.py` — Replaced `CacheKeys.message_update_throttle()` and `CacheTTL.MESSAGE_UPDATE_THROTTLE` references with inline literals (`f"message_update:{game_id}"` and `2`) to break the dependency on the now-deleted symbols. Removed unused `CacheKeys` and `CacheTTL` imports. Throttle logic itself unchanged; Phase 5 will replace it with DB insert.

## Removed

- `shared/cache/ttl.py` `CacheTTL.MESSAGE_UPDATE_THROTTLE` — obsolete 2-second throttle TTL constant.
- `shared/cache/keys.py` `CacheKeys.message_update_throttle()` — obsolete game-keyed throttle cache key function.
- `tests/unit/shared/cache/test_ttl.py` `test_message_update_throttle_ttl` — test for removed constant.
- `tests/unit/shared/cache/test_keys.py` `test_message_update_throttle_key` — test for removed key function.
