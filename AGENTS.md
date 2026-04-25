# Codex Instructions (Global)

This file provides global guidance for Codex. It intentionally avoids duplicating content.
Follow the referenced instruction files as the single source of truth.

## Always Follow

- `.github/copilot-instructions.md`
- `.github/instructions/coding-best-practices.instructions.md`
- `.github/instructions/self-explanatory-code-commenting.instructions.md`
- `.github/instructions/taming-copilot.instructions.md`
  - Note: The "declare intent before tool use" rule is relaxed for Codex.
- `.github/instructions/quality-check-overrides.instructions.md`
  - Applies when bypassing quality checks, suppressing lints, or during commit/push flows.
- `.github/instructions/commit-messages.instructions.md`
  - Applies when creating git commits.

## Conditional Guidance

- When writing or editing prompts of any kind (including prompt files, prompts embedded in code for agentic AI apps, or prompts a user will copy/paste):
  - Also follow `.github/instructions/prompt.instructions.md`.
  - Also follow `.github/instructions/ai-prompt-engineering-safety-best-practices.instructions.md`.
- When asked to create a research document:
  - Follow `.copilot-tracking/research/AGENTS.md`.
- When asked to create planning files (plans, details, or implementation prompts):
  - Follow `.copilot-tracking/planning/AGENTS.md`.
- When asked to implement a plan:
  - Open and follow the matching `.copilot-tracking/planning/prompts/implement-*.prompt.md` file if it exists.
  - If the prompt file is not specified, list available prompts or use `scripts/show-implement-prompt.sh` to locate one.

## Domain-Specific Guidance

- Frontend work:
  - `.github/instructions/reactjs.instructions.md`
  - `.github/instructions/typescript-5-es2022.instructions.md`

- Backend/services work:
  - `.github/instructions/python.instructions.md`
  - `.github/instructions/fastapi-transaction-patterns.instructions.md`
  - `.github/instructions/api-authorization.instructions.md`

- Testing:
  - `.github/instructions/test-driven-development.instructions.md`
  - `.github/instructions/unit-tests.instructions.md`
  - `.github/instructions/integration-tests.instructions.md`

- Containerization:
  - `.github/instructions/containerization-docker-best-practices.instructions.md`

- CI/CD workflows:
  - `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
