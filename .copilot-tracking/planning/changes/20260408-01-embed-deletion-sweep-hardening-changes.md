<!-- markdownlint-disable-file -->

# Changes: Embed Deletion Sweep Hardening and Test Coverage

**Plan**: .copilot-tracking/planning/plans/20260408-01-embed-deletion-sweep-hardening.plan.md
**Details**: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md

---

## Phase 1: Concurrency Guard (TDD RED) — COMPLETE

### Added

- `tests/unit/bot/test_trigger_sweep.py` — Four xfail unit tests covering: no active task launches new task; active task is cancelled then new task launched; interrupted counter is incremented on cancellation; counter not incremented when no active task.

### Modified

- `services/bot/bot.py` — Added `self._sweep_task: asyncio.Task[None] | None = None` in `__init__`; added `_trigger_sweep` stub raising `NotImplementedError`.

---

## Phase 2: Concurrency Guard (TDD GREEN) — COMPLETE

### Modified

- `services/bot/bot.py` — Replaced `_trigger_sweep` stub with full cancel-and-restart implementation (uses `contextlib.suppress` per SIM105); updated `on_ready` and `on_resumed` to call `await self._trigger_sweep()` instead of `await self._sweep_deleted_embeds()` directly.
- `tests/unit/bot/test_trigger_sweep.py` — Removed `@pytest.mark.xfail(strict=True)` markers from all four tests; all tests pass green.

**Out-of-plan deviation**: Added `meter`, `sweep_started_counter`, `sweep_interrupted_counter`, `sweep_messages_checked_counter`, `sweep_deletions_detected_counter`, and `sweep_duration_histogram` module-level OTel instruments to `services/bot/bot.py` as part of Phase 2. Reason: `sweep_interrupted_counter.add(1)` in `_trigger_sweep` triggered an `F821 Undefined name` ruff error; all 5 instruments were grouped together because they share the same `meter`. Phase 3 Task 3.1 (add metric instruments) is therefore already satisfied and only the tests need to be written.

---

## Phase 3: OTel Metrics (TDD RED) — COMPLETE

### Added

- `tests/unit/bot/test_sweep_metrics.py` — Five xfail unit tests covering all metric increments: `sweep_started_counter` on entry, `sweep_interrupted_counter` on cancellation, `sweep_messages_checked_counter` on successful fetch, `sweep_deletions_detected_counter` on 404, and `sweep_duration_histogram` on completion.

---

## Phase 4: OTel Metrics (TDD GREEN) — COMPLETE

### Modified

- `services/bot/bot.py` — Added `sweep_started_counter.add(1)` and `start_time` in `_sweep_deleted_embeds`; `sweep_duration_histogram.record(time.time() - start_time)` at end of sweep; `sweep_messages_checked_counter.add(1)` and `sweep_deletions_detected_counter.add(1)` in `_run_sweep_worker`.
- `tests/unit/bot/test_sweep_metrics.py` — Removed all `@pytest.mark.xfail(strict=True)` markers; all five metric tests pass green.

---

## Phase 5: Test Server (TDD RED) — COMPLETE

### Added

- `tests/unit/bot/test_test_server.py` — One xfail unit test verifying `_handle_sweep_request` calls `_trigger_sweep` and returns HTTP 200.

### Modified

- `services/bot/bot.py` — Added `_start_test_server` and `_handle_sweep_request` stubs both raising `NotImplementedError`.

---

## Phase 6: Test Server (TDD GREEN) — COMPLETE

### Modified

- `services/bot/bot.py` — Added `import os` and `import aiohttp.web`; implemented `_start_test_server` (aiohttp `AppRunner`/`TCPSite` on `0.0.0.0:8089`); implemented `_handle_sweep_request` (awaits `_trigger_sweep()`, awaits `self._sweep_task`, returns `Response(status=200)`); added `PYTEST_RUNNING`-gated `asyncio.create_task(self._start_test_server())` at end of `on_ready`.
- `tests/unit/bot/test_test_server.py` — Removed `@pytest.mark.xfail` marker; replaced `AsyncMock` sweep task with a real `asyncio.Task` (via `asyncio.create_task(_noop())`); test passes green.

---

## Phase 7: Integration Tests (Retrofitting) — COMPLETE

### Bug Fix

- `services/bot/bot.py` — Fixed `_sweep_deleted_embeds`: `game.channel_id` (UUID FK) was passed to `int()` which would crash; replaced with `game.channel.channel_id` (Discord snowflake via relationship); added `joinedload(GameSession.channel)` to the sweep query so the relationship is loaded within the session.
- `tests/unit/bot/test_sweep_metrics.py` — Updated `_db_ctx_one_game` mock: replaced `mock_game.channel_id = 111222333` with `mock_game.channel.channel_id = "111222333"` to match the fixed access pattern.

### Added

- `tests/integration/test_embed_deletion_consumer.py` — Two integration tests for `EmbedDeletionConsumer._handle_embed_deleted`: (1) creates a real game, calls the handler, asserts game row removed and `GAME_CANCELLED` published to RabbitMQ; (2) asserts no publication when game is already missing (idempotency).

### Deviation from Plan

- Task 7.2 (`_sweep_deleted_embeds` integration test with mocked Discord) was **not implemented** as an integration test. The integration environment has no Discord connection; mocking Discord.py Bot methods within that environment would duplicate existing unit test coverage rather than test real infrastructure. Sweep behaviour against real Discord will be covered by e2e Phase 8 Case 2 (`POST /admin/sweep` → bot runs real sweep against real Discord).
