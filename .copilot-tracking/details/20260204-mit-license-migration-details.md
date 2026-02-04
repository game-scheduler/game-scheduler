<!-- markdownlint-disable-file -->

# Task Details: MIT license migration for Game Scheduler

## Research Reference

**Source Research**: #file:../research/20260204-mit-license-migration-research.md

## Phase 1: Update license artifacts and tooling

### Task 1.1: Replace AGPL license text with MIT in COPYING.txt

Update the primary license file to the MIT license text and ensure the copyright year aligns with the project requirement.

- **Files**:
  - COPYING.txt - Replace AGPL-3.0 text with MIT license text and adjust year display.
- **Success**:
  - COPYING.txt contains the full MIT license text and no AGPL references.
  - Copyright year reflects 2025-2026 where applicable.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 9-10, 53-75, 91-98) - Current license file and MIT text guidance.
- **Dependencies**:
  - None

### Task 1.2: Update autocopyright template and script for MIT headers

Create a new MIT header template based on autocopyright's MIT.md.jinja2 (simplified: copyright without email, no project preamble) and update the script to reference it.

- **Files**:
  - templates/mit-template.jinja2 - Create new file based on https://raw.githubusercontent.com/Argmaster/autocopyright/main/templates/MIT.md.jinja2, adapted for pyproject.toml structure (use pyproject.project.authors[0].name instead of pyproject.tool.poetry.authors[0]).
  - scripts/add-copyright - Update template path from agpl-template.jinja2 to mit-template.jinja2.
  - templates/agpl-template.jinja2 - Remove obsolete AGPL template file.
- **Success**:
  - MIT template exists at templates/mit-template.jinja2 with copyright line (no email) and full MIT license text.
  - Script references templates/mit-template.jinja2 and no AGPL references remain.
  - Old AGPL template file has been removed.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 11-14, 40-43, 91-98, 103-129) - Current template, autocopyright MIT.md.jinja2 reference, and required changes.
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Update project metadata license to MIT

Update the project license metadata in pyproject.toml to MIT.

- **Files**:
  - pyproject.toml - Change `license` to MIT.
- **Success**:
  - pyproject.toml uses MIT as the project license.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 15-16, 80-84, 91-98) - Current metadata and requirement to update.
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Update source file headers

### Task 2.1: Apply MIT headers and adjust copyright years

Update Python and frontend TS/TSX headers to MIT using autocopyright, ensuring 2025 becomes 2025-2026 and 2026 stays unchanged.

- **Files**:
  - alembic/**/*.py - Update headers.
  - services/**/*.py - Update headers.
  - shared/**/*.py - Update headers.
  - tests/**/*.py - Update headers.
  - frontend/src/**/*.ts - Update headers.
  - frontend/src/**/*.tsx - Update headers.
- **Success**:
  - No AGPL header text remains in source files.
  - 2025 headers updated to 2025-2026, 2026 headers unchanged.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 22-30, 91-98, 103-112) - Current header spread and year handling requirements.
- **Dependencies**:
  - Task 1.2 completion

## Phase 3: Update documentation and UI references

### Task 3.1: Update README License section

Update README License section to reflect MIT and updated copyright year range.

- **Files**:
  - README.md - Replace AGPL references with MIT and adjust year range.
- **Success**:
  - README License section describes MIT license and no AGPL references remain.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 7-8, 91-98, 103-112) - README reference and requirement.
- **Dependencies**:
  - Task 1.1 completion

### Task 3.2: Update About page and tests for MIT license

Replace AGPL license text and GNU URL on the About page and update tests to assert MIT license text and link.

- **Files**:
  - frontend/src/pages/About.tsx - Replace license copy and link with MIT.
  - frontend/src/pages/__tests__/About.test.tsx - Update assertions for MIT text and link.
- **Success**:
  - About page displays MIT license text and link.
  - Tests assert MIT license content and correct license link.
- **Research References**:
  - #file:../research/20260204-mit-license-migration-research.md (Lines 17-20, 47-51, 91-98, 103-112) - About page and test references.
- **Dependencies**:
  - Task 1.1 completion

## Dependencies

- autocopyright (pyproject dependency)
- templates directory and scripts/add-copyright

## Success Criteria

- License text updated to MIT in COPYING.txt and metadata.
- All source headers reflect MIT with correct year handling.
- Documentation and About UI content reference MIT and pass tests.
