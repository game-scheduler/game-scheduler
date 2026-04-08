<!-- markdownlint-disable-file -->

# Task Details: Embed Deletion Sweep Hardening and Test Coverage

## Research Reference

**Source Research**: #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md

---

## Phase 1: Concurrency Guard (TDD RED)

### Task 1.1: Add `_trigger_sweep` Stub

Add an empty `_trigger_sweep` method to `GameSchedulerBot` that raises `NotImplementedError`,
and add a `_sweep_task: asyncio.Task | None = None` instance attribute initialized in `__init__`.
This establishes the interface before tests are written.

- **Files**:
  - `services/bot/bot.py` — add `self._sweep_task = None` in `__init__`; add `_trigger_sweep` method stub raising `NotImplementedError`
- **Success**:
  - `_trigger_sweep` exists on the class and raises `NotImplementedError` when called
  - `self._sweep_task` is initialized to `None` in `__init__`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 65-97) — Concurrency Bug analysis and task handle pattern
- **Dependencies**:
  - None

### Task 1.2: Write xfail Unit Tests for Cancel-and-Restart Behavior

Write unit tests that verify the correct behavior of `_trigger_sweep` and mark them
`@pytest.mark.xfail(strict=True)`. Tests must cover: (a) no active task → launches new task,
(b) active incomplete task → cancels it then launches new task, (c) interrupt counter incremented
on cancellation, (d) no interrupt counter increment when no active task.

- **Files**:
  - `tests/unit/bot/test_trigger_sweep.py` — new test file
- **Success**:
  - All four xfail tests exist and fail with `NotImplementedError` (xfailed)
  - Running `pytest tests/unit/bot/test_trigger_sweep.py` shows all tests as `xfailed`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 65-97) — cancel-and-restart logic and `sweep_interrupted_counter`
- **Dependencies**:
  - Task 1.1 (stub must exist for tests to import)

---

## Phase 2: Concurrency Guard (TDD GREEN)

### Task 2.1: Implement `_trigger_sweep` with Cancel-and-Restart

Replace the `NotImplementedError` stub with the full cancel-and-restart implementation.
Cancel the current `_sweep_task` if running, `await` it swallowing `CancelledError`, then
create a new task for `_sweep_deleted_embeds`.

- **Files**:
  - `services/bot/bot.py` — implement `_trigger_sweep` per research code pattern
- **Success**:
  - `_trigger_sweep` cancels any in-progress sweep and awaits its `CancelledError`
  - A new `asyncio.Task` wrapping `_sweep_deleted_embeds` is assigned to `self._sweep_task`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 79-97) — task handle pattern code block
- **Dependencies**:
  - Task 1.2 (tests must exist to go GREEN against)

### Task 2.2: Update `on_ready` and `on_resumed` Callers

Replace the direct `await self._sweep_deleted_embeds()` calls in `on_ready` and `on_resumed`
with `await self._trigger_sweep()`.

- **Files**:
  - `services/bot/bot.py` — update two call sites
- **Success**:
  - Neither `on_ready` nor `on_resumed` call `_sweep_deleted_embeds` directly
  - Both call `await self._trigger_sweep()`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 51-56) — `on_ready`/`on_resumed` call site analysis
- **Dependencies**:
  - Task 2.1

### Task 2.3: Remove xfail Markers and Verify Tests Pass

Remove `@pytest.mark.xfail` from all tests in `test_trigger_sweep.py` and verify they pass.

- **Files**:
  - `tests/unit/bot/test_trigger_sweep.py` — remove xfail markers
- **Success**:
  - All four tests pass without xfail markers
  - `pytest tests/unit/bot/test_trigger_sweep.py` shows all green
- **Research References**:
  - None (verification step)
- **Dependencies**:
  - Tasks 2.1 and 2.2

---

## Phase 3: OTel Metrics (TDD RED)

### Task 3.1: Add Module-Level Meter and Five Metric Instruments

Add `meter = metrics.get_meter(__name__)` and the five counters/histogram as module-level
variables in `services/bot/bot.py`, following the `retry_daemon.py` pattern exactly.

- **Files**:
  - `services/bot/bot.py` — add imports (`from opentelemetry import metrics`) and five metric instruments at module level
- **Success**:
  - `meter`, `sweep_started_counter`, `sweep_interrupted_counter`, `sweep_messages_checked_counter`, `sweep_deletions_detected_counter`, and `sweep_duration_histogram` all defined at module level
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 98-131) — OTel metrics pattern with code block and placement guidance
- **Dependencies**:
  - Phase 2 complete (avoids conflicts during implementation)

### Task 3.2: Write xfail Unit Tests for Metric Increments

Write xfail tests for: `sweep_started_counter` incremented once per `_sweep_deleted_embeds`, `sweep_interrupted_counter` incremented when cancelling, `sweep_messages_checked_counter` incremented per checked message in `_run_sweep_worker`, `sweep_deletions_detected_counter` incremented per deletion detected.

- **Files**:
  - `tests/unit/bot/test_sweep_metrics.py` — new test file
- **Success**:
  - All metric tests exist and are xfailed
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 98-131) — which methods increment which metrics
- **Dependencies**:
  - Task 3.1 (metric instruments must exist to import in tests)

---

## Phase 4: OTel Metrics (TDD GREEN)

### Task 4.1: Add Metric Increment Calls

Add metric `.add()` calls in `_sweep_deleted_embeds` (start, duration), `_run_sweep_worker`
(messages checked, deletions detected), and `_trigger_sweep` (interrupted). Follow the exact
research specification for which method records which metric.

- **Files**:
  - `services/bot/bot.py` — instrument three methods with metric calls
- **Success**:
  - `sweep_started_counter.add(1)` called at start of `_sweep_deleted_embeds`
  - `sweep_duration_histogram.record(elapsed)` called at end of `_sweep_deleted_embeds`
  - `sweep_interrupted_counter.add(1)` called in `_trigger_sweep` before cancellation
  - `sweep_messages_checked_counter.add(1)` and `sweep_deletions_detected_counter.add(1)` called in `_run_sweep_worker`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 126-131) — placement summary for each metric
- **Dependencies**:
  - Task 3.2 (tests must exist to go GREEN against)

### Task 4.2: Remove xfail Markers and Verify Metric Tests Pass

Remove `@pytest.mark.xfail` from all tests in `test_sweep_metrics.py` and verify they pass.

- **Files**:
  - `tests/unit/bot/test_sweep_metrics.py` — remove xfail markers
- **Success**:
  - All metric tests pass
  - `pytest tests/unit/bot/test_sweep_metrics.py` shows all green
- **Research References**:
  - None (verification step)
- **Dependencies**:
  - Task 4.1

---

## Phase 5: Test Server (TDD RED)

### Task 5.1: Add Test Server Method Stubs

Add `_start_test_server` and `_handle_sweep_request` stub methods to `GameSchedulerBot`,
both raising `NotImplementedError`.

- **Files**:
  - `services/bot/bot.py` — add two method stubs
- **Success**:
  - Both methods exist on the class and raise `NotImplementedError`
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 132-156) — test server code pattern
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Write xfail Unit Test for Sweep Handler

Write an xfail test that calls `_handle_sweep_request` with a mock request and verifies
it calls `_trigger_sweep` and returns HTTP 200.

- **Files**:
  - `tests/unit/bot/test_test_server.py` — new test file
- **Success**:
  - Test exists and is xfailed (raises `NotImplementedError`)
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 144-156) — `_handle_sweep_request` logic
- **Dependencies**:
  - Task 5.1 (stubs must exist)

---

## Phase 6: Test Server (TDD GREEN)

### Task 6.1: Implement `_start_test_server` and `_handle_sweep_request`

Implement the `aiohttp`-based test server on port `8089` with a `POST /admin/sweep`
route. `_handle_sweep_request` calls `_trigger_sweep()` and awaits `self._sweep_task`,
then returns `Response(status=200)`.

- **Files**:
  - `services/bot/bot.py` — implement two methods
- **Success**:
  - `_start_test_server` starts `aiohttp.web.TCPSite` on `0.0.0.0:8089`
  - `_handle_sweep_request` awaits sweep completion and returns HTTP 200
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 132-156) — full implementation code
- **Dependencies**:
  - Task 5.2 (test must exist to go GREEN against)

### Task 6.2: Gate Test Server Launch on `PYTEST_RUNNING`

In `on_ready`, after existing setup, add:

```python
if os.getenv("PYTEST_RUNNING"):
    asyncio.create_task(self._start_test_server())
```

- **Files**:
  - `services/bot/bot.py` — one line addition in `on_ready`
- **Success**:
  - Test server only starts when `PYTEST_RUNNING` env var is set
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 39-41) — `PYTEST_RUNNING` gate pattern from `shared/telemetry.py`
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 132-140) — gate usage in test server context
- **Dependencies**:
  - Task 6.1

### Task 6.3: Remove xfail and Verify Test Server Tests Pass

Remove `@pytest.mark.xfail` from tests in `test_test_server.py` and verify they pass.

- **Files**:
  - `tests/unit/bot/test_test_server.py` — remove xfail markers
- **Success**:
  - All test server unit tests pass
- **Research References**:
  - None (verification step)
- **Dependencies**:
  - Tasks 6.1 and 6.2

---

## Phase 7: Integration Tests (Retrofitting)

### Task 7.1: Integration Test for `EmbedDeletionConsumer._handle_embed_deleted`

Using the `test_participant_drop_event.py` direct-call pattern: create a real game in the DB,
call `_handle_embed_deleted` directly with the game's `game_id`, assert the game row is
removed and `GAME_CANCELLED` is published to RabbitMQ.

- **Files**:
  - `tests/integration/test_embed_deletion_consumer.py` — new test file
- **Success**:
  - Test creates game, calls `_handle_embed_deleted`, asserts game absent from DB
  - `GAME_CANCELLED` event confirmed in bound RabbitMQ queue
  - Test passes immediately (no xfail — retrofitting existing correct behavior)
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 20-22) — consumer idempotency note
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 157-162) — direct-call integration test pattern
- **Dependencies**:
  - None (independent of other phases)

### Task 7.2: Integration Test for `_sweep_deleted_embeds`

Create a real game in the DB, SQL UPDATE its `message_id` to a fake snowflake,
create a `MagicMock(spec=GameSchedulerBot)` with mocked `get_channel`/`fetch_channel`
returning a channel mock whose `fetch_message` raises `discord.NotFound`, then call
`await GameSchedulerBot._sweep_deleted_embeds(mock_bot)`. Assert `EMBED_DELETED` published.

- **Files**:
  - `tests/integration/test_sweep_deleted_embeds.py` — new test file
- **Success**:
  - Test creates game with fake `message_id`, calls sweep directly, asserts `EMBED_DELETED` in RabbitMQ
  - Test passes immediately (retrofitting existing correct behavior)
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 157-162) — integration test pattern for sweep
- **Dependencies**:
  - None (independent of other phases)

---

## Phase 8: E2E Tests

### Task 8.1: Add `delete_message` to `DiscordTestHelper`

Add the following method to `tests/e2e/helpers/discord.py`:

```python
async def delete_message(self, channel_id: str, message_id: str) -> None:
    channel = await self.client.fetch_channel(int(channel_id))
    message = await channel.fetch_message(int(message_id))
    await message.delete()
```

- **Files**:
  - `tests/e2e/helpers/discord.py` — add `delete_message` method
- **Success**:
  - `delete_message(channel_id, message_id)` deletes the specified Discord message
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 163-180) — E2E Case 1 test and `delete_message` implementation
- **Dependencies**:
  - None

### Task 8.2: E2E Test Case 1 — Real-Time Embed Deletion

Model on `tests/e2e/test_game_cancellation.py`. POST `/api/v1/games`, wait for `message_id`
populated, call `discord_helper.delete_message(channel_id, message_id)`, poll DB and assert
game row is absent.

- **Files**:
  - `tests/e2e/test_embed_deletion.py` — new test file (or add `test_case1_real_time_deletion` to an appropriate existing file)
- **Success**:
  - E2E test passes: game created, Discord message deleted, DB confirms game removed
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 163-180) — E2E Case 1 full specification
- **Dependencies**:
  - Task 8.1 (`delete_message` must exist)
  - Phases 1–2 complete (game cancellation triggered by `on_message_delete` → `_handle_embed_deleted`)

### Task 8.3: E2E Test Case 2 — Sweep via HTTP Trigger

POST `/api/v1/games`, wait for `message_id` populated, SQL UPDATE game's `message_id` to
`'9999999999999999999'`, POST `http://bot:8089/admin/sweep` (blocks until sweep completes),
poll DB and assert game row is absent.

- **Files**:
  - `tests/e2e/test_embed_deletion.py` — add `test_case2_sweep_http_trigger`
- **Success**:
  - E2E test passes: game created, message_id faked, sweep triggered, DB confirms game removed
- **Research References**:
  - #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md (Lines 181-191) — E2E Case 2 full specification
- **Dependencies**:
  - Phases 5–6 complete (test server must be running)

---

## Dependencies

- `aiohttp~=3.11.0` — already a project dependency (`pyproject.toml` line 36); no new packages needed
- `opentelemetry-api` — already used in the project (OTel imports available in bot scope)

## Success Criteria

- Back-to-back `on_resumed` events produce exactly one active sweep; first cancelled and logged
- OTel metrics published: `bot.sweep.started`, `bot.sweep.interrupted`, `bot.sweep.messages_checked`, `bot.sweep.deletions_detected`, `bot.sweep.duration`
- Integration test confirms `_handle_embed_deleted` removes game from DB and publishes `GAME_CANCELLED`
- Integration test confirms `_sweep_deleted_embeds` publishes `EMBED_DELETED` with mocked Discord
- E2E Case 1 passes: real Discord message deletion triggers game cancellation
- E2E Case 2 passes: fake `message_id` + `POST /admin/sweep` triggers game cancellation
- No changes to `bot.Dockerfile`, healthcheck, or `compose.e2e.yaml`
