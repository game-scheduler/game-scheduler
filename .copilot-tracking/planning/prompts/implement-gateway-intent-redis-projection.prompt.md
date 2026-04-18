---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord Gateway Intent Redis Projection

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260418-01-gateway-intent-redis-projection-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260418-01-gateway-intent-redis-projection.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow (stub + xfail before implementation for all new production code)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md — no lint suppressions or pre-commit bypasses without explicit user approval

**Phase dependency rules:**

- Phases 1–2 (bot side) must be complete before any Phase 4 call site migration
- Phase 3 (API reader) may be developed in parallel with Phase 2
- Phase 5 is safe only after all Phase 4 tasks are fully complete and verified

**Discord Developer Portal prerequisite:** Before deploying Phase 1, confirm with the user that the "Server Members Intent" toggle has been enabled in the Discord Developer Portal for the bot application. Do NOT skip this step.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260418-01-gateway-intent-redis-projection-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260418-01-gateway-intent-redis-projection.plan.md, .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md, and .copilot-tracking/research/20260418-01-gateway-intent-redis-projection-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] TDD followed: stub + xfail test written and confirmed failing before each new implementation
- [ ] `GUILD_MEMBERS` intent enabled in bot; Discord Developer Portal toggle confirmed
- [ ] `guild_projection.py` writer: gen flip happens after all data writes; OTel instruments fire correctly
- [ ] `member_projection.py` reader: gen-rotation retry handles up to 3 iterations (max 6 GETs); OTel counters fire correctly
- [ ] All four call sites in Phase 4 migrated; zero Discord REST calls from API after Phase 4
- [ ] Dead code removed; `user_display_names` table dropped via Alembic migration
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
