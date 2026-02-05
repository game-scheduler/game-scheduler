---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Channel Sync via Guild Sync Button

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260205-channel-sync-via-guild-sync-button-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260205-channel-sync-via-guild-sync-button-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/reactjs.instructions.md for all React/TypeScript code
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for service layer patterns
- #file:../../.github/instructions/api-authorization.instructions.md for authorization patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260205-channel-sync-via-guild-sync-button-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260205-channel-sync-via-guild-sync-button-plan.instructions.md](.copilot-tracking/plans/20260205-channel-sync-via-guild-sync-button-plan.instructions.md), [.copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md](.copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md), and [.copilot-tracking/research/20260205-channel-lazy-loading-guild-setup-research.md](.copilot-tracking/research/20260205-channel-lazy-loading-guild-setup-research.md) documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-channel-sync-via-guild-sync-button.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
