---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Scheduler Daemon Consolidation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260305-01-scheduler-daemon-consolidation-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260305-01-scheduler-daemon-consolidation.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker files
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260305-01-scheduler-daemon-consolidation-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260305-01-scheduler-daemon-consolidation.plan.md, .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md, and .copilot-tracking/research/20260305-01-scheduler-daemon-consolidation-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-scheduler-daemon-consolidation.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] `service_name` added to `SchedulerDaemon` with log and OTel integration
- [ ] Unified `scheduler_daemon_wrapper.py` with thread lifecycle and signal handling
- [ ] `docker/scheduler.Dockerfile` builds successfully
- [ ] All compose files updated; old three service names absent
- [ ] Old wrapper files and Dockerfiles deleted
- [ ] CI/CD workflow references `scheduler`, not `notification-daemon`
- [ ] Per-daemon log level env vars replaced by `SCHEDULER_LOG_LEVEL`
- [ ] In-code comments and docstrings updated (`services/`, `shared/`, `tests/`)
- [ ] All tests pass with no regressions
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
