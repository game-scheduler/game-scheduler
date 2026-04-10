<!-- markdownlint-disable-file -->

# Task Research Notes: Embed Deletion Sweep Hardening and Test Coverage

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - `_sweep_deleted_embeds` (line ~243) — no concurrency guard; back-to-back `on_resumed` events spawn independent worker pools, doubling Discord rate-limit pressure and publishing duplicate `EMBED_DELETED` events
  - `_run_sweep_worker` — `except Exception` does NOT swallow `CancelledError` (which is `BaseException` in Python 3.8+), so task cancellation propagates cleanly
  - `asyncio.gather(*workers)` — cancelling the parent task cancels all workers at their next `await` point
  - No OTel meter; only `tracer = trace.get_tracer(__name__)` exists; no sweep metrics
  - `on_ready` and `on_resumed` both call `_sweep_deleted_embeds` directly (not as a background task), so the coroutine runs inline and there is no `asyncio.Task` handle to cancel

- `services/retry/retry_daemon.py` (lines 47–88)
  - Canonical metrics pattern: `meter = metrics.get_meter(__name__)`, `meter.create_counter(...)`, `meter.create_histogram(...)`
  - Model for all new sweep metrics

- `services/api/services/embed_deletion_consumer.py`
  - `_handle_embed_deleted` — no real-DB coverage in unit tests (mocks `get_bypass_db_session` and `GameService`)
  - Consumer is idempotent: unknown `game_id` is silently dropped

- `tests/integration/test_participant_drop_event.py`
  - Direct-call pattern for bot-layer handlers without a running bot container
  - Model for both new integration tests

- `tests/e2e/helpers/discord.py`
  - `wait_for_message`, `wait_for_message_update`, `wait_for_message_deleted` all present
  - No `delete_message` method — required for Case 1 e2e test

- `compose.e2e.yaml` (line 66)
  - `PYTEST_RUNNING: "1"` already set for bot container
  - Bot shares `app-network` with e2e-tests container — `http://bot:8089` reachable with no compose changes

- `pyproject.toml` (line 36)
  - `aiohttp~=3.11.0` already a project dependency — no new packages needed for test server

- `shared/telemetry.py` (lines 72–74)
  - `PYTEST_RUNNING` gate pattern: `if os.getenv("PYTEST_RUNNING") or os.getenv("PYTEST_CURRENT_TEST"): return`
  - Established project convention for test-only behaviour

### Code Search Results

- `PYTEST_RUNNING`
  - Set in `tests/conftest.py` line 91; passed to all service containers in `compose.e2e.yaml` and `compose.int.yaml`; consumed in `shared/telemetry.py` — confirmed as the right gate variable

- `metrics.get_meter`
  - Only in `services/retry/retry_daemon.py` — the sole existing OTel metrics usage; confirms the pattern is established but not yet in the bot

- `self._sweep_task` / `_sweep_in_progress`
  - Not present anywhere — confirms the concurrency guard is entirely missing

- `on_ready` / `on_resumed` sweep call
  - Both call `await self._sweep_deleted_embeds()` directly, not via `asyncio.create_task`
  - To enable cancel-and-restart, `_sweep_deleted_embeds` must be wrapped in a task and the handle stored on `self`

### Project Conventions

- Standards referenced: `retry_daemon.py` for OTel metrics; `shared/telemetry.py` for `PYTEST_RUNNING` gate; `test_participant_drop_event.py` for direct-call integration test pattern
- Instructions followed: TDD applies (Python); no new packages; minimal production code surface for test-only features

## Key Discoveries

### Concurrency Bug

When the Discord Gateway temporarily disconnects and reconnects (common on flaky connections), `on_resumed` fires — sometimes multiple times in quick succession. Each invocation calls `_sweep_deleted_embeds` inline, spawning a fresh worker pool. Two concurrent sweeps:

1. Both query the DB independently — same game list
2. Both spawn up to 60 workers — up to 120 workers hitting Discord simultaneously
3. Both publish `EMBED_DELETED` for the same games — duplicate events (harmless due to idempotency, but wasteful)

**Correct fix — cancel-and-restart, not drop:**

- Dropping the new sweep is wrong: if Sweep 1 already passed channel A and a message in channel A was deleted, Sweep 2 would catch it but gets dropped — the deletion is missed.
- Cancel-and-restart is correct: Sweep 2 re-queries the DB from scratch, covering everything Sweep 1 hadn't reached **plus** any new deletions. Duplicates already published by Sweep 1 are harmless.

**`CancelledError` propagation is safe:**
`CancelledError` is `BaseException`, not `Exception`. The `except Exception` in `_run_sweep_worker` does not swallow it. Cancellation propagates to the next `await` point in each worker coroutine cleanly.

**Task handle pattern:**
`_sweep_deleted_embeds` must be launched via `asyncio.create_task` so the handle is stored on `self._sweep_task`. On each new trigger: cancel the old task (if running), await it swallowing `CancelledError`, then create a new task.

```python
async def _trigger_sweep(self) -> None:
    if self._sweep_task and not self._sweep_task.done():
        logger.warning("Embed deletion sweep interrupted: new sweep triggered")
        sweep_interrupted_counter.add(1)
        self._sweep_task.cancel()
        try:
            await self._sweep_task
        except asyncio.CancelledError:
            pass
    self._sweep_task = asyncio.create_task(self._sweep_deleted_embeds())
```

`on_ready` and `on_resumed` call `await self._trigger_sweep()` instead of `await self._sweep_deleted_embeds()` directly.

### OTel Metrics Pattern (from `retry_daemon.py`)

```python
meter = metrics.get_meter(__name__)

sweep_started_counter = meter.create_counter(
    name="bot.sweep.started",
    description="Number of embed deletion sweeps started",
    unit="1",
)
sweep_interrupted_counter = meter.create_counter(
    name="bot.sweep.interrupted",
    description="Number of sweeps cancelled because a new sweep was triggered",
    unit="1",
)
sweep_messages_checked_counter = meter.create_counter(
    name="bot.sweep.messages_checked",
    description="Total Discord messages fetched during sweeps",
    unit="1",
)
sweep_deletions_detected_counter = meter.create_counter(
    name="bot.sweep.deletions_detected",
    description="Total EMBED_DELETED events published by sweeps",
    unit="1",
)
sweep_duration_histogram = meter.create_histogram(
    name="bot.sweep.duration",
    description="Duration of completed embed deletion sweeps in seconds",
    unit="s",
)
```

`sweep_messages_checked_counter` and `sweep_deletions_detected_counter` are incremented inside `_run_sweep_worker`. `sweep_started_counter` and `sweep_duration_histogram` are recorded in `_sweep_deleted_embeds`. `sweep_interrupted_counter` is recorded in `_trigger_sweep`.

### Test-Only HTTP Server

```python
# In on_ready, after existing setup:
if os.getenv("PYTEST_RUNNING"):
    asyncio.create_task(self._start_test_server())

async def _start_test_server(self) -> None:
    app = aiohttp.web.Application()
    app.router.add_post("/admin/sweep", self._handle_sweep_request)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", 8089)
    await site.start()
    logger.info("Test server started on port 8089")

async def _handle_sweep_request(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
    await self._trigger_sweep()
    if self._sweep_task:
        await self._sweep_task
    return aiohttp.web.Response(status=200)
```

Port `8089` chosen to avoid conflicts with API (8000) and any other services. Bot container name in e2e environment is `${CONTAINER_PREFIX:-gamebot-e2e}-bot`; hostname on `app-network` is `bot`.

### Integration Test Pattern (from `test_participant_drop_event.py`)

For `_handle_embed_deleted`: create real game, call handler directly, assert row removed and `GAME_CANCELLED` published.

For `_sweep_deleted_embeds`: create real game, SQL UPDATE `message_id` to fake snowflake, create `MagicMock(spec=GameSchedulerBot)` with mocked `get_channel`/`fetch_channel` returning a channel mock whose `fetch_message` raises `discord.NotFound`, call `await GameSchedulerBot._sweep_deleted_embeds(mock_bot)`. Assert `EMBED_DELETED` published via a bound RabbitMQ queue.

### E2E Test: Case 1 (Real-Time Deletion)

Model: `tests/e2e/test_game_cancellation.py`.

```
POST /api/v1/games → wait for message_id populated
discord_helper.delete_message(channel_id, message_id)
poll DB → assert game row absent
```

Requires `delete_message(channel_id, message_id)` in `DiscordTestHelper`:

```python
async def delete_message(self, channel_id: str, message_id: str) -> None:
    channel = await self.client.fetch_channel(int(channel_id))
    message = await channel.fetch_message(int(message_id))
    await message.delete()
```

### E2E Test: Case 2 (Sweep via HTTP Trigger)

```
POST /api/v1/games → wait for message_id populated
SQL UPDATE game_sessions SET message_id = '9999999999999999999' WHERE id = :game_id
POST http://bot:8089/admin/sweep  (blocks until sweep completes)
poll DB → assert game row absent
```

No compose changes needed. `app-network` already shared. `PYTEST_RUNNING=1` already set on bot container.

## Recommended Approach

1. Add `_trigger_sweep` method with cancel-and-restart logic; replace direct `_sweep_deleted_embeds` calls in `on_ready` and `on_resumed`
2. Add OTel meter and five metrics to `bot.py` following `retry_daemon.py` pattern
3. Add test server gated on `PYTEST_RUNNING` with `POST /admin/sweep`
4. Write unit tests for `_trigger_sweep` cancel-and-restart behaviour and metric increments
5. Write integration test for `EmbedDeletionConsumer._handle_embed_deleted`
6. Write integration test for `_sweep_deleted_embeds` (direct call, mocked Discord)
7. Add `delete_message` to `DiscordTestHelper`
8. Write e2e test for Case 1 (real Discord message deletion)
9. Write e2e test for Case 2 (`/admin/sweep` HTTP trigger)

## Implementation Guidance

- **Objectives**:
  - Fix concurrency bug: concurrent sweeps cause duplicate Discord requests and duplicate event publishing
  - Add operational visibility via OTel metrics
  - Provide integration and e2e test coverage for sweep and consumer paths

- **Key Tasks** (recommended order):
  1. Add `_trigger_sweep` with cancel-and-restart; update `on_ready` and `on_resumed`
  2. Add `meter` and five metric instruments to `bot.py`; instrument `_sweep_deleted_embeds` and `_run_sweep_worker`
  3. Add `PYTEST_RUNNING`-gated `aiohttp` test server with `POST /admin/sweep`
  4. Unit tests for `_trigger_sweep` (cancel behaviour, interrupt counter, no-op when no active task)
  5. Unit tests for metric increments (sweep start, interruption, message checked, deletion detected)
  6. Integration test: `EmbedDeletionConsumer._handle_embed_deleted` — real DB + RabbitMQ
  7. Integration test: `_sweep_deleted_embeds` — mocked Discord, real DB + Redis + RabbitMQ
  8. Add `delete_message` to `DiscordTestHelper`
  9. E2E test: Case 1 (real-time embed deletion → game cancellation)
  10. E2E test: Case 2 (fake `message_id` → POST `/admin/sweep` → game cancellation)

- **Dependencies**:
  - Task 1 must precede Tasks 4, 9, 10 (trigger mechanism required)
  - Task 2 must precede Task 5 (metrics must exist before testing them)
  - Task 3 must precede Task 10 (test server required for Case 2)
  - Task 8 must precede Task 9 (`delete_message` required for Case 1)
  - Tasks 6 and 7 are independent of all other tasks

- **Success Criteria**:
  - Back-to-back `on_resumed` events result in exactly one active sweep, with the first cancelled and logged
  - OTel metrics exported: sweep counts, message checked counts, deletion detected counts, sweep duration
  - Integration test calls `_handle_embed_deleted` directly; asserts game row removed and `GAME_CANCELLED` published to RabbitMQ
  - Integration test calls `_sweep_deleted_embeds` directly with mocked Discord; asserts `EMBED_DELETED` published
  - E2E test deletes Discord message; asserts game row removed from DB
  - E2E test sets fake `message_id`, triggers sweep via `POST /admin/sweep`; asserts game row removed from DB
  - No changes to `bot.Dockerfile` healthcheck or `compose.e2e.yaml`

---

## Addendum: Remove Sweep from `on_resumed`

### Finding

The sweep (`_sweep_deleted_embeds`) is called in both `on_ready` and `on_resumed`. The `on_resumed` call is
redundant and expensive.

### Discord Gateway Resume Semantics (verified against official docs)

When a session is successfully resumed, Discord **replays all missed events in sequence order**, finishing
with the `RESUMED` event to signal replay is complete. discord.py fires `on_resumed` only after this replay
is finished. The replay includes `MESSAGE_DELETE` events, which trigger `on_raw_message_delete` — the same
handler that publishes `EMBED_DELETED` for real-time deletions.

`MESSAGE_DELETE` is gated on the `GUILD_MESSAGES (1 << 9)` intent, which the bot already declares
(`guild_messages=True`). So all message deletions that occurred during the disconnection window are
delivered via replay before `on_resumed` fires.

`on_ready` fires only on a **full reconnect** (session expired or could not be resumed). In this case
Discord sends no replay; all missed events are lost. The sweep is the only mechanism to recover them.

### Conclusion

| Event        | Gateway behaviour                           | Sweep needed? |
| ------------ | ------------------------------------------- | ------------- |
| `on_ready`   | Full reconnect — no event replay            | **Yes**       |
| `on_resumed` | Session resume — all missed events replayed | **No**        |

The sweep call in `on_resumed` should be removed. `_recover_pending_workers` is unaffected — it recovers
DB-queued `message_refresh_queue` work and belongs in both handlers regardless of Gateway replay.

### Required Change

In `services/bot/bot.py`, `on_resumed`:

```python
# Remove this line:
await self._sweep_deleted_embeds()
```

The `on_ready` call site is unchanged. The existing `on_resumed` unit test should be updated to assert
that `_sweep_deleted_embeds` is **not** called.
