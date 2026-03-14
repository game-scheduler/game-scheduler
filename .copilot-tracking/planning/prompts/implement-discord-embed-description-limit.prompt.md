---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord Embed Description Length Fix

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260314-01-discord-embed-description-limit-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260314-01-discord-embed-description-limit.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD phases
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript changes
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260314-01-discord-embed-description-limit-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260314-01-discord-embed-description-limit.plan.md, .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md, and .copilot-tracking/research/20260314-01-discord-embed-description-limit-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/planning/prompts/implement-discord-embed-description-limit.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
