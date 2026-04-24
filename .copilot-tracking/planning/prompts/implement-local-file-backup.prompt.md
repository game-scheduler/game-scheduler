---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Local File Backup Support

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260424-01-local-file-backup-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260424-01-local-file-backup.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260424-01-local-file-backup-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260424-01-local-file-backup.plan.md, .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md, and .copilot-tracking/research/20260424-01-local-file-backup-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented
- [ ] No `BACKUP_S3_BUCKET` references remain in any file
- [ ] No `RESTORE_BACKUP_KEY` references remain in any file
- [ ] All `config/env.*` files match `config.template/env.template` backup section structure
- [ ] Changes file updated continuously
