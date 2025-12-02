---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord Game Scheduling System

## Implementation Instructions

### Step 1: Verify new and modified code.

You WILL verify that any new or added code follows all rules and conventions as specified in these instruction files:

- #file:../../.github/instructions/coding-best-practices.instructions.md for best practices for all code
- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/reactjs.instructions.md for all ReactJS code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style

## Success Criteria

- [ ] All coding conventions followed
- [ ] The updates file should only describe meaningful changes made. Do not provide information about this verification prompt (e.g. "Fixed lint issues")
- [ ] All new code files have a copyright notice
  - [ ] Can be taken from existing files or added with scripts/add-copyright
- [ ] All import, commenting and documentation conventions followed
- [ ] All new and modified code has unit tests that focus on meaningful tests, not just coverage numbers, covering:
  - [ ] Business logic (where applicable)
  - [ ] Input validation
  - [ ] Edge cases
  - [ ] State Changes
  - [ ] Return Values
  - [ ] Error Handling
  - [ ] Achieve at lest 80% coverage. Report Test Coverage numbers in the updates file.
- [ ] All affected docker containers build
- [ ] All integration tests pass after rebuilding the containers (run with run-integration-tests.sh)
- [ ] All new and modified code files are free of compile and lint errors. It is very important that you run this step last because fixing other problems may introduce new errors.
