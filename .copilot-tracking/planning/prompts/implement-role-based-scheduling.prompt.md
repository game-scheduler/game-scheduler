---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Role-Based Scheduling Method

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260324-01-role-based-scheduling-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement
#file:../plans/20260324-01-role-based-scheduling.plan.md task-by-task.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md — write failing tests first (xfail), then implement, then verify passing for every Python and TypeScript change
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for route and service layer changes
- #file:../../.github/instructions/reactjs.instructions.md for TemplateForm.tsx changes
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**TDD enforcement**: For every Python function or TypeScript component changed or added,
write the test file first with `pytest.mark.xfail` (or vitest `todo`) stubs, confirm the
tests fail, implement the code, then confirm all tests pass before moving to the next task.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260324-01-role-based-scheduling-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260324-01-role-based-scheduling.plan.md,
   .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md, and
   .copilot-tracking/research/20260324-01-role-based-scheduling-research.md documents.
   You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests (written TDD-first)
- [ ] `resolve_role_position` pure function in `shared/utils/participant_sorting.py`
- [ ] `seed_user_roles` method on `RoleChecker`
- [ ] `GameService.join_game` accepts optional `position_type`/`position` params
- [ ] API join route resolves and passes role priority
- [ ] Bot `handle_join_game` resolves from interaction payload and seeds cache
- [ ] Alembic migration applies and rolls back cleanly
- [ ] `TemplateForm.tsx` has draggable role-priority section (max 8, locked settings)
- [ ] `tests/e2e/test_role_based_signup.py` with 4 parametrized cases passes
- [ ] `partition_participants` and all 6 call sites are completely unchanged
- [ ] Changes file updated continuously
