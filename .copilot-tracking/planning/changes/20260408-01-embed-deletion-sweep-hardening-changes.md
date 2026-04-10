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
