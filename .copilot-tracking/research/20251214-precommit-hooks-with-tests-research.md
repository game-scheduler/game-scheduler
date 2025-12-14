<!-- markdownlint-disable-file -->
# Task Research Notes: Pre-commit Hook Implementation with Intelligent Test Running

## Research Executed

### Official Documentation Analysis
- #fetch:"https://pre-commit.com/"
  - Pre-commit is the industry-standard framework for managing git hooks
  - Supports multi-language projects with automatic environment management
  - Provides `repo: local` for project-specific hooks
  - Supports `stages: [manual]` for optional hooks
  - Has `pass_filenames` control for passing files to hooks
  - Provides `always_run` for hooks that don't operate on files

### GitHub Repository Code Analysis
- #githubRepo:"pre-commit/pre-commit local hooks pass_filenames stages manual"
  - `pass_filenames: false` prevents passing filenames to hook
  - `stages: [manual]` creates hooks that only run with explicit invocation
  - Local hooks support all languages with `additional_dependencies`
  - Can use `language: system` or `language: python` for local hooks
  - Hook configuration in `.pre-commit-config.yaml` at repository root

### Project Structure Analysis
- **Python Project**: Uses `uv` for dependency management
  - Tests in `/app/tests/` with subdirectories: `e2e/`, `integration/`, `services/`, `shared/`
  - Test files follow pattern: `test_*.py` or `*_test.py`
  - Uses pytest with async support (`pytest-asyncio`)
  - Current linters: `ruff` (lint + format), `mypy` (type checking)

- **Frontend Project**: TypeScript/React in `/app/frontend/`
  - Uses npm for package management
  - Has ESLint, Prettier, TypeScript configured
  - Test scripts: `test`, `test:ui`, `test:coverage`

### CI/CD Pipeline Configuration
- Located at `.github/workflows/ci-cd.yml`
- Current checks:
  - Python: `ruff check`, `ruff format --check`, `mypy`
  - Frontend: `npm run lint`, `npm run test:ci`, `npm run build`
  - Unit and integration tests run separately

### Test Discovery Pattern Research
- Python tests: 50+ test files discovered in `tests/` subdirectories
- Test naming conventions: `test_*.py` files with `def test_*()` or `class Test*` patterns
- Tests are organized by component (services, shared, integration, e2e)

## Key Discoveries

### Pre-commit Framework Capabilities

**Installation and Setup**
```bash
# Using uv (project's Python package manager)
uv tool install pre-commit

# Install git hooks
pre-commit install

# Optional: Install all hook environments upfront
pre-commit install-hooks
```

**Hook Types Supported**
- `pre-commit`: Runs before commit (default)
- `pre-push`: Runs before push
- `commit-msg`: Validates commit messages
- `manual`: Only runs when explicitly invoked
- Several others (post-checkout, post-merge, etc.)

### Local Hook Configuration Pattern

**Basic Structure**
```yaml
repos:
  - repo: local
    hooks:
      - id: hook-id
        name: Human Readable Name
        entry: command to run
        language: python|system|node|etc
        pass_filenames: true|false
        stages: [pre-commit, manual]
        files: regex pattern
        types: [python, javascript, etc]
```

**Key Hook Properties**
- `pass_filenames`: Controls whether staged filenames are passed to hook
- `stages`: Defines when hook runs (or `manual` for on-demand)
- `files`: Regex pattern to filter files
- `types`: File type filters (more robust than regex)
- `always_run`: Run even if no files match
- `verbose`: Always show output even on success

### Intelligent Test Running Approaches

**Option 1: Test Modified Files Only (Fast)**
```yaml
- repo: local
  hooks:
    - id: pytest-changed
      name: Run tests for changed files
      entry: bash -c 'files=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$"); if [ -n "$files" ]; then uv run pytest $files --tb=short -x; fi'
      language: system
      pass_filenames: false
      always_run: true
      stages: [manual]
```

**Option 2: Test Files Related to Changes (Comprehensive)**
```yaml
- repo: local
  hooks:
    - id: pytest-related
      name: Run tests related to changes
      entry: bash -c 'changed=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" | grep -v "^tests/"); if [ -n "$changed" ]; then uv run pytest tests/ -k "$(echo $changed | sed "s|/|_|g; s|\.py||g")" --tb=short -x; fi'
      language: system
      pass_filenames: false
      always_run: true
      stages: [manual]
```

**Option 3: Smart Test Discovery Based on Imports (Advanced)**
- Requires custom Python script to analyze imports
- Maps source files to test files that import them
- Most accurate but requires development effort

### Complete Examples from Pre-commit Repository

**Python Hook with Additional Dependencies**
```yaml
- repo: local
  hooks:
    - id: local-pytest
      name: pytest on modified files
      entry: pytest
      language: python
      pass_filenames: true
      types: [python]
      stages: [manual]
      additional_dependencies: [pytest>=7.4.0, pytest-asyncio>=0.21.0]
```

**System Hook (No Virtual Environment)**
```yaml
- repo: local
  hooks:
    - id: no-todo
      name: No TODO comments
      entry: sh -c "! grep -iI todo $@" --
      language: system
      types: [text]
```

**Python Script Hook**
```yaml
- repo: local
  hooks:
    - id: custom-check
      name: Custom validation
      entry: python scripts/custom_check.py
      language: system
      pass_filenames: true
      types: [python]
```

## Recommended Approach

**Selected Configuration: Choice A + Automatic Tests for New/Modified Files**
- **Automatic on commit**: Linting, formatting, type checking, AND unit tests for new/modified files
- **Smart testing**: Only tests files you're actually committing (fast)
- **Optional full suite**: Can run all tests manually when needed

### Configuration File: `.pre-commit-config.yaml`

**Complete pre-commit configuration for this project:**

```yaml
# Pre-commit hook configuration
# See https://pre-commit.com for more information

default_language_version:
  python: python3.11
  node: "20"

default_stages: [pre-commit]

repos:
  # Standard pre-commit hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      # File cleanup
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--unsafe]  # Allow custom YAML tags
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: detect-private-key

  # Python linting and formatting
  - repo: local
    hooks:
      # Ruff linter (fast Python linter)
      - id: ruff-check
        name: ruff lint
        entry: uv run ruff check --fix
        language: system
        types: [python]
        require_serial: true

      # Ruff formatter (fast Python formatter)
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
        require_serial: true

      # MyPy type checking
      - id: mypy
        name: mypy type check
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
        args: [shared/, services/]

  # Frontend linting and formatting
  - repo: local
    hooks:
      # ESLint
      - id: eslint
        name: ESLint
        entry: bash -c 'cd frontend && npm run lint:fix'
        language: system
        files: ^frontend/.*\.(ts|tsx|js|jsx)$
        pass_filenames: false

      # Prettier
      - id: prettier
        name: Prettier format
        entry: bash -c 'cd frontend && npm run format'
        language: system
        files: ^frontend/.*\.(ts|tsx|js|jsx|json|css|scss|md)$
        pass_filenames: false

      # TypeScript type check
      - id: typescript
        name: TypeScript check
        entry: bash -c 'cd frontend && npm run type-check'
        language: system
        files: ^frontend/.*\.(ts|tsx)$
        pass_filenames: false

  # Automatic testing for new/modified files
  - repo: local
    hooks:
      # Unit tests for new/modified Python files (RUNS ON EVERY COMMIT)
      - id: pytest-changed
        name: pytest on new/modified files
        entry: bash -c 'files=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$"); if [ -n "$files" ]; then uv run pytest $files --tb=short -x -v; else echo "No Python files to test"; fi'
        language: system
        pass_filenames: false
        always_run: true
        verbose: true

      # Frontend tests for new/modified files (RUNS ON EVERY COMMIT)
      - id: vitest-changed
        name: Frontend tests on changed files
        entry: bash -c 'files=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^frontend/.*\.(ts|tsx|js|jsx)$"); if [ -n "$files" ]; then cd frontend && npm run test -- --run; else echo "No frontend files to test"; fi'
        language: system
        pass_filenames: false
        always_run: true
        verbose: true

  # Optional/Manual hooks - run with: pre-commit run <hook-id> --hook-stage manual
  - repo: local
    hooks:
      # All unit tests (for comprehensive validation)
      - id: pytest-all
        name: pytest all unit tests
        entry: uv run pytest tests/services/ tests/shared/ --tb=short
        language: system
        pass_filenames: false
        stages: [manual]
        verbose: true

      # All frontend tests
      - id: vitest-all
        name: All frontend unit tests
        entry: bash -c 'cd frontend && npm run test'
        language: system
        pass_filenames: false
        stages: [manual]
        verbose: true
```

### Setup Instructions

**1. Install pre-commit**
```bash
# Using uv (project's package manager)
uv tool install pre-commit
```

**2. Create configuration file**
```bash
# Create .pre-commit-config.yaml in repository root
# (Content shown above)
```

**3. Install git hooks**
```bash
# Install hooks for default stages (pre-commit)
pre-commit install

# Optional: Install hook environments now
pre-commit install-hooks
```

**4. Test the configuration**
```bash
# Run all hooks on all files (good first test)
pre-commit run --all-files

# Run specific hook
pre-commit run ruff-check --all-files

# Run manual hooks
pre-commit run pytest-changed --hook-stage manual --all-files
```

### Usage Patterns

**Automatic Execution (Default)**
```bash
# These run automatically on EVERY git commit:
# - trailing-whitespace
# - end-of-file-fixer
# - check-yaml
# - check-added-large-files
# - ruff-check (Python linting with auto-fix)
# - ruff-format (Python formatting)
# - mypy (Python type checking)
# - eslint (frontend linting, for frontend files only)
# - prettier (frontend formatting, for frontend files only)
# - typescript (TypeScript checking, for frontend files only)
# - pytest-changed (unit tests for NEW/MODIFIED Python files)
# - vitest-changed (frontend tests for NEW/MODIFIED frontend files)

git add modified_file.py
git commit -m "Your commit message"
# Pre-commit runs ALL checks + tests for modified files automatically
```

**Optional Manual Test Execution**
```bash
# Run ALL unit tests (comprehensive validation, not just changed files)
pre-commit run pytest-all --hook-stage manual

# Run ALL frontend tests (comprehensive validation, not just changed files)
pre-commit run vitest-all --hook-stage manual
```

**Skipping Hooks (Emergency Use Only)**
```bash
# Skip ALL hooks for this commit (not recommended, but available)
git commit -m "WIP: urgent hotfix" --no-verify

# Skip specific hooks (e.g., if a test is flaky)
SKIP=pytest-changed git commit -m "Skip tests temporarily"

# Skip just the tests but keep linting
SKIP=pytest-changed,vitest-changed git commit -m "Skip tests only"
```

**Note:** Full test suite still runs in CI/CD, so skipped tests will be caught there.

### Advanced: Smart Test Selection Script

**Option for intelligent test discovery (`scripts/run_related_tests.py`):**

```python
#!/usr/bin/env python3
"""
Run tests related to changed files based on import analysis.
Usage: python scripts/run_related_tests.py file1.py file2.py
"""
import sys
import subprocess
from pathlib import Path

def find_test_files_for(source_file: Path) -> list[Path]:
    """Find test files that might test the given source file."""
    test_candidates = []

    # Direct test file (e.g., services/api/routes.py -> tests/services/api/test_routes.py)
    if source_file.parts[0] in ('services', 'shared'):
        test_path = Path('tests') / source_file.parent / f'test_{source_file.name}'
        if test_path.exists():
            test_candidates.append(test_path)

    # Search for imports
    try:
        import_name = str(source_file).replace('/', '.').replace('.py', '')
        result = subprocess.run(
            ['grep', '-r', '-l', f'from {import_name}', 'tests/'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            test_candidates.extend(Path(f) for f in result.stdout.strip().split('\n'))
    except Exception:
        pass

    return list(set(test_candidates))

def main():
    changed_files = [Path(f) for f in sys.argv[1:] if f.endswith('.py') and not f.startswith('tests/')]

    if not changed_files:
        print("No source files changed, skipping tests")
        return 0

    test_files = []
    for source_file in changed_files:
        test_files.extend(find_test_files_for(source_file))

    if not test_files:
        print(f"No test files found for: {[str(f) for f in changed_files]}")
        return 0

    print(f"Running tests: {[str(f) for f in test_files]}")
    result = subprocess.run(['uv', 'run', 'pytest', *map(str, test_files), '--tb=short', '-v'])
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
```

**Updated hook configuration to use smart script:**
```yaml
- repo: local
  hooks:
    - id: pytest-smart
      name: pytest smart test selection
      entry: python scripts/run_related_tests.py
      language: system
      pass_filenames: true
      types: [python]
      stages: [manual]
      verbose: true
```

## Implementation Guidance

### Objectives
1. **Prevent committing files with lint/format errors** (automatic, fast)
2. **Provide optional unit tests for new/modified files** (manual execution)
3. **Maintain fast pre-commit performance** (< 10 seconds for automatic hooks)
### Objectives
1. **Prevent committing files with lint/format errors** (automatic, fast)
2. **Ensure new/modified files pass unit tests** (automatic, before commit)
3. **Maintain reasonable pre-commit performance** (tests only modified files)
4. **Keep full test suite in CI/CD** (comprehensive validation with all combinations)it`
3. Run `pre-commit install` to set up git hooks
4. Test configuration with `pre-commit run --all-files`
5. Document usage for team in README or CONTRIBUTING guide
6. Optional: Create smart test selection script

### Dependencies
- `pre-commit` framework (installed via uv tools)
- Existing linters: ruff, mypy, eslint, prettier
- Existing test runners: pytest, vitest

### Success Criteria
- ✅ Pre-commit hooks run automatically on `git commit`
- ✅ Lint/format checks block commits with issues
- ✅ Unit tests for new/modified files run automatically before commit
- ✅ Tests run ONLY on new or modified files (efficient, focused)
- ✅ Automatic hooks complete in reasonable time (10-30 seconds depending on files changed)
- ✅ Team can skip hooks with `--no-verify` in emergencies
- ✅ Full test suite still runs in CI/CD for comprehensive validation
- ✅ Documentation explains hook usage and customization

### Performance Characteristics
**Expected Timings (Typical Commit with 1-3 Modified Files):**
- Trailing whitespace/file checks: < 1s
- Ruff check + format: 2-4s
- MyPy type check: 3-5s
- ESLint (if frontend files): 2-3s
- **Pytest for modified files**: 5-20s (depends on number of test files)
- **Vitest for modified files**: 3-10s (depends on number of test files)
- **Total: 15-45 seconds** (varies based on files changed)

**Optional Full Test Suite (Manual):**
- `pytest-all`: 1-3 minutes (all unit tests)
- `vitest-all`: 10-30s (all frontend tests)

**Why Tests Are Automatic:**
- Tests run ONLY on files you're committing (not the entire suite)
- Catches bugs before they reach the codebase
- Faster feedback loop than waiting for CI
- If a specific test is slow, you can temporarily skip with `--no-verify`
- Full comprehensive test suite still runs in CI/CDual`
- If too slow, can be trimmed back or adjusted per developer preference

### Alternative Considered: Pre-push Hooks

If pre-commit becomes too slow, tests can be moved to pre-push:

```yaml
# In .pre-commit-config.yaml
default_install_hook_types: [pre-commit, pre-push]

# Then configure test hooks with:
stages: [pre-push]  # Instead of manual
```

Install with:
```bash
pre-commit install --hook-type pre-push
```

## Integration with CI/CD

Pre-commit hooks are a **first line of defense**, not a replacement for CI:

**Pre-commit (Local)**
- Fast linting/formatting
- Optional quick tests
- Immediate feedback

**CI/CD (GitHub Actions)**
- Full test suite (unit + integration + e2e)
- Multi-version testing (Python 3.11, 3.12)
- Coverage reporting
- Build validation
- Deployment

**Recommended CI Check:**
```yaml
# Add to .github/workflows/ci-cd.yml
- name: Check pre-commit hooks pass
  run: pre-commit run --all-files
```

This ensures CI validates the same checks developers run locally.

## Team Adoption Strategy

**Phase 1: Introduction (Week 1)**
- Install pre-commit configuration
- Run `pre-commit run --all-files` to fix existing issues
- Update team documentation
- Announce in team meeting

**Phase 2: Voluntary Use (Weeks 2-3)**
- Team members install with `pre-commit install`
- Collect feedback on performance and issues
- Adjust configuration if needed

**Phase 3: Required Use (Week 4+)**
- Add CI check: `pre-commit run --all-files`
- Update contribution guidelines
- Set up troubleshooting guide

**Common Issues and Solutions:**
1. **Hook too slow**: Move to `manual` stage or optimize
2. **False positives**: Adjust file patterns or add exclusions
3. **Installation issues**: Document platform-specific steps
4. **Legacy code**: Add `# noqa` comments or exclude files

## References and Resources

- Official Documentation: https://pre-commit.com
- Supported Hooks: https://pre-commit.com/hooks.html
- Pre-commit GitHub: https://github.com/pre-commit/pre-commit
- This project's linting config: `/app/pyproject.toml`
- This project's CI config: `/app/.github/workflows/ci-cd.yml`
