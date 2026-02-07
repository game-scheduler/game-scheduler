---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Game Creation Form Validation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260207-01-game-form-validation-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260207-01-game-form-validation-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/reactjs.instructions.md for all React/TypeScript code
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript conventions
- #file:../../.github/instructions/python.instructions.md for backend Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

**TDD REQUIREMENTS**:

- You WILL create stubs throwing errors BEFORE writing tests
- You WILL write failing tests expecting errors (RED phase)
- You WILL implement minimal solutions to pass tests (GREEN phase)
- You WILL update tests and refactor with passing tests (REFACTOR phase)
- You WILL NEVER skip or reorder TDD phases

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260207-01-game-form-validation-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260207-01-game-form-validation-plan.instructions.md, .copilot-tracking/details/20260207-01-game-form-validation-details.md, and .copilot-tracking/research/20260207-01-game-form-validation-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-game-form-validation.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] TDD methodology followed for all new code (Red-Green-Refactor)
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] All tests pass with 100% coverage for new code
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
