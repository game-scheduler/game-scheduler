---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Delayed Join Notification with Conditional Signup Instructions

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251218-signup-instructions-dm-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251218-signup-instructions-dm-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/coding-best-practices.instructions.md for general practices
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Implementation Notes

**Key Behavior Changes:**
- REMOVE immediate "You've joined" DMs from all join paths
- CREATE schedule for 60-second delayed notification on every join
- CONDITIONAL message based on game.signup_instructions presence
- CASCADE delete handles automatic cancellation

**Database Migration:**
- Run Alembic migration to add columns to notification_schedule
- Test both upgrade and downgrade paths
- Verify indexes created correctly

**Testing Requirements:**
- Update all existing reminder tests for renamed event type
- Add new tests for join notification (with and without signup instructions)
- Create integration tests for schedule creation and CASCADE cancellation
- Verify no immediate DMs sent in any join scenario

**Backward Compatibility:**
- Existing game reminder notifications MUST continue working
- notification_type defaults to 'reminder' for existing records
- Daemon processes both reminder and join_notification types

### Step 4: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251218-signup-instructions-dm-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20251218-signup-instructions-dm-plan.instructions.md](.copilot-tracking/plans/20251218-signup-instructions-dm-plan.instructions.md), [.copilot-tracking/details/20251218-signup-instructions-dm-details.md](.copilot-tracking/details/20251218-signup-instructions-dm-details.md), and [.copilot-tracking/research/20251218-signup-instructions-dm-research.md](.copilot-tracking/research/20251218-signup-instructions-dm-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-signup-instructions-dm.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] Database migration runs successfully (upgrade and downgrade)
- [ ] NotificationSchedule model updated with new columns
- [ ] Event system updated (NOTIFICATION_DUE replaces GAME_REMINDER_DUE)
- [ ] Event builder renamed and updated for both types
- [ ] Schedule helper function created
- [ ] API games service creates schedules on join (no immediate DMs)
- [ ] Bot join handler creates schedules on join (no immediate DMs)
- [ ] Bot event handler routes by notification_type
- [ ] Join notification handler sends conditional message
- [ ] All existing reminder tests pass with updated event type
- [ ] New join notification tests pass (with and without signup instructions)
- [ ] Integration tests verify schedule creation and CASCADE cancellation
- [ ] No Docker changes required (verified)
- [ ] All lint and type checks pass
- [ ] Changes file updated continuously with all modifications
- [ ] Line numbers updated if any referenced files changed
