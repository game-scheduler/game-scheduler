---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Test Coverage Gaps

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260308-03-test-coverage-gaps-changes.md` in #file:../changes/ if it
does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260308-03-test-coverage-gaps.plan.md
task-by-task.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md — writing
  tests for already-implemented code (NOT the TDD stub-and-xfail cycle)
- #file:../../.github/instructions/integration-tests.instructions.md — integration and
  e2e test patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md
  for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**Before writing any test**, read the source file under test to understand the exact
behaviour at the uncovered lines. Use `coverage report --show-missing <file>` to confirm
which lines remain uncovered before and after each task.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260308-03-test-coverage-gaps-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to:
   - .copilot-tracking/planning/plans/20260308-03-test-coverage-gaps.plan.md
   - .copilot-tracking/planning/details/20260308-03-test-coverage-gaps-details.md
   - .copilot-tracking/research/20260308-03-test-coverage-gaps-research.md

   You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete
   .copilot-tracking/planning/prompts/implement-test-coverage-gaps.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with passing tests
- [ ] All detailed specifications satisfied
- [ ] No production code modified
- [ ] All new tests pass in unit, integration, and e2e suites as appropriate
- [ ] `scripts/coverage-report.sh` shows measurably improved coverage for all 10 target files
- [ ] Changes file updated continuously
