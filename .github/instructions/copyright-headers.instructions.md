---
description: 'Copyright header management - do not add manually'
applyTo: '**/*.py,**/*.ts,**/*.tsx,**/*.sh'
---

# Copyright Header Management

## Critical Rule: DO NOT Add Copyright Headers Manually

**NEVER manually add copyright headers when creating new files.**

## How Copyright Headers Work

This project uses the `autocopyright` pre-commit hook to automatically add MIT license headers to all source files:

- Python files (`.py`)
- TypeScript files (`.ts`, `.tsx`)
- Shell scripts (`.sh`)

The hook uses the template at `templates/mit-template.jinja2` which includes `{{ now.year }}` to automatically insert the current year.

## What to Do When Creating New Files

1. **Create the file WITHOUT any copyright header**
2. **Write your code**
3. **Commit the file** - the pre-commit hook will automatically add the correct copyright header with the current year

## Why Not Add Headers Manually?

- Manual headers may have incorrect years (copying old headers results in year ranges like `2025-2026` when it should just be the current year)
- The template ensures consistency across all files
- The tool correctly handles the year based on when the file is committed
- Less manual work and fewer errors

## If You See Incorrect Copyright Years

The `autocopyright` tool automatically updates copyright years based on file modification. Year ranges (e.g., `2025-2026`) indicate files modified across multiple years, which is correct behavior for those files.

New files should only have the current year.
