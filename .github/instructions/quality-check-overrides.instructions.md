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

## Required Approval Process

Before implementing any override:

1. **Explain the Need**: Clearly state why the override is necessary
   - What specific issue prevents passing the check?
   - Why can't the code be modified to pass the check?
   - What is the impact of leaving the check in place?

2. **Present Alternatives**: Show what alternatives were considered
   - Can the code be refactored to pass the check?
   - Is there a better pattern that satisfies the check?
   - Can the issue be addressed in a different way?

3. **Request Permission**: Explicitly ask the user for approval
   - State exactly what will be overridden
   - Confirm the user understands the implications
   - Wait for explicit "yes" or approval before proceeding

4. **Document the Override**: If approved, document why
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
