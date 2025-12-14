<!-- markdownlint-disable-file -->

# Task Details: Pre-commit Hook Implementation with Intelligent Test Running

## Research Reference

**Source Research**: #file:../research/20251214-precommit-hooks-with-tests-research.md

## Phase 1: Pre-commit Configuration

### Task 1.1: Create `.pre-commit-config.yaml` with standard hooks

Create the base pre-commit configuration file with standard file cleanup hooks.

- **Files**:
  - `.pre-commit-config.yaml` - Main pre-commit configuration file
- **Success**:
  - Configuration file exists at repository root
  - Standard hooks configured: trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict, detect-private-key
  - Default language versions set: python3.11, node 20
  - Default stage set to pre-commit
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Complete configuration example
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 48-67) - Local hook configuration patterns
- **Dependencies**:
  - None (first task)

### Task 1.2: Configure Python linting and formatting hooks

Add local hooks for Python code quality: ruff linting, ruff formatting, and mypy type checking.

- **Files**:
  - `.pre-commit-config.yaml` - Add Python linting hooks section
- **Success**:
  - Ruff check hook configured with `--fix` flag
  - Ruff format hook configured
  - MyPy type check hook configured for `shared/` and `services/` directories
  - All hooks use `language: system` and `uv run` entry points
  - Hooks target `types: [python]` files
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Complete hook configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 19-26) - Current Python linting setup
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Configure frontend linting and formatting hooks

Add local hooks for frontend code quality: ESLint, Prettier, and TypeScript checking.

- **Files**:
  - `.pre-commit-config.yaml` - Add frontend linting hooks section
- **Success**:
  - ESLint hook configured with `npm run lint:fix`
  - Prettier hook configured with `npm run format`
  - TypeScript check hook configured with `npm run type-check`
  - All hooks operate in `frontend/` directory
  - Hooks target appropriate file patterns: `.ts`, `.tsx`, `.js`, `.jsx`, `.json`, `.css`, `.scss`, `.md`
  - All hooks use `pass_filenames: false` to handle command execution correctly
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Frontend hooks configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 28-31) - Current frontend setup
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Test Automation Hooks

### Task 2.1: Add automatic unit tests for modified Python files

Configure hook to automatically run pytest on new or modified Python files during commit.

- **Files**:
  - `.pre-commit-config.yaml` - Add pytest-changed hook
- **Success**:
  - Hook runs automatically on every commit (default stage)
  - Only tests new/modified Python files (uses `git diff --cached --name-only --diff-filter=ACM`)
  - Uses `uv run pytest` with appropriate flags: `--tb=short`, `-x`, `-v`
  - Hook has `always_run: true` and `verbose: true`
  - Gracefully handles case when no Python files are changed
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Automatic test hook configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 75-84) - Test modified files pattern
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Add automatic frontend tests for modified files

Configure hook to automatically run Vitest on new or modified frontend files during commit.

- **Files**:
  - `.pre-commit-config.yaml` - Add vitest-changed hook
- **Success**:
  - Hook runs automatically on every commit (default stage)
  - Only tests new/modified frontend files (uses `git diff --cached --name-only --diff-filter=ACM`)
  - Uses `npm run test -- --run` in frontend directory
  - Hook has `always_run: true` and `verbose: true`
  - Gracefully handles case when no frontend files are changed
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Frontend test hook configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 28-31) - Frontend test setup
- **Dependencies**:
  - Phase 1 completion

### Task 2.3: Add optional manual hooks for full test suite

Configure manual hooks for comprehensive test validation (run on demand).

- **Files**:
  - `.pre-commit-config.yaml` - Add pytest-all and vitest-all manual hooks
- **Success**:
  - pytest-all hook configured with `stages: [manual]`
  - pytest-all runs all unit tests: `tests/services/` and `tests/shared/`
  - vitest-all hook configured with `stages: [manual]`
  - vitest-all runs all frontend tests
  - Both hooks use `verbose: true` for detailed output
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 117-197) - Manual hooks configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 48-67) - stages: [manual] pattern
- **Dependencies**:
  - Phase 1 completion

## Phase 3: Installation and Documentation

### Task 3.1: Install pre-commit and configure git hooks

Install pre-commit framework and activate git hooks for the repository.

- **Files**:
  - Git hooks in `.git/hooks/` (created by pre-commit)
- **Success**:
  - pre-commit installed via `uv tool install pre-commit`
  - Git hooks installed via `pre-commit install`
  - Hooks are active and will run on next commit
  - Hook environments optionally pre-installed via `pre-commit install-hooks`
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 199-211) - Setup instructions
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 40-46) - Installation commands
- **Dependencies**:
  - Phase 2 completion (configuration must be complete)

### Task 3.2: Update project documentation with usage instructions

Document pre-commit hook usage, configuration, and troubleshooting for the team.

- **Files**:
  - `README.md` or `CONTRIBUTING.md` - Add pre-commit hooks section
- **Success**:
  - Documentation explains automatic vs manual hooks
  - Usage patterns documented: normal commit, manual hook execution, skipping hooks
  - Performance expectations explained (15-45 seconds typical)
  - Manual hook commands documented: `pre-commit run pytest-all --hook-stage manual`
  - Emergency skip documented: `git commit --no-verify` or `SKIP=hook-id git commit`
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 213-252) - Usage patterns
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 497-505) - Performance characteristics
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Test configuration and validate all hooks work

Run comprehensive tests to ensure all hooks function correctly.

- **Files**:
  - All project files (validation only)
- **Success**:
  - `pre-commit run --all-files` completes successfully
  - Each individual hook can be run: `pre-commit run <hook-id> --all-files`
  - Manual hooks work: `pre-commit run pytest-all --hook-stage manual`
  - Test commit shows hooks running automatically
  - Any pre-existing issues are fixed or documented
- **Research References**:
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 199-211) - Testing configuration
  - #file:../research/20251214-precommit-hooks-with-tests-research.md (Lines 529-545) - Team adoption strategy
- **Dependencies**:
  - Task 3.1 and 3.2 completion

## Dependencies

- pre-commit framework (installed via uv tools)
- Existing linters: ruff, mypy, eslint, prettier
- Existing test runners: pytest, vitest
- uv package manager
- npm package manager

## Success Criteria

- Pre-commit hooks run automatically on `git commit`
- Lint/format checks block commits with issues
- Unit tests for new/modified files run automatically before commit
- Tests run ONLY on new or modified files (efficient, focused)
- Automatic hooks complete in reasonable time (15-45 seconds typical)
- Manual hooks available for comprehensive testing
- Team can skip hooks with `--no-verify` in emergencies
- Full test suite still runs in CI/CD for comprehensive validation
- Documentation explains hook usage and customization options
