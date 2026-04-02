---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Embed Deletion Detection and Auto-Cancellation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260402-01-embed-deletion-detection-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement
#file:../plans/20260402-01-embed-deletion-detection.plan.md task-by-task in the
order specified by the dependency constraints:

- Phase 1 tasks (1.1 → 1.2 → 1.3) must be implemented first in that order
- Phase 2 tasks (2.1 → 2.2) must follow Phase 1 completion
- Phase 3 tasks (3.1 → 3.2 → 3.3) must follow Phase 1 completion
- Phase 4 task (4.1) may be done at any point

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology — write a failing test stub before each implementation
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260402-01-embed-deletion-detection-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260402-01-embed-deletion-detection.plan.md,
   .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md,
   and .copilot-tracking/research/20260402-01-embed-deletion-detection-research.md
   documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Integration test verifies end-to-end cancellation via the `EMBED_DELETED` event path
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
