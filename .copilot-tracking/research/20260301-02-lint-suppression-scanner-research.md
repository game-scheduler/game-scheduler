<!-- markdownlint-disable-file -->

# Task Research Notes: Lint Suppression Scanner Pre-commit Hook

## Research Executed

### File Analysis

- `.pre-commit-config.yaml`
  - Comprehensive local hooks; tools run in this order: pre-commit-hooks → copyright → ruff → prettier/eslint → python-compile → mypy → pytest-coverage → diff-coverage → frontend-build → typescript → vitest-coverage → diff-coverage-frontend → complexipy → lizard-typescript → jscpd-generate → jscpd-diff
  - New hook belongs after `jscpd-diff` (last substantive check before optional/manual hooks)
- `pyproject.toml`
  - ruff configured with extensive rule set; `warn_unused_ignores = true` in mypy section
  - `[tool.ruff.lint.per-file-ignores]` section shows existing legitimate suppressions in tests/
- `scripts/wrappers/git`
  - Established pattern: intercept → block raw mechanism → provide `APPROVED_` prefixed alternative
  - Error messages reference `.github/instructions/quality-check-overrides.instructions.md`
- `scripts/check-copyright-precommit.sh`
  - Script style: `set -e`, uses `git diff --cached`, iterates staged files
- `.github/instructions/quality-check-overrides.instructions.md`
  - Already lists all suppression patterns as prohibited actions
  - Missing: `# noqa: complexipy`, `#lizard forgives` patterns, and the `APPROVED_OVERRIDES` approval pathway

### External Research

- #fetch:https://github.com/terryyin/lizard
  - `#lizard forgives` — suppresses all warnings for a function (place inside or before function)
  - `#lizard forgives(metric1, metric2)` — selective forgiveness for specific metrics (e.g. `length`, `cyclomatic_complexity`)
  - `#lizard forgive global` — suppresses warnings for all code outside functions
  - All three forms must be scanned; the selective form is analogous to `# noqa: CODE` (specific, count-based)
- #fetch:https://github.com/rohaquinlop/complexipy
  - `# noqa: complexipy` — inline ignore for a function's cognitive complexity
  - Place on function definition line or line immediately above
  - Optional reason text in parentheses is ignored by the parser
  - This is count-based (specific suppression), not a blanket

### Project Conventions

- Standards referenced: `scripts/wrappers/git` approval pattern, `quality-check-overrides.instructions.md`
- `APPROVED_SKIP` → converts to `SKIP`; parallel: `APPROVED_OVERRIDES` → permits N suppressions
- Error messages never expose the environment variable name; direct users to the instructions file

## Key Discoveries

### Suppression Pattern Matrix

| Pattern                            | Tool            | Bare/Blanket?                     | Treatment                                              |
| ---------------------------------- | --------------- | --------------------------------- | ------------------------------------------------------ |
| `# noqa`                           | ruff            | Yes — suppresses all lint on line | Always block, no override possible                     |
| `# ruff: noqa`                     | ruff            | Yes — suppresses entire file      | Always block, no override possible                     |
| `# noqa: CODE`                     | ruff            | No — specific rule                | Count-based, blocked if count > `APPROVED_OVERRIDES`   |
| `# type: ignore`                   | mypy            | Yes — suppresses all type errors  | Always block, no override possible                     |
| `# type: ignore[code]`             | mypy            | No — specific error               | Count-based                                            |
| `# noqa: complexipy`               | complexipy      | No — specific tool                | Count-based                                            |
| `#lizard forgives`                 | lizard          | Yes — all metrics for function    | Count-based (specific by nature, targets one function) |
| `#lizard forgives(metric)`         | lizard          | No — specific metric              | Count-based                                            |
| `#lizard forgive global`           | lizard          | Yes — all global code             | Always block                                           |
| `// @ts-ignore`                    | TypeScript/mypy | Yes — all TS errors on next line  | Always block                                           |
| `// @ts-expect-error`              | TypeScript      | No — expected specific error      | Count-based                                            |
| `// eslint-disable` (any form)     | ESLint          | Yes — line or block               | Always block                                           |
| `// eslint-disable-next-line CODE` | ESLint          | No — specific rule                | Count-based                                            |

### Error Message Design

Mirrors `scripts/wrappers/git` exactly — no mechanism names exposed:

**Bare/blanket suppression (no override path):**

```
ERROR: Bare/blanket quality check suppression detected in staged changes.
  <file>:<line>: <matched text>
This suppresses checks entirely and is never permitted.
See .github/instructions/quality-check-overrides.instructions.md for policy details.
```

**Specific suppression without approval:**

```
ERROR: 2 quality check suppression(s) added in staged changes.
These require explicit user approval before committing.
See .github/instructions/quality-check-overrides.instructions.md for policy details.
```

### Scanning Logic

- Input: `git diff --cached --unified=0`
- Count only lines with `+` prefix (newly added), excluding `+++` file headers
- Two categories evaluated separately:
  1. **Permanently blocked**: any match → immediate failure, list offending lines
  2. **Count-based**: total added count compared to `APPROVED_OVERRIDES` (default: 0)
- `APPROVED_OVERRIDES=N` permits exactly N count-based suppressions per commit; no banking across commits

### Hook Placement

After `jscpd-diff`, before optional/manual section. This ensures:

- All linters/scanners have run first (suppressions only matter once we know what they're suppressing)
- Consistent with the hook being a meta-check on suppression attempts

### Files to Create/Modify

| Action   | File                                                           |
| -------- | -------------------------------------------------------------- |
| Create   | `scripts/check_lint_suppressions.py`                           |
| Add hook | `.pre-commit-config.yaml` (after `jscpd-diff`)                 |
| Update   | `.github/instructions/quality-check-overrides.instructions.md` |

### quality-check-overrides.instructions.md Updates Needed

1. Add `# noqa: complexipy` and `#lizard forgives` / `#lizard forgives(metric)` / `#lizard forgive global` to the Linter Suppression Comments list
2. Add a section documenting the `APPROVED_OVERRIDES` approval pathway (analogous to `--approved-no-verify` and `APPROVED_SKIP`)

## Recommended Approach

Single Python script `scripts/check_lint_suppressions.py` invoked as a local pre-commit hook with `language: python` and no `additional_dependencies` (stdlib only: `re`, `subprocess`, `sys`). The script:

1. Reads `git diff --cached --unified=0` once via `subprocess.run`, processes all `+`-prefixed added lines (excluding `+++` file headers), tracking the current filename from `+++ b/` headers
2. Matches against permanently-blocked patterns (two compiled `list[re.Pattern]`) — fails immediately if any found, listing each offending line with file and line number
3. Matches against count-based patterns — sums total matches, compares to `int(os.environ.get("APPROVED_OVERRIDES", 0))`, fails with count message if exceeded
4. Exits 0 only if both checks pass

This follows the established project pattern: `scripts/check_commit_duplicates.py` uses the identical hook configuration (`entry: python scripts/...`, `language: python`) for comparable diff-scanning logic. Python is preferred over bash for this script because the 13-pattern matrix across two categories is expressed cleanly as two lists of compiled `re.Pattern` objects — readable, auditable, and easy to extend — whereas bash requires separate grep invocations with complex shell quoting for each pattern. The stdlib-only requirement means no `additional_dependencies` in the hook config.

## Implementation Guidance

- **Objectives**: Catch AI agent attempts to silence linters via inline suppression comments; enforce explicit human approval for any such suppression
- **Key Tasks**:
  1. Create `scripts/check_lint_suppressions.py` with two-phase scanning logic (stdlib only: `re`, `subprocess`, `sys`, `os`)
  2. Add pre-commit hook entry after `jscpd-diff` in `.pre-commit-config.yaml` with `language: python`, `pass_filenames: false`, no `additional_dependencies`
  3. Update `.github/instructions/quality-check-overrides.instructions.md` with new patterns and `APPROVED_OVERRIDES` pathway documentation
- **Dependencies**: None beyond Python stdlib (Python runtime already used by pre-commit for `jscpd-diff` and other hooks)
- **Success Criteria**:
  - Bare `# noqa` in a staged file causes hook to fail with clear message pointing to instructions
  - `# noqa: ERA001` in a staged file fails when `APPROVED_OVERRIDES` is unset or 0
  - `APPROVED_OVERRIDES=1` with exactly one `# noqa: ERA001` addition passes
  - `APPROVED_OVERRIDES=1` with one bare `# noqa` still fails (bare is never permitted)
  - All TypeScript and Python suppression patterns are caught in a single hook run
  - Hook passes cleanly on commits with no suppression comments
