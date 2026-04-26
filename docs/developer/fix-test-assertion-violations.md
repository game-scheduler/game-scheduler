# Fixing `check-test-assertions` Violations

The `check-test-assertions` pre-commit hook blocks test functions with zero
assertions. This document explains each violation type and how to fix it.

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

## Choosing the Right Assertion

| Situation                          | Preferred assertion                           |
| ---------------------------------- | --------------------------------------------- |
| Return value exists                | `assert result == expected`                   |
| Side-effect only (void function)   | `mock.assert_called_once_with(args)`          |
| Mock must not be called            | `mock.assert_not_called()`                    |
| Exception expected                 | `pytest.raises(ExceptionType)`                |
| No return value, no mock to verify | `assert True  # verifies no exception raised` |

Prefer `assert_called_once_with(...)` over `assert_called_once()` — the former
verifies the arguments too. See the unit test standards for more detail.
