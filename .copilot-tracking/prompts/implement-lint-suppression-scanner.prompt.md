---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Lint Suppression Scanner Pre-commit Hook

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260301-02-lint-suppression-scanner-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260301-02-lint-suppression-scanner.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD phases (Phase 1)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md for the policy being enforced

**CRITICAL TDD Rules for Phase 1:**

- Task 1.1: Create `scripts/check_lint_suppressions.py` as a stub — module-level `BLOCKED_PATTERNS` and `COUNTED_PATTERNS` lists exist (importable), but `main()` raises `NotImplementedError`
- Task 1.2: Write ALL tests in `tests/unit/scripts/test_check_lint_suppressions.py` with REAL assertions marked `@pytest.mark.xfail(strict=True)` — do NOT write trivial placeholder tests
- Task 1.3: Implement `main()` fully using stdlib only (`re`, `subprocess`, `sys`, `os`), then remove xfail decorators WITHOUT changing any assertions — run pytest to confirm all pass
- Task 1.4: Refactor for clarity, add comprehensive edge case tests (no xfail), confirm all pass

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

**Script Algorithm (Task 1.3):**

1. `subprocess.run(["git", "diff", "--cached", "--unified=0"], capture_output=True, text=True)`
2. Track current filename from `+++ b/` diff headers
3. Collect lines with `+` prefix, skipping `+++` headers
4. Phase A: match each line against `BLOCKED_PATTERNS` → collect all violations → if any found, print each as `<file>:<line>: <matched text>` with framing error message, exit nonzero
5. Phase B: count matches against `COUNTED_PATTERNS` → compare to `int(os.environ.get("APPROVED_OVERRIDES", 0))` → if exceeded, print count error message, exit nonzero
6. Exit 0

Use exact error message templates from research Lines 67-82.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260301-02-lint-suppression-scanner-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260301-02-lint-suppression-scanner.plan.md, .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md, and .copilot-tracking/research/20260301-02-lint-suppression-scanner-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-lint-suppression-scanner.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] `scripts/check_lint_suppressions.py` implemented with two-phase scanning (stdlib only)
- [ ] All unit tests in `tests/unit/scripts/test_check_lint_suppressions.py` pass
- [ ] Hook entry added to `.pre-commit-config.yaml` after `jscpd-diff`
- [ ] `pre-commit run check-lint-suppressions` exits 0 on a clean working tree
- [ ] `.github/instructions/quality-check-overrides.instructions.md` updated with missing patterns and `APPROVED_OVERRIDES` pathway
- [ ] All project coding conventions followed
- [ ] Changes file updated continuously throughout implementation
