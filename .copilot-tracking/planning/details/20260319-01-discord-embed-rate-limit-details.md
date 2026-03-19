<!-- markdownlint-disable-file -->

# Task Details: Discord Embed Rate Limit Redesign

## Research Reference

**Source Research**: #file:../research/20260319-01-discord-embed-rate-limit-research.md

---

## Phase 1: Database Foundation

### Task 1.1: Alembic Migration for `message_refresh_queue` Table and `pg_notify` Trigger

Create a new Alembic migration in `alembic/versions/` using the `PGFunction` +
`op.execute` pattern established in the initial schema migration. The migration must:

1. Create the `message_refresh_queue` table with `id` (UUID pk), `game_id` (FK to
   `game_sessions` ON DELETE CASCADE), `channel_id` (VARCHAR 20), and `enqueued_at`
   (TIMESTAMPTZ server default NOW()), plus the `(channel_id, enqueued_at)` index.
2. Create a `PGFunction` `notify_message_refresh_queue_changed` that executes
   `pg_notify('message_refresh_queue_changed', NEW.channel_id::text)`.
3. Register an `AFTER INSERT FOR EACH ROW` trigger calling the function.
4. Include a clean downgrade: drop trigger, drop function, drop table.

- **Files**:
  - `alembic/versions/<revision_id>_add_message_refresh_queue.py` — new migration file
- **Success**:
  - `alembic upgrade head` completes without error
  - Table exists with correct schema and index
  - Trigger fires on INSERT and delivers `pg_notify` payload equal to the inserted `channel_id`
  - `alembic downgrade -1` removes table, trigger, and function cleanly
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 102-125) —
    `message_refresh_queue` table schema, trigger definition, and NOTIFY payload
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 30-38) —
    verified `PGFunction` + trigger migration pattern from initial schema
- **Dependencies**:
  - `alembic-utils` `PGFunction` (already available)
  - `game_sessions` table exists (FK target)

### Task 1.2: `MessageRefreshQueue` SQLAlchemy ORM Model (TDD – New Model)

Add `MessageRefreshQueue` to `shared/models/` following existing model conventions.
The model maps the `message_refresh_queue` table: `id` (UUID pk, `gen_random_uuid()`
server default), `game_id` (FK to `game_sessions.id` ON DELETE CASCADE), `channel_id`
(String 20), `enqueued_at` (server default NOW()). Export the model from
`shared/models/__init__.py`. Include unit tests verifying column types and FK relationship.

- **Files**:
  - `shared/models/message_refresh_queue.py` — new ORM model
  - `shared/models/__init__.py` — export the new model
  - `tests/unit/shared/models/test_message_refresh_queue.py` — new unit test
- **Success**:
  - Model instantiates without error
  - Column definitions and FK relationship match the migration schema
  - Unit tests pass
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 102-115) —
    `message_refresh_queue` table schema
- **Dependencies**:
  - Task 1.1 complete

---

## Phase 2: Redis Rate Limit Tracking — `claim_channel_rate_limit_slot` (TDD)

### Task 2.1: Stub `claim_channel_rate_limit_slot` on `RedisClient`

Add an async method `claim_channel_rate_limit_slot(channel_id: str) -> int` to `RedisClient`
in `shared/cache/client.py` (class defined at line 36). Stub body: `raise NotImplementedError`.
This establishes the interface used by `_channel_worker` before tests are written.

- **Files**:
  - `shared/cache/client.py` — add stub method to `RedisClient`
- **Success**:
  - Method is importable and raises `NotImplementedError` when awaited
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 93-117) —
    sorted set algorithm, key naming `channel_rate_limit:{id}`, Lua script logic
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Write xfail Unit Tests for `claim_channel_rate_limit_slot` (RED)

Write unit tests with `@pytest.mark.xfail(strict=True)` covering:
(a) Returns 0 when the sorted set is empty (immediate — no edits in the 5s window).
(b) Returns correct `wait_ms` for n=1..4 edits per the graduated spacing table
(0, 1000, 1000, 1500, 1500 ms).
(c) Returns `window_wait_ms` (oldest_edit_ts + 5000 - now_ms) when n ≥ 5.
(d) Redis key carries a PEXPIRE of 5001ms and disappears after 5s of inactivity.

- **Files**:
  - `tests/unit/shared/cache/test_claim_channel_rate_limit_slot.py` — new test file
- **Success**:
  - All new tests carry `@pytest.mark.xfail(strict=True)` and fail as expected
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 79-117) —
    graduated spacing table and sorted set algorithm
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Implement `claim_channel_rate_limit_slot` Lua Script (GREEN)

Implement the atomic Lua script executed via `EVAL`. The script:

1. `ZREMRANGEBYSCORE(key, 0, now_ms - 5000)` — prune stale timestamps.
2. `n = ZCARD(key)` — count edits in the window.
3. `spacing_wait_ms = last_edit_ts + SPACING[min(n, 4)] * 1000 - now_ms`
   (SPACING = [0, 1, 1, 1.5, 1.5]).
4. `window_wait_ms = oldest_edit_ts + 5000 - now_ms` only when n ≥ 5.
5. Return `max(spacing_wait_ms, window_wait_ms, 0)`.
   If `wait_ms == 0`, record the current timestamp via `ZADD(key, now_ms, now_ms)` and
   `PEXPIRE(key, 5001)`. Remove all `@pytest.mark.xfail` markers from Task 2.2 tests
   without modifying any assertion.

- **Files**:
  - `shared/cache/client.py` — full implementation of `claim_channel_rate_limit_slot`
- **Success**:
  - All Task 2.2 tests pass with xfail markers removed
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 93-117) —
    full sorted set and Lua script algorithm
- **Dependencies**:
  - Task 2.2 complete

### Task 2.4: Remove Obsolete Cache Constants and Add Edge Case Tests

Delete `MESSAGE_UPDATE_THROTTLE` from `shared/cache/ttl.py` and `message_update_throttle`
key function from `shared/cache/keys.py`. Resolve any import sites that reference them.
Add edge case tests to `test_claim_channel_rate_limit_slot.py`: independent channels do
not share state; key auto-expires after 5s of inactivity.

- **Files**:
  - `shared/cache/ttl.py` — remove `MESSAGE_UPDATE_THROTTLE` constant
  - `shared/cache/keys.py` — remove `message_update_throttle` key function
  - `tests/unit/shared/cache/test_claim_channel_rate_limit_slot.py` — add edge cases
- **Success**:
  - No remaining references to `MESSAGE_UPDATE_THROTTLE` or `message_update_throttle`
  - All unit tests pass
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 175-183) —
    complete removal checklist
- **Dependencies**:
  - Task 2.3 complete

---

## Phase 3: asyncpg LISTEN Listener — `MessageRefreshListener` (TDD)

### Task 3.1: Stub `MessageRefreshListener` Class

Create `services/bot/message_refresh_listener.py` defining a `MessageRefreshListener`
class with:

- `__init__(self, bot_db_url: str, spawn_worker_cb)` — stores the URL and callback.
- `_channel_workers: dict` initialized as `{}`.
- `async def start(self) -> None` — stub, raises `NotImplementedError`.
- `def _on_notify(self, conn, pid, channel, payload) -> None` — stub, raises `NotImplementedError`.

- **Files**:
  - `services/bot/message_refresh_listener.py` — new file with stubbed class
- **Success**:
  - Class is importable; both stub methods raise `NotImplementedError`
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 126-134) —
    listener interface specification and `_on_notify` callback algorithm
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Write xfail Unit Tests for `MessageRefreshListener` (RED)

Write unit tests with `@pytest.mark.xfail(strict=True)` covering:

- `start()` opens a dedicated asyncpg connection using the provided `bot_db_url`.
- `add_listener` is called with `'message_refresh_queue_changed'` and `self._on_notify`.
- A `_on_notify` call with a new `channel_id` payload invokes `spawn_worker_cb(channel_id)`.
- A repeated `_on_notify` call for the same `channel_id` does NOT invoke the callback again.

- **Files**:
  - `tests/unit/services/bot/test_message_refresh_listener.py` — new test file
- **Success**:
  - All new tests carry `@pytest.mark.xfail(strict=True)` and fail as expected
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 126-134) —
    listener algorithm
- **Dependencies**:
  - Task 3.1 complete

### Task 3.3: Implement `MessageRefreshListener` (GREEN)

Implement `start()`: open a dedicated asyncpg connection (not from the SQLAlchemy pool)
using `self._bot_db_url`, call `await conn.add_listener('message_refresh_queue_changed',
self._on_notify)`, then keep the coroutine alive. Implement `_on_notify`: extract
`discord_channel_id` from `payload`; if not in `self._channel_workers`, invoke
`self._spawn_worker_cb(discord_channel_id)` and store the resulting task. Remove all
xfail markers without modifying assertions.

- **Files**:
  - `services/bot/message_refresh_listener.py` — full implementation
- **Success**:
  - All Task 3.2 tests pass with xfail markers removed
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 126-134)
- **Dependencies**:
  - Task 3.2 complete

### Task 3.4: Refactor and Edge Case Tests for `MessageRefreshListener`

Add edge case unit tests: asyncpg connection error on `start()` is handled and logged;
unknown or empty payload in `_on_notify` is ignored without raising; completed worker
tasks are removed from `_channel_workers` so the dict does not grow unbounded.

- **Files**:
  - `tests/unit/services/bot/test_message_refresh_listener.py` — extended with edge cases
- **Success**:
  - All tests pass; no regressions
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 126-134)
- **Dependencies**:
  - Task 3.3 complete

---

## Phase 4: Per-Channel Worker — `_channel_worker` (TDD)

### Task 4.1: Stub `_channel_worker` in `EventHandlers`

Add `async def _channel_worker(self, discord_channel_id: str) -> None` to `EventHandlers`
in `services/bot/events/handlers.py`. Body: `raise NotImplementedError`. Add
`_channel_workers: dict[str, asyncio.Task]` to `EventHandlers.__init__`.

- **Files**:
  - `services/bot/events/handlers.py` — add stub method and dict attribute
- **Success**:
  - Method exists; calling it raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 135-166) —
    worker loop pseudocode
- **Dependencies**:
  - Phase 3 complete

### Task 4.2: Write xfail Unit Tests for `_channel_worker` (RED)

Write unit tests with `@pytest.mark.xfail(strict=True)` covering:

- Worker calls `claim_channel_rate_limit_slot` and sleeps the returned `wait_ms/1000` seconds.
- Worker queries DB for `message_refresh_queue` rows and calls `message.edit` with current game state.
- 429 response from Discord causes the worker to sleep `retry_after` seconds and retry without
  losing the queue row (DB row survives until after a successful edit).
- Worker exits cleanly when the DB query returns no rows for its channel.
- After a successful Discord edit, consumed queue rows (`enqueued_at <= T_cut`) are deleted.

- **Files**:
  - `tests/unit/services/bot/events/test_channel_worker.py` — new test file
- **Success**:
  - All new tests carry `@pytest.mark.xfail(strict=True)` and fail as expected
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 135-166) —
    worker loop pseudocode with T_cut, 429 retry, and exit condition
- **Dependencies**:
  - Task 4.1 complete

### Task 4.3: Implement `_channel_worker` Full Loop (GREEN)

Implement the full worker loop per the research pseudocode:

1. Call `claim_channel_rate_limit_slot(discord_channel_id)` → `wait_ms`.
2. If `wait_ms > 0`, `await asyncio.sleep(wait_ms / 1000)`.
3. Set `T_cut = now()`.
4. Query DB: `SELECT 1 FROM message_refresh_queue WHERE channel_id = ... LIMIT 1`.
5. If no row, break and deregister from `_channel_workers`.
6. Fetch current game state; call `discord_message.edit(embed=...)`.
7. On 429: read `retry_after`, sleep, `continue`.
8. `DELETE FROM message_refresh_queue WHERE channel_id = ... AND enqueued_at <= T_cut`.
9. Loop (picks up rows inserted during the edit call).
   Remove all xfail markers from Task 4.2 tests without modifying assertions.

- **Files**:
  - `services/bot/events/handlers.py` — implement `_channel_worker`
- **Success**:
  - All Task 4.2 tests pass with xfail markers removed
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 135-166)
- **Dependencies**:
  - Task 4.2 complete

### Task 4.4: Refactor and Multi-Game Edge Case Tests for `_channel_worker`

Add edge case tests: two games in the same channel correctly share the per-channel rate
limit bucket (only one worker, one call to `claim_channel_rate_limit_slot` at a time);
a burst of 5 simultaneous queue inserts produces edit calls at approximately 0, 1, 2,
3.5s intervals; a non-429 Discord API error is logged and does not terminate the worker.

- **Files**:
  - `tests/unit/services/bot/events/test_channel_worker.py` — extended with edge cases
- **Success**:
  - All edge case tests pass; full unit test suite is green
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 75-97) —
    graduated spacing table and per-channel bucket sharing
- **Dependencies**:
  - Task 4.3 complete

---

## Phase 5: Event Handler Replacement and Final Cleanup

### Task 5.1: Update Existing Tests for `_handle_game_updated` to Expect DB Insert (RED)

Locate the current unit tests for `_handle_game_updated`, `_set_message_refresh_throttle`,
and `_delayed_refresh` in `tests/unit/services/bot/events/test_handlers.py`. Remove the
tests for `_set_message_refresh_throttle` and `_delayed_refresh` entirely (these methods
are being deleted). Rewrite `_handle_game_updated` test(s) to assert that handling a
`game_updated` event inserts a row into `message_refresh_queue` with the correct `game_id`
and `channel_id`. Mark these assertions `@pytest.mark.xfail(strict=True)` since the live
implementation still uses the old Redis throttle path.

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — update and remove tests
- **Success**:
  - Old throttle tests removed; new `_handle_game_updated` test(s) run as expected xfail
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 60-67) —
    current design problems driving the replacement
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 122-125) —
    new insert path specification
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Replace Throttle Logic with DB Insert and Add Startup Recovery (GREEN)

In `services/bot/events/handlers.py`, rewrite `_handle_game_updated`:

- Remove the Redis TTL check and `asyncio.create_task(_delayed_refresh(...))` calls.
- Replace with: fetch `channel_id` from the game record; execute
  `INSERT INTO message_refresh_queue (game_id, channel_id) VALUES (...)`.
  In `services/bot/bot.py`, add startup recovery to `on_ready` and `on_resumed`:
  query `SELECT DISTINCT channel_id FROM message_refresh_queue`; for each result,
  if no worker exists for that channel, spawn one via `MessageRefreshListener`.
  Remove all xfail markers from Task 5.1 tests without modifying assertions.

- **Files**:
  - `services/bot/events/handlers.py` — replace `_handle_game_updated` body
  - `services/bot/bot.py` — add startup recovery in `on_ready` and `on_resumed`
- **Success**:
  - All Task 5.1 tests pass with xfail markers removed
  - `on_ready` scan spawns workers for any channels with pending queue rows
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 122-125) —
    insert path
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 167-174) —
    startup recovery query
- **Dependencies**:
  - Task 5.1 complete

### Task 5.3: Delete Obsolete Methods and Verify No Regressions

Delete `_set_message_refresh_throttle`, `_delayed_refresh`, `_pending_refreshes` (set),
and `_background_tasks` (set) from `services/bot/events/handlers.py`. Confirm that the
full unit test suite passes and no references to the removed names remain in the codebase.

- **Files**:
  - `services/bot/events/handlers.py` — delete four obsolete methods/attributes
- **Success**:
  - `grep` finds no remaining references to `_set_message_refresh_throttle`,
    `_delayed_refresh`, `_pending_refreshes`, or `_background_tasks`
  - Full unit test suite is green
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 175-183) —
    complete list of items to remove
- **Dependencies**:
  - Task 5.2 complete

---

## Phase 6: Integration Tests

### Task 6.1: Integration Test — Queue Trigger Fires Correct `pg_notify` Payload

Create `tests/integration/test_message_refresh_queue.py` to hold all three
integration test classes (Tasks 6.1, 6.2, and 6.3). Follow the
`PostgresNotificationListener` + `admin_db_url_sync` + `admin_db_sync` pattern
from `tests/integration/test_notification_daemon.py`.

Test steps:

1. Open a `PostgresNotificationListener(admin_db_url_sync)` and call
   `listener.listen("message_refresh_queue_changed")`
2. Create a game environment via `test_game_environment()`; insert one row into
   `message_refresh_queue` via `admin_db_sync` with `game_id=env["game"]["id"]`
   and `channel_id=env["channel"]["channel_id"]`; call `admin_db_sync.commit()`
3. Call `listener.wait_for_notification(timeout=2.0)`, assert `received is True`,
   and assert `payload == env["channel"]["channel_id"]`

The existing `admin_db_sync` setup cleanup (CASCADE delete from `game_sessions`)
removes any leftover queue rows at the start of each subsequent test, so no
additional cleanup fixture is needed.

- **Files**:
  - `tests/integration/test_message_refresh_queue.py` — new file
- **Success**:
  - LISTEN connection receives a NOTIFY with `payload == channel_id` immediately
    after the INSERT is committed
  - Guards the Alembic migration trigger function correctness
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 213-230) — addendum test 1 description
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 76-100) — trigger function SQL in migration
- **Dependencies**:
  - Phase 1 complete (migration applied; `message_refresh_queue` table and trigger exist)

### Task 6.2: Integration Test — `MessageRefreshListener` Receives `channel_id` via asyncpg

Add `TestMessageRefreshListenerIntegration` to
`tests/integration/test_message_refresh_queue.py`. This is an `async def` test
exercising the full asyncpg LISTEN pathway. Use `bot_db_url` for the listener
(BYPASS-RLS, matching production bot credentials) and `admin_db_url` for the
inserting connection.

Test steps:

1. Create `received_payloads: list[str] = []` and `received_event = asyncio.Event()`
2. Define `spawn_cb(channel_id: str) -> asyncio.Task` that appends `channel_id`
   to the list, sets `received_event`, and returns
   `asyncio.create_task(asyncio.sleep(0))`
3. Construct `listener = MessageRefreshListener(bot_db_url, spawn_cb)` and launch
   `task = asyncio.create_task(listener.start())`
4. `await asyncio.sleep(0.3)` to allow the asyncpg LISTEN connection to establish
5. Open a direct asyncpg admin connection:
   `conn = await asyncpg.connect(admin_db_url.replace("postgresql+asyncpg://", "postgresql://"))`;
   execute the `INSERT INTO message_refresh_queue (game_id, channel_id) VALUES ($1, $2)`;
   `await conn.close()` so the transaction auto-commits
6. `await asyncio.wait_for(received_event.wait(), timeout=2.0)`
7. `task.cancel(); await asyncio.gather(task, return_exceptions=True)`
8. Assert `received_payloads == [env["channel"]["channel_id"]]`

- **Files**:
  - `tests/integration/test_message_refresh_queue.py` — add `TestMessageRefreshListenerIntegration`
- **Success**:
  - `spawn_cb` fires with the correct `channel_id`; `received_event` set within 2 s
  - Guards `MessageRefreshListener._on_notify` parsing and asyncpg `add_listener` wiring
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 231-242) — addendum test 2 description
- **Dependencies**:
  - Task 6.1 complete
  - Phase 3 complete (`MessageRefreshListener` fully implemented)
  - `bot_db_url` and `admin_db_url` fixtures in `tests/conftest.py` (Lines 200-215)

### Task 6.3: Integration Test — Startup Recovery Query Returns Pending Channels

Add `TestMessageRefreshQueueRecovery` to
`tests/integration/test_message_refresh_queue.py`. This is a pure sync SQL test;
no async listener or NOTIFY receipt is needed.

Test steps:

1. Delete all existing `message_refresh_queue` rows via `admin_db_sync` to start
   with a known-empty table
2. Create a game environment via `test_game_environment()`; insert two rows with
   `game_id=env["game"]["id"]` but two distinct `channel_id` strings (e.g.,
   `"111111111111111111"` and `"222222222222222222"`); commit
3. Execute the exact recovery query used in `services/bot/bot.py`:
   `SELECT DISTINCT channel_id FROM message_refresh_queue`
4. Assert both expected `channel_id` strings appear in the result set

Use the identical SQL text as the `on_ready` recovery query so that any future
change to that query will also break this test.

- **Files**:
  - `tests/integration/test_message_refresh_queue.py` — add `TestMessageRefreshQueueRecovery`
- **Success**:
  - Both distinct `channel_id` values returned by the recovery SELECT
  - Guards the `on_ready` recovery query against schema or logic regressions
- **Research References**:
  - #file:../research/20260319-01-discord-embed-rate-limit-research.md (Lines 243-256) — addendum test 3 description
- **Dependencies**:
  - Task 6.1 complete
  - Phase 5 complete (startup recovery query implemented in `services/bot/bot.py`)

---

## Dependencies

- `asyncpg~=0.30.0` (already in `pyproject.toml`)
- `BOT_DATABASE_URL` environment variable (already configured)
- Redis sorted set commands: `ZADD`, `ZCARD`, `ZREMRANGEBYSCORE`, `PEXPIRE` (available)
- `alembic-utils` `PGFunction` (already used in migrations)

## Success Criteria

- First join after idle: Discord embed updates immediately (no artificial delay)
- Burst of N joins on same game: edits fire at 0, 1, 2, 3.5, 5s (max 1.5s wait per user)
- Multiple games in same channel: correctly share the per-channel rate limit bucket
- Bot crash mid-burst: pending queue rows survive; workers restart on `on_ready` / `on_resumed`
- System idle: no background tasks, no Redis keys, no DB rows remain
- No 429 responses from Discord under normal operation
