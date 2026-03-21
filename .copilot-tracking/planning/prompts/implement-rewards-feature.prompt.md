---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Rewards Feature

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260321-02-rewards-feature-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Verify Prerequisite

You WILL confirm the bug fix from `20260321-01-*` is already implemented before proceeding. The Save and Archive flow (Task 5.2, 5.3) depends on it. If it is not in place, implement that plan first.

### Step 3: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260321-02-rewards-feature.plan.md task-by-task, following TDD:

- For each Phase 6 test task, write the tests first (they will xfail), then implement the production code for the relevant earlier phase, then verify the tests pass.
- For Phases 1-5, write unit tests alongside each change.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for service patterns
- #file:../../.github/instructions/reactjs.instructions.md for React components
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/integration-tests.instructions.md for integration test patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 4: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260321-02-rewards-feature-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260321-02-rewards-feature.plan.md, .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md, and .copilot-tracking/research/20260321-02-rewards-feature-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] Prerequisite bug fix verified present
- [ ] Alembic migration created and upgrades cleanly
- [ ] Models, schemas, service, and routes updated with rewards fields
- [ ] Discord embed shows `||rewards||` spoiler when rewards set
- [ ] Host DM sent at COMPLETED when `remind_host_rewards=True` and rewards empty
- [ ] Frontend rewards textarea status-gated, checkbox always visible
- [ ] Save and Archive button functional and triggers archival within ~1 second
- [ ] Spoiler display in GameDetails and GameCard
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] All new and modified code passes lint
- [ ] Changes file updated continuously
