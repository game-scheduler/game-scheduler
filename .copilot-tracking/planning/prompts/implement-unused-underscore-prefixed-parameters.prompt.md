---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remove Obsolete and Deprecated Function Parameters

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260425-01-unused-underscore-prefixed-parameters-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260425-01-unused-underscore-prefixed-parameters.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**IMPORTANT**: Work through phases in order (1 → 2 → 3 → 4 → 5 → 6 → 7). Phases 1–3 are ordered by dependency (access-token chain, bottom-up). Phases 4–7 are independent but should follow Phase 3.

**IMPORTANT**: After removing each parameter, use `grep` to verify no call sites remain that still pass the removed argument before proceeding to the next task.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260425-01-unused-underscore-prefixed-parameters-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260425-01-unused-underscore-prefixed-parameters.plan.md, .copilot-tracking/planning/details/20260425-01-unused-underscore-prefixed-parameters-details.md, and .copilot-tracking/research/20260425-01-unused-underscore-prefixed-parameters-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] No function in production code accepts a deprecated or never-referenced parameter
- [ ] All production and test callers updated
- [ ] `uv run pytest tests/unit` passes
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
