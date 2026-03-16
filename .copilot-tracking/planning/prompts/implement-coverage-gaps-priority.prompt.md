---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Coverage Gap Priority Improvements

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260316-03-coverage-gaps-priority-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260316-03-coverage-gaps-priority.plan.md task-by-task

**Note on TDD methodology**: These are tests written for already-implemented code. Do NOT apply
the stub-and-xfail TDD cycle. Write tests directly against the existing implementation per the
"Writing Tests for Already-Implemented Code" guidance in the TDD instructions.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/test-driven-development.instructions.md for test methodology
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**Phase 1 must be completed and verified before continuing** — run `scripts/coverage-report.sh`
after Phase 1 to confirm `notification_service.py` is now reported at ≥95%.

For Phase 4 integration tests, each test must be run inside the integration test environment using
`scripts/run-integration-tests.sh` with at least a 600000ms timeout.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260316-03-coverage-gaps-priority-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260316-03-coverage-gaps-priority.plan.md, .copilot-tracking/planning/details/20260316-03-coverage-gaps-priority-details.md, and .copilot-tracking/research/20260316-03-coverage-gaps-priority-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/planning/prompts/implement-coverage-gaps-priority.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] Phase 1: signal test fixed; `notification_service.py` reports ≥95% in combined coverage
- [ ] Phase 2: all five unit test tasks complete; per-module coverage targets met
- [ ] Phase 3: Redis, guild sync, and Discord client error paths covered; per-module targets met
- [ ] Phase 4: integration tests for auth/games/templates routes covering error responses
- [ ] Phase 5: all utility and minor gap fill tasks complete
- [ ] Combined coverage ≥92% confirmed via `scripts/coverage-report.sh`
- [ ] All new tests pass (`uv run pytest tests/unit/`)
- [ ] No lint suppressions added without explicit user approval
- [ ] Changes file updated continuously throughout implementation
