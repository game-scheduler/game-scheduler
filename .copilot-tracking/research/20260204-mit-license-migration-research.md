<!-- markdownlint-disable-file -->
# Task Research Notes: MIT license migration for Game Scheduler

## Research Executed

### File Analysis
- README.md
  - Current License section references COPYING.txt and lists Copyright 2025 Bret McKee.
- COPYING.txt
  - Contains full GNU Affero General Public License v3 text.
- templates/agpl-template.jinja2
  - Autocopyright template renders AGPL header text for source files.
- scripts/add-copyright
  - Uses autocopyright with templates/agpl-template.jinja2 for Python and frontend TS/TSX files.
- pyproject.toml
  - Project license metadata set to AGPL-3.0-or-later.
- frontend/src/pages/About.tsx
  - About page renders AGPL text and GNU license URL; includes 2025 copyright.
- frontend/src/pages/__tests__/About.test.tsx
  - Tests assert AGPL-specific text and GNU license link.

### Code Search Results
- GNU Affero General Public License
  - Found across source headers in Python and frontend TS/TSX files (AGPL boilerplate).
- AGPL-3.0-or-later
  - Present in project metadata (pyproject.toml).
- Copyright 2026
  - Present in 2026-only files (e.g., new RLS-related alembic migrations, tests, and data access).
- About
  - About page and tests reference AGPL text and GNU license URL.

### External Research
- #fetch:https://spdx.org/licenses/MIT.html
  - SPDX canonical MIT license text and notes that there is no standard header.
- #fetch:https://opensource.org/license/mit/
  - OSI MIT license text for redistribution and warranty disclaimer.
- #fetch:https://raw.githubusercontent.com/Argmaster/autocopyright/main/templates/MIT.md.jinja2
  - Official autocopyright MIT template with simplified header format.

### Project Conventions
- Standards referenced: .github/instructions/coding-best-practices.instructions.md, .github/instructions/markdown.instructions.md
- Instructions followed: task-researcher mode rules, .github/instructions/researcher-enhancements.instructions.md

## Key Discoveries

### Project Structure
The project currently embeds AGPL text in source file headers (Python `#` and frontend `//`), a full AGPL license in COPYING.txt, and documentation references to the AGPL license in README and the frontend About page. The autocopyright workflow relies on templates/agpl-template.jinja2 and is invoked by scripts/add-copyright for Python and frontend sources.

### Implementation Patterns
- Source file headers follow a multi-line “This file is part of Game_Scheduler” AGPL notice.
- Frontend About page includes a dedicated License card with AGPL text and link to https://www.gnu.org/licenses/.
- Tests verify the About page contains the AGPL-specific text and GNU link.
- Project metadata license is declared in pyproject.toml as AGPL-3.0-or-later.- MIT template will use simplified header: copyright line without email, followed by full MIT license text, no project-specific preamble.
### Complete Examples
```text
MIT License

Copyright (c) <year> <copyright holders>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### API and Schema Documentation
No API or schema changes are required; updates are limited to licensing text, headers, and documentation.

### Configuration Examples
```toml
[project]
license = "MIT"
```

```bash
uv run autocopyright -s "#" -d alembic -d services -d shared -d tests -g "*.py" -l "./templates/mit-template.jinja2"
uv run autocopyright -s "//" -d frontend/src -g "*.ts" -g "*.tsx" -l "./templates/mit-template.jinja2"
```

```jinja
Copyright {{ now.year }} {{ pyproject.project.authors[0].name }}

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### Technical Requirements
- Replace AGPL license text with MIT license text in COPYING.txt or equivalent license file.
- Update source file headers to MIT using simplified template (copyright line without email, no project-specific preamble), with copyright year handling:
  - 2025 → 2025-2026
  - 2026 stays 2026
- Create MIT autocopyright template based on https://raw.githubusercontent.com/Argmaster/autocopyright/main/templates/MIT.md.jinja2, adapted for pyproject.toml structure.
- Update documentation and UI messages that refer to AGPL (README, About page, and tests).
- Update project metadata license to MIT (pyproject.toml).

## Recommended Approach
Adopt a single MIT licensing path by replacing the AGPL license file with MIT, updating the autocopyright template and script to emit MIT headers, and updating all documentation and UI references (README and About page, including tests). Update copyright years in headers to 2025-2026 when the original shows 2025, while leaving 2026-only files unchanged. This keeps the licensing consistent across metadata, file headers, and user-facing documentation.

## Implementation Guidance
- **Objectives**: Replace AGPL with MIT across license file, headers, metadata, and documentation while adjusting years per requirement.
- **Key Tasks**:
  - Replace COPYING.txt contents with MIT license text.
  - Create MIT header template at templates/mit-template.jinja2 based on autocopyright's MIT.md.jinja2, adapted for pyproject.toml structure (no email, no project preamble).
  - Update scripts/add-copyright to reference MIT template.
  - Update pyproject.toml license metadata to MIT.
  - Update README License section to reflect MIT and updated copyright year range.
  - Update frontend About page copy and tests to assert MIT text and proper license link.
  - Run header updates across Python and frontend sources using the MIT autocopyright template, respecting year rules.
- **Dependencies**: autocopyright (already in pyproject.toml), templates directory, scripts/add-copyright.
- **Success Criteria**:
  - No remaining AGPL references in headers or documentation.
  - About page and tests reference MIT license text and link.
  - Project metadata declares MIT.
  - 2025 headers updated to 2025-2026, 2026 headers unchanged.
