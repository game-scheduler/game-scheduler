<!-- markdownlint-disable-file -->

# Task Research Notes: Git Wrapper Script for Quality Check Override Enforcement

## Research Executed

### File Analysis

- `.github/instructions/quality-check-overrides.instructions.md`
  - Documents prohibited bypass patterns: `--no-verify`, `-n`, `SKIP=`
  - Requires explicit user approval for quality check overrides
  - AI agents currently ignoring these instructions
- `.devcontainer/Dockerfile`
  - Uses Python 3.13-slim base with git installed
  - Creates vscode user with sudo access
  - Supports `.bashrc_devcontainer` for custom shell configuration
- `scripts/*.sh`
  - Project uses consistent shebang patterns: `#!/bin/bash` or `#!/usr/bin/env bash`
  - Follows MIT license header convention (21 lines)
  - Standard error handling with `set -e`

### Code Search Results

- `.devcontainer/devcontainer.json`
  - postCreateCommand installs pre-commit hooks
  - postStartCommand appends `.bashrc_devcontainer` to `.bashrc`
  - Terminal uses bash login shell by default
- `scripts/` directory structure
  - Contains 11 utility scripts for testing, coverage, migration
  - No existing git wrapper or interception mechanisms

### External Research

- Git wrapper scripts are commonly used for:
  - Enforcing organizational policies
  - Preventing accidental destructive commands
  - Adding custom validations before git operations
  - Logging and auditing git usage
- PATH precedence in Unix:
  - First match in PATH wins
  - `~/bin` or `/usr/local/bin` typically precede system paths
  - Dev container can prepend custom PATH locations

### Project Conventions

- Standards referenced: MIT License, bash scripting conventions, pre-commit integration
- Instructions followed: quality-check-overrides.instructions.md policy enforcement

## Key Discoveries

### Project Structure

The project uses VS Code dev containers with:

- Debian-based Python 3.13 environment
- Pre-commit hooks installed automatically during container creation
- Custom bash configuration support via `.bashrc_devcontainer`
- User-writable `/usr/local/bin` for system-wide tools

### Implementation Patterns

Current quality enforcement relies on:

1. Pre-commit hooks for automated validation
2. Copilot instructions for AI agent guidance (insufficient)
3. No technical controls to prevent `--no-verify` or `SKIP=` usage

### Complete Example: Git Wrapper Script

```bash
#!/bin/bash
# Git wrapper to enforce quality check policy
# Prevents --no-verify and SKIP= without explicit approval

# Path to real git binary (found during installation)
REAL_GIT="/usr/bin/git"

# Flag to track if we need approval
NEEDS_APPROVAL=false
ERROR_MESSAGE=""

# Parse command line for prohibited patterns
args=("$@")
new_args=()

# Check for environment variable SKIP=
if [[ -n "$SKIP" ]]; then
    NEEDS_APPROVAL=true
    ERROR_MESSAGE+="ERROR: SKIP environment variable detected.\n"
    ERROR_MESSAGE+="Pre-commit hook bypass requires explicit user approval.\n"
    ERROR_MESSAGE+="Use APPROVED_SKIP instead: APPROVED_SKIP=<hooks> git commit\n\n"
fi

# Check for APPROVED_SKIP and convert to SKIP
if [[ -n "$APPROVED_SKIP" ]]; then
    export SKIP="$APPROVED_SKIP"
    unset APPROVED_SKIP
fi

# Scan arguments for problematic flags
for i in "${!args[@]}"; do
    arg="${args[$i]}"

    case "$arg" in
        --no-verify|-n)
            NEEDS_APPROVAL=true
            ERROR_MESSAGE+="ERROR: $arg flag detected.\n"
            ERROR_MESSAGE+="Pre-commit hook bypass requires explicit user approval.\n"
            ERROR_MESSAGE+="Use --approved-no-verify instead: git commit --approved-no-verify\n\n"
            ;;
        --approved-no-verify)
            # Replace with actual --no-verify for git
            new_args+=("--no-verify")
            ;;
        *)
            new_args+=("$arg")
            ;;
    esac
done

# If approval needed, show error and exit
if [[ "$NEEDS_APPROVAL" == "true" ]]; then
    echo -e "$ERROR_MESSAGE" >&2
    echo "See .github/instructions/quality-check-overrides.instructions.md for policy details." >&2
    exit 1
fi

# Execute real git with processed arguments
exec "$REAL_GIT" "${new_args[@]}"
```

### API and Schema Documentation

Git command parsing considerations:

- Arguments can appear anywhere in command line
- Environment variables like `SKIP=` are set before command
- Multiple bypass methods can be combined
- Short (`-n`) and long (`--no-verify`) forms both exist

### Configuration Examples

Dev container PATH configuration in `.devcontainer/Dockerfile`:

```dockerfile
# Add git wrapper to PATH before system git
RUN mkdir -p /usr/local/bin/wrappers && \
    mv /usr/bin/git /usr/bin/git.real && \
    ln -s /usr/local/bin/wrappers/git /usr/bin/git
```

Alternative using PATH prepending in `.bashrc_devcontainer`:

```bash
# Prepend wrapper directory to PATH
export PATH="/workspaces/game-scheduler/scripts/wrappers:$PATH"
```

### Technical Requirements

1. Wrapper must be executable before system git in PATH
2. Must handle all git commands and pass-through safely
3. Must detect both flag-based and environment-based bypasses
4. Must provide clear error messages referencing policy
5. Must allow approved alternatives (`--approved-no-verify`, `APPROVED_SKIP`)
6. Must preserve all git functionality for normal operations

## Recommended Approach

**Create a git wrapper script in the project that intercepts quality check bypasses:**

1. **Location**: `scripts/wrappers/git` (new directory)
   - Keeps wrapper code in version control
   - Clearly separated from other scripts
   - Easy to maintain and update

2. **Implementation Strategy**:
   - Detect prohibited patterns: `--no-verify`, `-n`, `SKIP=` environment variable
   - Convert approved alternatives: `--approved-no-verify` → `--no-verify`, `APPROVED_SKIP` → `SKIP`
   - Display clear error messages referencing policy document
   - Pass through all other git commands unchanged

3. **Integration Method**: Prepend to PATH in dev container
   - Add to `.bashrc_devcontainer` for automatic activation
   - Non-invasive: doesn't modify system git installation
   - Easy to disable for troubleshooting
   - Works across all terminal sessions in dev container

4. **Error Message Design**:
   - Explain what was detected
   - Reference policy document
   - Show approved alternative syntax
   - Clear, actionable guidance

## Implementation Guidance

- **Objectives**: Enforce quality-check-overrides.instructions.md policy through technical controls
- **Key Tasks**:
  1. Create `scripts/wrappers/` directory structure
  2. Write git wrapper script with prohibited pattern detection
  3. Add MIT license header matching project conventions
  4. Make wrapper executable (`chmod +x`)
  5. Update `.devcontainer/Dockerfile` to prepend wrapper to PATH
  6. Test wrapper with various git commands and bypass attempts
  7. Document wrapper behavior in developer documentation
- **Dependencies**: Existing pre-commit configuration, bash shell environment
- **Success Criteria**:
  - `git commit --no-verify` shows error message
  - `SKIP=hook git commit` shows error message
  - `git commit --approved-no-verify` works (passes to git as `--no-verify`)
  - `APPROVED_SKIP=hook git commit` works (sets SKIP for pre-commit)
  - Normal git commands work without interference
  - Error messages are clear and reference policy document
