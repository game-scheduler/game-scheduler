# Fixing `check-test-assertions` Violations

The `check-test-assertions` pre-commit hook blocks test functions with weak or
missing assertions. This document explains each violation type and how to fix it.

**The goal is not to silence the checker. The goal is to write tests that
would catch a real bug.** Before reaching for an escape hatch, ask: if someone
changed the arguments passed to this mock, would this test fail? If not, the
test is not actually verifying the behavior it claims to cover.

For broader unit test quality guidance, see
[`.github/instructions/unit-tests.instructions.md`](../../.github/instructions/unit-tests.instructions.md).

## Violation Types

### `test_foo: no assertions`

The function contains no `assert` statement, no mock call-verification call, and
no `pytest.raises` context manager.

**Fix — verify the return value:**

```python
# before
def test_foo():
    result = compute(x)

# after
def test_foo():
    result = compute(x)
    assert result == expected_value
```

**Fix — verify a mock was called correctly:**

```python
# before
async def test_handle_event(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)

# after
async def test_handle_event(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)
    mock_deps.publisher.publish.assert_not_called()
```

**Fix — explicit "no exception" intent:**

Only use this when the test genuinely has no return value or mock call to verify:

```python
# after
async def test_handle_event_does_not_raise(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)
    assert True  # verifies no exception raised
```

### `test_foo: named mock 'mock_x' has no assert_* call`

The function captures a context manager with `as mock_x:` but never calls any
`assert_*` method on it. The author named the mock, implying an intent to verify
behavior that was never completed.

```python
# before — mock_x is named but never verified
def test_foo():
    with patch("module.fn") as mock_x:
        result = do_thing()
    assert result == 42

# after — verify the mock was called as expected
def test_foo():
    with patch("module.fn") as mock_x:
        result = do_thing()
    assert result == 42
    mock_x.assert_called_once_with(expected_arg)
```

If the mock is truly irrelevant to what is being tested, remove the `as mock_x`
alias so the intent is clear:

```python
# after — alias removed; mock only exists to suppress the real call
def test_foo():
    with patch("module.fn"):
        result = do_thing()
    assert result == 42
```

### `test_foo: \`assert_called_once()\` — prefer assert_called_once_with()`

### `test_foo: \`assert_called_once_with()\` — add arguments or add '# assert-no-args'`

Both violations mean the same thing: the mock's call count is verified but not
what arguments it received. A bug that passes the wrong argument will not be
caught.

**The standard fix is to add the expected arguments:**

```python
# before — call count only; wrong arguments would not be caught
mock_require.assert_called_once()

# after — verifies both the call and its arguments
mock_require.assert_called_once_with(mock_db, game.guild_id, "user123", not_found_detail="Game not found")
```

Use `unittest.mock.ANY` when one argument is an opaque internal object (e.g., a
redis client created inside the function under test) and the other arguments are
the ones that actually matter:

```python
from unittest.mock import ANY

# good: verifies user and guild are correct; redis client is internal
mock_check.assert_called_once_with("user123", guild_config.guild_id, ANY)
```

**The escape hatch — `# assert-no-args`:**

This marker suppresses the violation. It exists for the narrow case where the
function under test genuinely takes no arguments and no `ANY`-based assertion
would add signal. It is **not** a way to close a violation quickly.

Before using it, answer both questions:

1. Does the function under test actually take no arguments?
2. Is the call count itself meaningful to this test, or is this mock incidental?

If the answer to (2) is "incidental," the right fix is to remove the `as` alias
entirely, not to add a marker. If the answer to (1) is "it does take arguments
but they are complex," use `ANY` for the parts you cannot easily reference.

```python
# legitimate use: asyncio.create_task receives an internally-created coroutine
mock_create_task.assert_called_once()  # assert-no-args: coroutine is opaque; call count confirms task was scheduled

# wrong use: the function takes real arguments but this is easier than writing them out
mock_get_client.assert_called_once_with()  # assert-no-args  ← DO NOT DO THIS
```

**Auto-exempted methods:**

`flush()`, `commit()`, `rollback()`, and `close()` are automatically exempted
because they genuinely take no arguments. No annotation is needed for these.

## Choosing the Right Assertion

| Situation                             | Preferred assertion                                     |
| ------------------------------------- | ------------------------------------------------------- |
| Return value exists                   | `assert result == expected`                             |
| Side-effect only (void function)      | `mock.assert_called_once_with(args)`                    |
| Mock must not be called               | `mock.assert_not_called()`                              |
| Exception expected                    | `pytest.raises(ExceptionType)`                          |
| No return value, no mock to verify    | `assert True  # verifies no exception raised`           |
| Args truly opaque, call count matters | `mock.assert_called_once()  # assert-no-args: <reason>` |
