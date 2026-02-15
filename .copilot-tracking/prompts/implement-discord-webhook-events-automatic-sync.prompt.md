---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord Webhook Events for Automatic Guild Sync

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260214-01-discord-webhook-events-automatic-sync-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260214-01-discord-webhook-events-automatic-sync.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for transaction management
- #file:../../.github/instructions/api-authorization.instructions.md for authorization patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL TDD REQUIREMENTS**:

- For each new function (signature validation, webhook endpoint, bot sync, channel refresh):
  - Task N.1: Create stub with NotImplementedError
  - Task N.2: Write failing tests expecting NotImplementedError (RED)
  - Task N.3: Implement minimal working solution (GREEN)
  - Task N.4: Update tests to verify actual behavior (GREEN)
  - Task N.5: Refactor with comprehensive edge case tests (REFACTOR)

- NEVER implement functionality without tests first
- NEVER skip the stub → test → implement → update test → refactor cycle
- Each task must be verifiable with passing tests before proceeding

**CRITICAL SECURITY REQUIREMENTS**:

- Ed25519 signature validation MUST reject invalid signatures with 401
- DISCORD_PUBLIC_KEY MUST be validated as hex string
- Request body MUST NOT be parsed before signature validation
- Timestamp concatenation MUST match Discord specification exactly

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260214-01-discord-webhook-events-automatic-sync-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260214-01-discord-webhook-events-automatic-sync.plan.md, .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md, and .copilot-tracking/research/20260214-01-discord-webhook-events-automatic-sync-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-discord-webhook-events-automatic-sync.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] TDD methodology followed for all new functions (stub → test → implement → update test → refactor)
- [ ] Ed25519 signature validation working correctly
- [ ] Webhook endpoint responds correctly to PING and APPLICATION_AUTHORIZED
- [ ] Bot sync creates new guilds without user authentication
- [ ] Channel refresh updates database on demand
- [ ] Test coverage >90% for all new code
- [ ] Integration tests verify end-to-end functionality
- [ ] Documentation complete for Discord portal configuration
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
