<!-- markdownlint-disable-file -->

# Release Changes: Pre-commit Hook Implementation with Intelligent Test Running

**Related Plan**: 20251214-precommit-hooks-with-tests-plan.instructions.md
**Implementation Date**: 2024-12-14

## Summary

Implementation of pre-commit hooks with automatic linting, formatting, type checking, and intelligent test execution for modified files.

## Changes

### Added

- `.pre-commit-config.yaml` - Base pre-commit configuration with standard file cleanup hooks

### Modified

- `.pre-commit-config.yaml` - Added Python linting and formatting hooks (ruff check, ruff format, mypy)
- `.pre-commit-config.yaml` - Added frontend linting and formatting hooks (eslint, prettier, typescript check)
- `.pre-commit-config.yaml` - Added automatic pytest hook for new/modified Python files
- `.pre-commit-config.yaml` - Added automatic vitest hook for new/modified frontend files
- `.pre-commit-config.yaml` - Added manual pytest-all and vitest-all hooks for comprehensive test validation
- `.pre-commit-config.yaml` - Updated Python version from 3.11 to 3.13 to match system installation
- `.git/hooks/pre-commit` - Installed pre-commit git hook to activate automatic execution
- `README.md` - Added pre-commit hooks section with setup, usage, and troubleshooting documentation
- `.devcontainer/devcontainer.json` - Added Node.js 20 feature to support frontend pre-commit hooks
- `.devcontainer/devcontainer.json` - Updated postCreateCommand to install frontend dependencies, pre-commit hooks, and verify tools
- `.devcontainer/Dockerfile` - Updated to install dev dependencies including pre-commit framework
- `pyproject.toml` - Added pre-commit>=3.5.0 to dev dependency group for automatic installation
- `.pre-commit-config.yaml` - Added manual ci-cd-workflow hook to run GitHub Actions locally using act
- `README.md` - Updated documentation to include ci-cd-workflow manual hook and simplified command examples

### Removed

## Release Summary

**Total Files Affected**: 3

### Files Created (1)

- `.pre-commit-config.yaml` - Pre-commit framework configuration with automatic linting, formatting, type checking, and intelligent test execution for modified files

### Files Modified (2)

- `.pre-commit-config.yaml` - Comprehensive hook configuration including Python (ruff, mypy) and frontend (eslint, prettier, typescript) quality checks, plus automatic unit tests for new/modified files
- `README.md` - Documentation for pre-commit hook usage, setup instructions, performance expectations, and emergency skip procedures

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: pre-commit framework (installed via uv tools)
- **Updated Dependencies**: None
- **Infrastructure Changes**: Git hooks installed in `.git/hooks/pre-commit` for automatic execution
- **Configuration Updates**: Python version updated from 3.11 to 3.13 in pre-commit config

### Deployment Notes

**Setup Required:**
1. Team members need to run `uv tool run pre-commit install` to activate hooks locally
2. Hooks run automatically on every commit
3. Performance expectation: 15-45 seconds per commit (tests only modified files)
4. Emergency skip available with `--no-verify` flag

**Key Features:**
- Automatic code quality checks prevent committing files with lint/format errors
- Intelligent test execution runs only tests for new/modified files
- Manual hooks available for comprehensive test validation (pytest-all, vitest-all, ci-cd-workflow)
- CI/CD workflow can be run locally using `act` before pushing
- Maintains CI/CD as authoritative test suite

**Manual Hooks Available:**
- `pytest-all` - Run all Python unit tests
- `vitest-all` - Run all frontend unit tests
- `ci-cd-workflow` - Run full CI/CD pipeline locally (requires Docker, takes ~1-2 minutes)
