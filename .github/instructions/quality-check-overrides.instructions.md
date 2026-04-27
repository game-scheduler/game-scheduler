---
description: 'Require explicit user approval before overriding any pre-commit checks, lint rules, or code quality standards'
applyTo: '**'
---

# Quality Check Override Policy

This project enforces code quality through automated checks including pre-commit hooks, linters, formatters, and other validation tools. These checks exist to maintain consistency and catch issues early.

## Core Rule: No Silent Overrides

**NEVER override, bypass, or suppress quality checks without explicit user approval.**

## Prohibited Actions Without Approval

The following actions require explanation and explicit user consent before implementation:

### Git Commit Bypasses

- **`git commit --no-verify`**: Skips all pre-commit hooks
- **`git commit -n`**: Short form of `--no-verify`
- **`git push --no-verify`**: Skips pre-push hooks

### Pre-commit Specific Bypasses

- **`SKIP=<hook-name> git commit`**: Skips specific pre-commit hooks
- **`SKIP=<hook-1>,<hook-2> git commit`**: Skips multiple pre-commit hooks
- Modifying `.pre-commit-config.yaml` to disable or remove hooks
- Setting `fail_fast: false` or similar configuration to hide failures

### Linter Suppression Comments

- **`# noqa`**: Suppresses all linting errors on a line (Python, general)
- **`# noqa: <code>`**: Suppresses specific linting error codes
- **`# type: ignore`**: Suppresses type checking errors (Python, mypy)
- **`# pylint: disable=<rule>`**: Disables specific Pylint rules
- **`# ruff: noqa`**: Suppresses Ruff linting errors
- **`// eslint-disable-next-line`**: Disables ESLint for next line (JavaScript/TypeScript)
- **`/* eslint-disable */`**: Disables ESLint for entire file or sections
- **`// @ts-ignore`**: Suppresses TypeScript errors
- **`// @ts-expect-error`**: Suppresses expected TypeScript errors
- **`# noqa: complexipy`**: Suppresses complexipy cognitive complexity check
- **`#lizard forgives`**: Suppresses all lizard warnings for a function
- **`#lizard forgives(metric)`**: Suppresses a specific lizard metric for a function
- **`#lizard forgive global`**: Suppresses all lizard warnings for global code
- Any inline comment designed to silence warnings or errors

### Configuration Modifications

- Loosening or disabling rules in configuration files:
  - `.pre-commit-config.yaml`
  - `pyproject.toml` (ruff, mypy, pytest, coverage settings)
  - `eslint.config.js`
  - `tsconfig.json`
  - `complexipy.json`
  - Any other linting or quality tool configuration
- Reducing coverage thresholds
- Increasing complexity limits
- Disabling specific rules or checks

### Test Bypasses

- Skipping tests with decorators like `@pytest.mark.skip`
- Using `pytest -k` to exclude specific tests
- Commenting out test cases
- Modifying test configuration to reduce coverage requirements

## `APPROVED_OVERRIDES` Environment Variable

Some specific (non-blanket) suppression comments are gated rather than permanently blocked.
The `check-lint-suppressions` pre-commit hook enforces this gate.

- **What it controls**: The number of specific/count-based suppression comments permitted in a single commit
- **Does NOT apply to bare/blanket suppressions**: Bare suppressions (`# noqa`, `# type: ignore`, `// @ts-ignore`, `/* eslint-disable */`, `#lizard forgive global`, etc.) are always blocked with no override path
- **Resets per commit**: No banking across commits — each commit requires its own approval
- **Usage**: `APPROVED_OVERRIDES=2 git commit -m "..."` to permit exactly two specific suppressions in that commit

This mirrors the `APPROVED_SKIP` mechanism for `SKIP`-based bypasses.

## `APPROVED_WEAK_ASSERTIONS` Environment Variable

`# assert-not-weak: <reason>` annotations in test files are counted per commit. If the count
exceeds `APPROVED_WEAK_ASSERTIONS`, the commit is blocked.

- **What it controls**: The number of `# assert-not-weak: <reason>` annotations permitted in a single commit
- **Resets per commit**: No banking across commits — each commit requires its own approval
- **Usage**: `APPROVED_WEAK_ASSERTIONS=2 git commit -m "..."` to permit exactly two annotations

**Before requesting any value of `APPROVED_WEAK_ASSERTIONS`, verify each annotation individually.**
For each `# assert-not-weak: <reason>` you plan to add, answer:

1. Does the function under test actually take no arguments?
2. Are there arguments passed to this call in the code under test that, if wrong, would produce incorrect behavior?
3. If there are arguments, can they be named in the assertion (or approximated with `ANY`)?

If the answers to (2) and (3) are both yes, **the right fix is `assert_called_once_with(...)`,
not `# assert-not-weak: <reason>`**.

**Common false justification — "constructor args are internal/opaque":**

Constructor arguments are not opaque if the code under test explicitly passes them. If the
code does:

```python
embed = discord.Embed(title=game.title, description=game.description, color=status_color)
```

then `title`, `description`, and `color` are all verifiable and should be verified.
Claiming they are "internal/opaque" is factually wrong — a bug that passes the wrong title
would not be caught by `assert_called_once()` but would be caught by
`assert_called_once_with(title=expected_title, description=expected_description, color=expected_color)`.

Before writing any `# assert-not-weak: <reason>` on a constructor call, look at the actual call site
and ask: "Are named arguments passed here?" If yes, those arguments must be verified.

## Required Approval Process

**Your justification will be questioned.** The user will ask follow-up questions to test
whether the bypass is genuinely necessary. Do the cross-examination yourself first:

- For each `# assert-not-weak: <reason>`: Could I write `assert_called_once_with(...)` with real arguments
  here? If yes, that is the right fix, not a marker.
- For each `APPROVED_OVERRIDES`: Is this a genuine false positive, or is the check flagging
  real complexity I am avoiding?
- For each `SKIP=<hook>`: Is the hook failing because the code is wrong, or because the check
  itself is wrong?

**If a single follow-up question would change your answer, your justification is not ready.**
Fix the code instead of preparing a better-sounding justification.

Before implementing any override:

1. **Self-verify first**: Run the cross-examination above before presenting the request.
   If you cannot answer "yes, the function genuinely takes no meaningful arguments" for
   each `# assert-not-weak: <reason>`, stop and write real assertions instead.

2. **Explain the Need**: Clearly state why the override is necessary
   - What specific issue prevents passing the check?
   - Why can't the code be modified to pass the check?
   - What is the impact of leaving the check in place?

3. **Present Alternatives**: Show what alternatives were considered
   - Can the code be refactored to pass the check?
   - Is there a better pattern that satisfies the check?
   - Can the issue be addressed in a different way?

4. **Request Permission**: Explicitly ask the user for approval
   - State exactly what will be overridden
   - Confirm the user understands the implications
   - Wait for explicit "yes" or approval before proceeding

5. **Document the Override**: If approved, document why
   - Add a comment explaining the reason for the override
   - Include a reference to the discussion or ticket if applicable

## Example Approval Request

```markdown
I need to override the complexity check for function `process_game_signup` because:

**Issue**: The function has a complexity of 12, exceeding the limit of 10.

**Why Override Needed**: Refactoring this function would require splitting
participant validation logic across multiple functions, which would actually
reduce readability and make the code harder to maintain.

**Alternatives Considered**:

- Extracting validation logic: Would create many small functions with unclear boundaries
- Simplifying logic: Already using early returns and clear conditionals

**Proposed Override**: Add `# noqa: C901` to suppress the complexity warning

**May I proceed with this override?**
```

## Legitimate Reasons for Overrides

Valid reasons that may justify overrides include:

- **External API constraints**: Third-party library requires specific patterns that trigger warnings
- **Performance critical code**: Optimization requires patterns that violate style guidelines
- **Type system limitations**: Known type system bugs or limitations
- **False positives**: Tool incorrectly flags valid code (explain why it's a false positive)
- **Temporary workarounds**: Documented short-term fix with plan to resolve properly

## Invalid Reasons for Overrides

These are NOT acceptable reasons to override checks:

- "The check is annoying"
- "It's faster to skip it"
- "The code works fine as-is"
- "I don't understand why it's failing"
- "Too many errors to fix"
- Making changes would require too much work
- "Given the time constraints" or similar schedule-based justifications

## When in Doubt

If you're unsure whether an override is appropriate:

1. **Stop and ask**: Present the situation to the user before proceeding
2. **Seek to understand**: Make sure you understand why the check is failing
3. **Try to fix properly**: Attempt to address the root cause first
4. **Never assume**: Don't assume overrides are acceptable without asking

## Summary

Quality checks exist for good reasons. Treat them as valuable feedback, not obstacles. Always fix the underlying issue when possible. When overrides are truly necessary, make them visible, justified, and approved.
