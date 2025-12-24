---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Participant Ordering Schema Refactoring

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251224-participant-ordering-schema-refactor-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251224-participant-ordering-schema-refactor-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/coding-best-practices.instructions.md for general coding standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL TESTING REQUIREMENT**: Tests MUST be updated and passing at the end of EACH phase before proceeding to the next phase. This is a fundamental requirement - do NOT defer test updates to later phases.

**Testing Approach**:

- Phase 1: Update and verify database schema tests pass
- Phase 2: Update model/schema test fixtures, verify tests pass before proceeding
- Phase 3: Update sorting test fixtures, verify all sorting tests pass before proceeding
- Phase 4: Update service test fixtures, verify all service tests pass before proceeding
- Phase 5: Update API test fixtures, verify all API tests pass before proceeding
- Phase 6: Update remaining test fixtures, verify full test suite passes
- Phase 7: Integration, E2E, and manual validation

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251224-participant-ordering-schema-refactor-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20251224-participant-ordering-schema-refactor-plan.instructions.md, .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md, and .copilot-tracking/research/20251224-participant-ordering-schema-refactor-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-participant-ordering-schema-refactor.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Tests updated and passing incrementally after each phase (not deferred)
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
