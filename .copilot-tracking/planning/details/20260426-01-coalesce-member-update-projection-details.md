<!-- markdownlint-disable-file -->

# Task Details: coalesce-member-update-projection

## Research Reference

**Source Research**: #file:../research/20260426-01-coalesce-member-update-projection-research.md

## Phase 1: TDD RED — write xfail tests for new worker and updated signatures

### Task 1.1: Create test file for `_member_event_worker`

Create `tests/unit/bot/test_bot_member_event_worker.py` with three xfail test classes:

- `TestMemberEventWorkerCoalescing`: assert that firing the event N times before the
  worker wakes results in exactly one `repopulate_all` call
- `TestMemberEventWorkerCooldown`: assert the worker does not call `repopulate_all` again
  within the 60s sleep window after a rebuild
- `TestOnReadyUnaffected`: assert `on_ready` still invokes `repopulate_all` immediately
  (synchronously, before the worker) and emits `started{reason="on_ready"}`

Mark all three test classes `@pytest.mark.xfail(strict=True)` at the class level.
Use `unittest.mock.patch` to mock `asyncio.sleep`, `guild_projection.repopulate_all`,
and `get_redis_client` so the test remains a pure unit test.

- **Files**:
  - `tests/unit/bot/test_bot_member_event_worker.py` — new file
- **Success**:
  - All three test classes present and marked `xfail`
  - `pytest tests/unit/bot/test_bot_member_event_worker.py` shows `xfailed` for all tests
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 112–163) — recommended approach and worker lifecycle
- **Dependencies**:
  - None (first phase)

### Task 1.2: Add xfail tests in `test_guild_projection.py` for updated `repopulate_all` signature

Add two xfail tests to `tests/unit/bot/test_guild_projection.py` inside
`TestRepopulateAll`:

- `test_repopulate_all_has_no_reason_parameter`: call `repopulate_all(bot=bot, redis=redis)`
  without `reason=`; assert it succeeds (currently fails because `reason` is required)
- `test_repopulate_all_does_not_emit_started_counter`: confirm the started counter is NOT
  called inside `repopulate_all` after the refactor (mock `repopulation_started_counter.add`
  and assert it is never called from within `repopulate_all`)

Mark both with `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - `tests/unit/bot/test_guild_projection.py` — append to `TestRepopulateAll`
- **Success**:
  - Two new xfail tests present; `pytest` reports them as `xfailed`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 70–102) — metrics architecture rationale
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Update `repopulate_all` signature and all callers

### Task 2.1: Remove `reason` from `repopulate_all` in `guild_projection.py`

In `services/bot/guild_projection.py`:

- Remove the `reason: str` parameter from `repopulate_all` (line 193)
- Remove the docstring line `reason: Reason for repopulation...` (line 204)
- Remove `repopulation_started_counter.add(1, {"reason": reason})` (line 207)
- Change `repopulation_duration_histogram.record(write_duration, {"reason": reason})`
  to `repopulation_duration_histogram.record(write_duration)` (line 224)
- Change `repopulation_members_written_histogram.record(total_members_written, {"reason": reason})`
  to `repopulation_members_written_histogram.record(total_members_written)` (line 225)
- Remove `reason` from the `logger.info` call (lines 228–231)

- **Files**:
  - `services/bot/guild_projection.py` — modify `repopulate_all` function (lines 189–231)
- **Success**:
  - `repopulate_all` accepts only `bot` and `redis` keyword arguments
  - No reference to `reason` remains in `repopulate_all`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 104–111) — consequence for `repopulate_all` signature
- **Dependencies**:
  - Phase 1 xfail tests exist to confirm the RED state

### Task 2.2: Update all callers of `repopulate_all` in `bot.py`

In `services/bot/bot.py`:

- `on_ready` (line 217): add `guild_projection.repopulation_started_counter.add(1, {"reason": "on_ready"})` immediately before the `repopulate_all` call; drop `reason="on_ready"` from the call (line 220)
- `on_member_add` (line 399): drop `reason="member_add"` from `repopulate_all` call
- `on_member_update` (line 408): drop `reason="member_update"` from `repopulate_all` call
- `on_member_remove` (line 417): drop `reason="member_remove"` from `repopulate_all` call

Note: the three member-event handlers still call `repopulate_all` directly here; they will
be replaced entirely in Phase 3.

- **Files**:
  - `services/bot/bot.py` — modify `on_ready`, `on_member_add`, `on_member_update`, `on_member_remove`
- **Success**:
  - No caller passes `reason=` to `repopulate_all`
  - `on_ready` emits the started counter before calling `repopulate_all`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 112–138) — recommended approach code snippets
- **Dependencies**:
  - Task 2.1 (signature removed before callers updated)

### Task 2.3: Update `test_guild_projection.py` to drop `reason=` and remove xfail

In `tests/unit/bot/test_guild_projection.py`:

- Remove `reason=` keyword argument from all eight `repopulate_all` call sites (lines 313, 345, 365, 389, 404, 419, 665, 688)
- Update `test_repopulate_all_otel_metrics` (line 394): assert that `repopulation_started_counter.add` is NOT called inside `repopulate_all` (mock the counter and check `call_count == 0`)
- Remove `@pytest.mark.xfail` markers from `test_repopulate_all_has_no_reason_parameter` and `test_repopulate_all_does_not_emit_started_counter` added in Phase 1

- **Files**:
  - `tests/unit/bot/test_guild_projection.py` — multiple edits
- **Success**:
  - All `repopulate_all` calls use only `bot=` and `redis=` kwargs
  - xfail markers removed from Phase 1 tests; those tests now pass
  - Full unit test suite passes with no failures
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 70–102) — metrics design rationale
- **Dependencies**:
  - Tasks 2.1 and 2.2

## Phase 3: Add `_member_event_worker` and replace member event handlers

### Task 3.1: Initialize `self._member_event` in `GameSchedulerBot.__init__`

In `services/bot/bot.py`, inside `__init__` (after `self._sweep_task = None`, ~line 131):

```python
self._member_event: asyncio.Event = asyncio.Event()
```

- **Files**:
  - `services/bot/bot.py` — `__init__` method
- **Success**:
  - `GameSchedulerBot.__init__` sets `self._member_event` as an `asyncio.Event`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 115–117) — worker lifecycle
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Add `_member_event_worker` method to `GameSchedulerBot`

Add the async method to `services/bot/bot.py`, adjacent to `_projection_heartbeat`
(near line 802):

```python
async def _member_event_worker(self) -> None:
    while True:
        try:
            await self._member_event.wait()
            self._member_event.clear()
            redis = await get_redis_client()
            await guild_projection.repopulate_all(bot=self, redis=redis)
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Member event worker cancelled")
            return
```

- **Files**:
  - `services/bot/bot.py` — new method on `GameSchedulerBot`
- **Success**:
  - Method present; follows same `CancelledError` guard pattern as `_projection_heartbeat`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 115–125) — worker lifecycle pseudocode
- **Dependencies**:
  - Task 3.1

### Task 3.3: Start worker task in `setup_hook`

In `services/bot/bot.py`, `setup_hook` (after the `_projection_heartbeat_task` guard, ~line 164):

```python
if not hasattr(self, "_member_event_worker_task"):
    self._member_event_worker_task = asyncio.create_task(self._member_event_worker())
    logger.info("Started member event worker task")
```

- **Files**:
  - `services/bot/bot.py` — `setup_hook` method
- **Success**:
  - Worker task started with same `hasattr` guard pattern used for heartbeat
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 112–118) — worker lifecycle
- **Dependencies**:
  - Task 3.2

### Task 3.4: Replace member event handlers

In `services/bot/bot.py`, replace the bodies of `on_member_add`, `on_member_update`,
and `on_member_remove` to emit the counter and signal the event:

```python
async def on_member_add(self, _member: discord.Member) -> None:
    guild_projection.repopulation_started_counter.add(1, {"reason": "member_add"})
    self._member_event.set()

async def on_member_update(self, _before: discord.Member, _after: discord.Member) -> None:
    guild_projection.repopulation_started_counter.add(1, {"reason": "member_update"})
    self._member_event.set()

async def on_member_remove(self, _member: discord.Member) -> None:
    guild_projection.repopulation_started_counter.add(1, {"reason": "member_remove"})
    self._member_event.set()
```

- **Files**:
  - `services/bot/bot.py` — `on_member_add` (line 396), `on_member_update` (line 405), `on_member_remove` (line 414)
- **Success**:
  - None of the three handlers call `repopulate_all` or `get_redis_client`
  - Each emits the counter with the correct `reason` label
  - Each calls `self._member_event.set()`
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 126–135) — event handler code snippets
- **Dependencies**:
  - Tasks 3.1, 3.2, 3.3

### Task 3.5: Remove xfail markers from worker tests

In `tests/unit/bot/test_bot_member_event_worker.py`, remove `@pytest.mark.xfail(strict=True)`
from all three test classes. Run the test file and confirm all tests pass.

- **Files**:
  - `tests/unit/bot/test_bot_member_event_worker.py`
- **Success**:
  - All worker tests pass without xfail
  - Full unit test suite passes with no failures
- **Research References**:
  - #file:../research/20260426-01-coalesce-member-update-projection-research.md (Lines 163–175) — success criteria
- **Dependencies**:
  - Tasks 3.1–3.4

## Dependencies

- Python `asyncio` stdlib (no new third-party packages)
- `pytest-asyncio` (already in test suite)

## Success Criteria

- A burst of N `on_member_update` calls produces exactly N counter increments and exactly 1 `repopulate_all` call from the worker (after the 60s window)
- `on_ready` still invokes `repopulate_all` immediately with `reason="on_ready"` counter emitted before the call
- `repopulate_all` accepts only `bot` and `redis`; no `reason` parameter
- Duration and member-count histograms carry no labels
- Full unit test suite passes with no failures at every phase boundary
