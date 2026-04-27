---
description: 'Unit test quality standards — prevent coverage theater, require behavioral assertions'
applyTo: '**/test_*.py'
---

# Unit Test Quality Standards

## Core Principle: Tests Must Be Falsifiable

A unit test is only valuable if a wrong implementation would cause it to fail. A test that passes regardless of what the code does provides false confidence and is worse than no test — it teaches the coverage tool that a branch is "covered" while hiding real bugs.

**Before writing a test, ask:** if I swap two arguments, delete a return value, or invert a condition, will this test catch it? If the answer is no, the test needs more assertions.

## The Scanner Is a Floor, Not a Target

The pre-commit checker flags common patterns of weak assertions. Satisfying the checker is the minimum bar — not the goal. The goal is tests that catch real bugs.

**Do not write assertions whose only purpose is to silence the checker.** If the only way to satisfy a violation is to add an assertion that doesn't verify anything meaningful, the right response is to write a better test, not to add a hollow assertion.

Examples of gaming the scanner that are explicitly prohibited:

- Adding `assert True` to a test that has observable behavior that should be verified
- Replacing `assert_called_once()` with `assert mock.call_count == 1` to avoid the weak-assert check
- Using `assert_called_once_with(ANY, ANY)` when the actual arguments are available and verifiable
- Adding `# assert-not-weak: <reason>` to avoid writing real argument assertions

When you encounter a scanner violation, ask: **what is the code under test actually doing that I should be verifying?** Answer that question, then write the assertion. The scanner violation will resolve as a side effect.

## Required: Every Test Function Must Have at Least One Assertion

Every `test_*` function must contain at least one of:

- An `assert` statement
- A mock call-verification call (`assert_called_once_with`, `assert_called_with`, `assert_any_call`, `assert_not_called`, `assert_awaited_once_with`, etc.)
- A `pytest.raises(...)` context manager

A test body that only calls the function under test and makes no assertions does not verify behavior — it only verifies that no exception is raised.

```python
# BAD: no assertion — only proves no exception was raised
async def test_handle_game_created_not_found(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    await handlers.handle_game_created({"game_id": "123"})

# GOOD: asserts the downstream call was suppressed
async def test_handle_game_created_not_found(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    await handlers.handle_game_created({"game_id": "123"})
    mock_deps.publisher.publish_game_created.assert_not_called()
```

If the intent genuinely is "no exception raised," make that explicit:

```python
# ACCEPTABLE: explicit intent, not an oversight
async def test_handle_game_created_not_found_does_not_raise(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    # No downstream action expected when game is not found
    await handlers.handle_game_created({"game_id": "123"})
    assert True  # documents the intent: no exception is the assertion
```

## Mock Call Verification: Use `assert_called_once_with`, Not `assert_called_once`

`assert_called_once()` confirms the mock was invoked but ignores what arguments were passed. `assert_called_once_with(...)` verifies both invocation and arguments. Almost always prefer the latter.

```python
# BAD: confirms a call happened but not what was passed
mock_session.add.assert_called_once()

# GOOD: verifies the correct object was passed
mock_session.add.assert_called_once_with(expected_participant)
```

Use `unittest.mock.ANY` when exact argument values are not the point of the test, such as for log message strings:

```python
from unittest.mock import ANY

# GOOD: verifies error was logged with the exception, not the exact message wording
mock_logger.error.assert_called_once_with(ANY, caught_exception)
```

## Do Not Verify Only That Code Ran

Tests that set up mocks and call the function under test without verifying the outcome are coverage theater. The mock return values used during setup are also assertions about expected behavior — if a mock returns a specific value, the test should verify that value was used correctly.

```python
# BAD: sets up 5 mocks, calls the function, asserts nothing
async def test_process_event(handler, mock_db, mock_publisher, mock_cache, mock_logger):
    mock_db.execute.return_value = mock_result
    mock_result.scalar_one_or_none.return_value = mock_game
    await handler.process_event(event)
    # no assertions

# GOOD: verifies what actually happened with the returned game
async def test_process_event(handler, mock_db, mock_publisher, mock_cache, mock_logger):
    mock_db.execute.return_value = mock_result
    mock_result.scalar_one_or_none.return_value = mock_game
    await handler.process_event(event)
    mock_publisher.publish_game_updated.assert_called_once_with(mock_game.id)
```

## Prefer Behavioral Assertions Over Call-Count Assertions

Asserting on return values, state changes, or specific argument values is stronger than asserting only that a method was called. Call-count assertions (e.g., `assert_called_once`) are appropriate for side-effect-only functions where no return value exists.

```python
# WEAK: only verifies flush was called once
mock_session.flush.assert_called_once()

# STRONGER: verifies the object was added before flush
mock_session.add.assert_called_once_with(new_record)
mock_session.flush.assert_called_once()
```

## Negative Assertions Require a Trigger

`assert_not_called()` is only meaningful when the test exercises a code path that would call the mock if the condition being tested were different. A test that calls `assert_not_called()` on a mock that has no reason to be called in any scenario is not testing anything.

```python
# BAD: mock_redis.delete can never be called here — not testing anything
async def test_some_path(handler):
    await handler.run()
    mock_redis.delete.assert_not_called()

# GOOD: another code path does call mock_redis.delete; this test verifies it's
# suppressed when the condition is False
async def test_cache_not_invalidated_when_flag_is_false(handler, mock_redis):
    await handler.run(invalidate=False)
    mock_redis.delete.assert_not_called()
```

## One Behavior Per Test

Each test function should verify one specific behavior or scenario. Long test functions with many mocks and many assertions usually indicate multiple behaviors that should be split into separate tests with clear names.

```python
# BAD: testing two distinct behaviors in one function
async def test_participant_removal(handler, mock_db, mock_publisher):
    # scenario 1
    mock_participant.status = "WAITLISTED"
    await handler.remove_participant(event)
    mock_publisher.publish_promoted.assert_called_once()
    # scenario 2
    mock_participant.status = "CONFIRMED"
    await handler.remove_participant(event)
    mock_publisher.publish_removed.assert_called_once()

# GOOD: separate tests with clear names
async def test_waitlisted_participant_removal_triggers_promotion(handler, mock_db, mock_publisher):
    mock_participant.status = "WAITLISTED"
    await handler.remove_participant(event)
    mock_publisher.publish_promoted.assert_called_once_with(mock_participant.id)

async def test_confirmed_participant_removal_publishes_removed(handler, mock_db, mock_publisher):
    mock_participant.status = "CONFIRMED"
    await handler.remove_participant(event)
    mock_publisher.publish_removed.assert_called_once_with(mock_participant.id)
```

## Telemetry: Assert on Metric Calls When the Metric Is the Feature

Do not skip metric assertions just because "it's just telemetry." If a function's purpose includes emitting a counter or histogram, the test should verify the metric was incremented with the correct labels.

```python
# GOOD: metric increment is part of the observable contract
mock_counter.add.assert_called_once_with(1, {"reason": "on_ready", "status": "success"})
```

Use `unittest.mock.ANY` for description strings or unit strings if those details are not the focus.

## Coverage Theater Checklist

Before committing a test, verify it does not fall into these patterns:

- [ ] Function body has at least one `assert`, `assert_called*`, or `pytest.raises`
- [ ] Mock call verifications use `assert_called_once_with(...)` not just `assert_called_once()`
- [ ] If a mock returns a value, the test asserts something about how that value was used
- [ ] `assert_not_called()` is only used when a sibling test for the same mock _does_ call it
- [ ] The test name describes a specific behavior, not just "test it runs"
