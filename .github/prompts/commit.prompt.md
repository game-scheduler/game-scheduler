---
agent: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Commit Changes with Validation

You are preparing to commit outstanding changes to the repository. Before committing, you must validate the code quality and correctness by running linters and tests.

## Step 1: Review Code Against Coding Standards

Before running automated checks, review the changed files to ensure they comply with project coding standards:

1. Ensure you're in the repository root and check which files have been modified:
   ```bash
   cd /home/mckee/src/github.com/game-scheduler
   git diff --name-only
   ```

2. For Python files (`.py`), verify compliance with:
   - `.github/instructions/python.instructions.md`

3. For React/TypeScript files (`.tsx`, `.ts`, `.jsx`, `.js`), verify compliance with:
   - `.github/instructions/reactjs.instructions.md`
   - `.github/instructions/typescript-5-es2022.instructions.md`

Review the changed code against the relevant instruction files and confirm that:
- Naming conventions are followed
- Code structure matches project patterns
- Best practices are applied
- Documentation standards are met

**Important**: All code must adhere to the guidelines in `.github/instructions/coding-best-practices.instructions.md`.

## Step 2: Verify Compilation

### Python Compilation Check
Verify all Python files compile without syntax errors:
```bash
cd /home/mckee/src/github.com/game-scheduler
uv run python -m compileall -q services shared tests
```

### Frontend Build Check
Verify the frontend builds successfully:
```bash
cd /home/mckee/src/github.com/game-scheduler/frontend
npm run build
```

**Important**: All code must adhere to the guidelines in `.github/instructions/coding-best-practices.instructions.md`.

## Step 3: Run Linters

### Python Linting
Run ruff to check and format Python code:
```bash
cd /home/mckee/src/github.com/game-scheduler
uv run ruff check --fix
uv run ruff format
```

### Python Type Checking
Run mypy for static type checking:
```bash
cd /home/mckee/src/github.com/game-scheduler
uv run mypy services shared
```

### Frontend Linting
Run ESLint and TypeScript type checking:
```bash
cd /home/mckee/src/github.com/game-scheduler/frontend
npm run lint:fix
npm run type-check
```

### Markdown Linting
Run Prettier to format markdown files:
```bash
cd /home/mckee/src/github.com/game-scheduler/frontend
npm run format:check
```
## Step 4: Run Tests

### Python Unit Tests
Run the Python unit tests (excluding e2e and integration tests):
```bash
cd /home/mckee/src/github.com/game-scheduler
uv run pytest --ignore tests/e2e --ignore tests/integration -v
```

### Frontend Tests
Run the frontend test suite:
```bash
cd /home/mckee/src/github.com/game-scheduler/frontend
npm run test:ci
```

## Step 5: Commit Changes

After all linters and tests pass successfully, return to the root directory and commit:

1. Return to repository root:
   ```bash
   cd /home/mckee/src/github.com/game-scheduler
   ```

2. Check the status of changed files:
   ```bash
   git status
   ```

3. Review the changes:
   ```bash
   git diff
   ```

4. Stage all changes:
   ```bash
   git add -A
   ```

4. Create a descriptive commit message that:
   - Starts with a concise summary (50 chars or less)
   - Uses imperative mood ("Add feature" not "Added feature")
   - Includes details about what changed and why if needed
   - References any related issues or tickets

5. Commit the changes:
   ```bash
   git commit -m "Your commit message here"
   ```

## Important Notes

- **All linters and tests must pass** before committing
- If any linter fails, fix the issues and re-run
- If any test fails, investigate and fix the issue before proceeding
- Do not commit if validation fails
- Review the git diff carefully to ensure no unintended changes are included

## Execution

Execute the steps above in order. Report the results of each step. If any step fails, stop and report the failure without proceeding to commit.
