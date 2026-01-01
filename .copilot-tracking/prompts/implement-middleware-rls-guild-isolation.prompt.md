---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Middleware-Based Guild Isolation with RLS

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260101-middleware-rls-guild-isolation-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260101-middleware-rls-guild-isolation-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker files
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/integration-tests.instructions.md for integration tests
- #file:../../.github/instructions/coding-best-practices.instructions.md for general practices

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Test-First Methodology

You WILL follow test-first development:
1. Write tests BEFORE implementing functionality
2. Verify tests fail initially (red)
3. Implement functionality
4. Verify tests pass (green)
5. Run full test suite to ensure no regressions

### Step 4: Incremental Validation

After EACH task completion, you WILL:
1. Run relevant unit tests
2. Run relevant integration tests
3. Run E2E tests if applicable
4. Verify zero breaking changes
5. Update changes file with test results

### Step 5: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260101-middleware-rls-guild-isolation-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to:
   - [Plan file](.copilot-tracking/plans/20260101-middleware-rls-guild-isolation-plan.instructions.md)
   - [Details file](.copilot-tracking/details/20260101-middleware-rls-guild-isolation-details.md)
   - [Research file](.copilot-tracking/research/20260101-middleware-rls-guild-isolation-research.md)

   You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete `.copilot-tracking/prompts/implement-middleware-rls-guild-isolation.prompt.md`

## Success Criteria

- [ ] Changes tracking file created
- [ ] Phase 0: Database users configured with RLS enforcement validated
- [ ] Phase 1: Infrastructure complete (ContextVars, event listener, dependency, RLS policies disabled)
- [ ] Phase 2: All service factories migrated to use enhanced dependency
- [ ] Phase 3: RLS enabled on all tables, E2E guild isolation verified
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Zero breaking changes to existing code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has tests
- [ ] Changes file updated continuously
- [ ] Production readiness verified
