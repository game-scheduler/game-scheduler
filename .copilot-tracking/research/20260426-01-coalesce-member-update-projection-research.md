<!-- markdownlint-disable-file -->

# Task Research Notes: coalesce-member-update-projection

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - `on_member_update`, `on_member_add`, `on_member_remove` (lines 405–422): each calls
    `guild_projection.repopulate_all()` directly, synchronously, in the event handler body
  - `_rebuild_redis_from_gateway` → `on_ready` also calls `repopulate_all(reason="on_ready")`
    directly and is intentionally outside any coalescing path
  - `_projection_heartbeat` (line 802): background `asyncio.Task` created in `setup_hook`
    via `asyncio.create_task`, guarded by `not hasattr(self, "_projection_heartbeat_task")`,
    loops with `await asyncio.sleep(30)` and catches `CancelledError` cleanly — the
    canonical pattern for new background tasks in this codebase
  - `_trigger_sweep` (referenced in code): cancel-and-restart pattern using
    `asyncio.Task.cancel()` — not a model for the coalescer (see below)

- `services/bot/guild_projection.py`
  - `repopulate_all()` (line ~195): full rebuild — new generation timestamp, pipeline all
    members across all guilds, flip `proj:gen` pointer, SCAN-delete old gen keys
  - `repopulation_started_counter` (line 207): `add(1, {"reason": reason})` — fires once
    per `repopulate_all` call, at the start of the function
  - `repopulation_duration_histogram` (line 224) and `repopulation_members_written_histogram`
    (line 225): record after work completes, also tagged with `{"reason": reason}`
  - `write_member()` (exists but unused by event handlers): targeted single-member write
    to the current generation — safe for `member_update` (roles, nick, username variants),
    but does not update `proj:usernames` ZADD/ZREM for old name variants

### Code Search Results

- `on_member_update|on_member_add|on_member_remove`
  - All three handlers follow the identical pattern: `redis = await get_redis_client()` then
    `await guild_projection.repopulate_all(bot=self, redis=redis, reason="<event_name>")`
  - No rate limiting, debouncing, or coalescing present

- `_projection_heartbeat_task|_sweep_task`
  - `_projection_heartbeat_task`: created in `setup_hook`, never cancelled
  - `_sweep_task`: cancel-and-restart per sweep trigger via `task.cancel()` + `create_task`

### Project Conventions

- Standards referenced: `python.instructions.md`, `test-driven-development.instructions.md`,
  `unit-tests.instructions.md`
- Background tasks use `asyncio.create_task()` in `setup_hook`, guarded by `hasattr` check,
  with `CancelledError` caught and logged cleanly in the loop body
- TDD methodology applies (Python)

## Key Discoveries

### Performance Baseline

Observed over a 40-minute sample window:

- 5 total `repopulate_all` calls from member events
- Burst of 3 calls within 8 seconds immediately after `on_ready` (Discord fires batched
  `member_update` events on reconnect/resume)
- ~0.75s per repopulation (full pipeline write + SCAN delete)
- Current frequency is low enough that the problem is latent, not actively harmful

### Why Cancel-and-Restart Does Not Help

`_trigger_sweep` uses cancel-and-restart because the sweep is a long-running iteration that
can be safely abandoned mid-flight. `repopulate_all` is not: all Redis pipeline work is
already committed before cancellation could fire at an `await` point. Cancelling a running
`repopulate_all` partway through leaves the projection in a partially-written new generation
with the gen pointer not yet flipped — worse than letting it complete.

### Why `asyncio.Queue` Works but `asyncio.Event` Is Better

A `Queue` requires a drain loop to coalesce N pending items into a single rebuild call.
An `asyncio.Event` is inherently a binary signal — any number of `set()` calls during the
cooldown window collapse to one pending notification. No drain loop, no unbounded growth,
no stale items.

### Metrics Architecture With Coalescing

**Problem with keeping current metrics unchanged:** if the coalescer fires once per 60s
window but coalesces 3 events, recording `started(reason="member_update")` inside
`repopulate_all` would undercount triggers (the other 2 events would be invisible) while
reporting misleading per-reason timing.

**Selected design — counter tracks why, histograms track cost:**

| Metric                                                  | Where emitted                                                                               | `reason` label                                                                       |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `bot.projection.repopulation.started` counter           | In each event handler (on `event.set()`), and in `on_ready` before calling `repopulate_all` | original gateway reason (`on_ready`, `member_update`, `member_add`, `member_remove`) |
| `bot.projection.repopulation.duration` histogram        | Inside `repopulate_all` after work completes                                                | **no label**                                                                         |
| `bot.projection.repopulation.members_written` histogram | Inside `repopulate_all` after work completes                                                | **no label**                                                                         |

**Why histograms carry no `reason` label:** rebuild duration and member count are determined
entirely by guild size, not by what triggered the rebuild. An `on_ready` rebuild and a
coalesced member-event rebuild run identical code against the same member cache — the trigger
type tells you nothing about the cost. A `reason` label on the histograms would add series
to the timing panels without adding analytical value. The counter already answers "why and
how often"; the histograms answer "how expensive" — these are orthogonal questions and the
label should not cross over.

**Consequence for `repopulate_all` signature:** `reason` is no longer needed as a parameter.
The counter moves entirely to callers. `repopulate_all` becomes a pure rebuild function with
no metric side effects beyond the histograms.

**Dashboard impact:** "Repopulation Rate by Reason" (counter panel) continues to show
per-event-type trigger rates. "Repopulation Duration" and "Members Written" panels show a
single series — simpler and accurate.

## Recommended Approach

`asyncio.Event`-based coalescing worker with a 60-second minimum-interval cooldown.
Counter moves to callers; histograms remain in `repopulate_all` with no `reason` label.

**Worker lifecycle:**

- `asyncio.Event` instance stored on the bot (`self._member_event`)
- Worker task created in `setup_hook`, same guard pattern as `_projection_heartbeat_task`
- Worker loops: `await event.wait()` → `event.clear()` → `repopulate_all()` → `await asyncio.sleep(60)`

**Event handler change (all three handlers):**

```python
async def on_member_update(self, _before: discord.Member, _after: discord.Member) -> None:
    repopulation_started_counter.add(1, {"reason": "member_update"})
    self._member_event.set()
```

(Same pattern for `on_member_add` with `reason="member_add"` and `on_member_remove` with
`reason="member_remove"`.)

**`on_ready` path:**

```python
repopulation_started_counter.add(1, {"reason": "on_ready"})
await guild_projection.repopulate_all(bot=self, redis=redis)
```

**`repopulate_all` signature change:** `reason` parameter removed. The counter is no longer
emitted inside `repopulate_all`; the `duration` and `members_written` histograms remain
inside it, without any label.

**Cooldown semantics:** the 60s `asyncio.sleep` after each rebuild means at most one rebuild
per minute from member events. Events that fire during the sleep are coalesced into the next
wakeup — `event.set()` is safe to call any number of times.

## Implementation Guidance

- **Objectives**: eliminate repeated full rebuilds when multiple member events fire in
  quick succession (especially post-reconnect bursts); preserve accurate per-event-type
  trigger counts in existing dashboards
- **Key Tasks**:
  1. Add `self._member_event = asyncio.Event()` initialization in `__init__`
  2. Create `_member_event_worker` async method: wait → clear → repopulate → sleep 60s loop
  3. Start worker task in `setup_hook` with `hasattr` guard
  4. Replace `repopulate_all` call in each of the three member event handlers with
     `repopulation_started_counter.add(1, {"reason": "<event_name>"})` + `self._member_event.set()`
  5. Add `repopulation_started_counter.add(1, {"reason": "on_ready"})` before the direct
     `repopulate_all` call in `on_ready`
  6. Remove `reason` parameter from `repopulate_all`; remove the counter call from inside it;
     remove `{"reason": reason}` attributes from the two histogram `.record()` calls
  7. Write unit tests for the worker: verify event.set() coalesces, verify cooldown,
     verify on_ready is unaffected
- **Dependencies**: no new libraries; `asyncio.Event` is stdlib
- **Success Criteria**:
  - A burst of 10 `on_member_update` events produces exactly 1 `repopulate_all` call
    (after the 60s window) and 10 `started{reason="member_update"}` counter increments
  - `on_ready` still produces 1 immediate `repopulate_all` call with `reason="on_ready"`
  - Dashboard "Repopulation Rate by Reason" continues to show per-event-type trigger rates
  - Dashboard timing and member-count panels show a single unambiguous series
