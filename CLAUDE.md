# Claude Code Instructions Index

This file indexes the instruction files in `.github/instructions/`. Each entry includes the description, scope (applyTo patterns), and guidance on when to apply it.

---

## Core Language & Coding Standards

### Python

**Path:** `.github/instructions/python.instructions.md`
**Scope:** `**/*.py`
**When to use:** Working on any Python file. Covers TDD, type hints, Ruff linting, docstrings, code style, imports, and naming conventions.

### Coding Best Practices

**Path:** `.github/instructions/coding-best-practices.instructions.md`
**When to use:** General guidance for any code changes. Cross-language best practices.

### Self-Explanatory Code & Commenting

**Path:** `.github/instructions/self-explanatory-code-commenting.instructions.md`
**When to use:** When writing code that needs inline commentary or documentation.

---

## Architecture & Framework Patterns

### FastAPI Transaction Patterns

**Path:** `.github/instructions/fastapi-transaction-patterns.instructions.md`
**Scope:** `services/api/routes/*.py`, `services/api/services/*.py`
**When to use:** Working on FastAPI route handlers or service layer functions. Covers transaction management, dependency injection, and session handling.

### API Authorization

**Path:** `.github/instructions/api-authorization.instructions.md`
**When to use:** Implementing or modifying API endpoints, authentication, or permission checks.

### Containerization & Docker

**Path:** `.github/instructions/containerization-docker-best-practices.instructions.md`
**When to use:** Working with Docker configuration, container setup, or containerized services.

---

## Testing

### Test-Driven Development (TDD)

**Path:** `.github/instructions/test-driven-development.instructions.md`
**When to use:** Writing new Python functionality. Covers the RED→GREEN→REFACTOR workflow with pytest and xfail markers.

### Unit Test Quality

**Path:** `.github/instructions/unit-tests.instructions.md`
**Scope:** `**/test_*.py`
**When to use:** Writing any unit test. Covers falsifiability, required assertions, mock call-verification patterns, and coverage theater anti-patterns.

### Integration Tests

**Path:** `.github/instructions/integration-tests.instructions.md`
**When to use:** Writing or running integration test suites with real infrastructure.

### Test Execution Rules

**Path:** `.github/instructions/test-execution.instructions.md`
**Scope:** `**` (all files)
**When to use:** Running `scripts/run-integration-tests.sh` or `scripts/run-e2e-tests.sh`. Critical: always capture full output with `tee`.

---

## Commit & Quality

### Commit Messages

**Path:** `.github/instructions/commit-messages.instructions.md`
**When to use:** Creating git commits. Covers message format and conventions.

### Quality Check Overrides

**Path:** `.github/instructions/quality-check-overrides.instructions.md`
**When to use:** Need to override or suppress quality checks with `noqa` comments.

### Copyright Headers

**Path:** `.github/instructions/copyright-headers.instructions.md`
**When to use:** Creating new files that need copyright/license headers.

---

## DevOps & CI/CD

### GitHub Actions & CI/CD

**Path:** `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
**When to use:** Working on CI/CD workflows, GitHub Actions configuration, or automation.

---

## Frontend & Web

### ReactJS

**Path:** `.github/instructions/reactjs.instructions.md`
**When to use:** Working on React components or frontend code.

### TypeScript 5 & ES2022

**Path:** `.github/instructions/typescript-5-es2022.instructions.md`
**When to use:** Writing TypeScript or modern JavaScript.

### Markdown

**Path:** `.github/instructions/markdown.instructions.md`
**When to use:** Writing or editing Markdown documentation.

---

## Project & Process

### Task Implementation

**Path:** `.github/instructions/task-implementation.instructions.md`
**When to use:** General guidance on implementing features and tasks.

### Agents

**Path:** `.github/instructions/agents.instructions.md`
**When to use:** Working with AI agents or agentic patterns in the codebase.

### Prompt Engineering & Safety

**Path:** `.github/instructions/ai-prompt-engineering-safety-best-practices.instructions.md`
**When to use:** Creating prompts or AI-related functionality. Covers safety and best practices.

### Taming Copilot

**Path:** `.github/instructions/taming-copilot.instructions.md`
**When to use:** Context on working with GitHub Copilot in this project.

### Researcher Enhancements

**Path:** `.github/instructions/researcher-enhancements.instructions.md`
**When to use:** Research-related functionality or data gathering tasks.

---

## Meta

### Instructions Guidelines

**Path:** `.github/instructions/instructions.instructions.md`
**When to use:** Reference for how to structure and maintain instruction files.

### Prompt Files Guidelines

**Path:** `.github/instructions/prompt.instructions.md`
**When to use:** Creating or maintaining `.prompt.md` files for Copilot Chat.

---

## How I Use This Index

When you ask me to work on code:

1. I identify the relevant file types and domains
2. I check this index for applicable instruction files
3. I read the matching `.github/instructions/*.md` files
4. I apply those guidelines to my work

**Example:** If you ask me to add a new Python function:

- I'd read `python.instructions.md` (TDD, type hints, Ruff rules)
- I'd read `test-driven-development.instructions.md` (RED phase, xfail markers)
- If it's in `services/api/`, I'd also read `fastapi-transaction-patterns.instructions.md`

You don't need to tell me which files apply—I'll recognize the context and pull the relevant instructions.
