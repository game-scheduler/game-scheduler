---
applyTo: ".copilot-tracking/changes/20260204-mit-license-migration-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: MIT license migration for Game Scheduler

## Overview

Replace AGPL licensing with MIT across license files, headers, metadata, and documentation while updating 2025 headers to 2025-2026 and keeping 2026 headers unchanged.

## Objectives

- Replace AGPL license text and metadata with MIT across the repository.
- Update source headers, documentation, and About page content to MIT with correct year ranges.

## Research Summary

### Project Files

- COPYING.txt - Current AGPL license text and target MIT replacement.
- templates/agpl-template.jinja2 - Autocopyright header template used for source files.
- scripts/add-copyright - Autocopyright invocation for Python and frontend sources.
- pyproject.toml - Project license metadata currently set to AGPL-3.0-or-later.
- frontend/src/pages/About.tsx - About page license text and link.
- frontend/src/pages/__tests__/About.test.tsx - Tests asserting AGPL text and GNU link.
- README.md - License section referencing COPYING.txt.

### External References

- #file:../research/20260204-mit-license-migration-research.md - Consolidated findings and MIT license text.
- #fetch:https://spdx.org/licenses/MIT.html - SPDX canonical MIT license text.
- #fetch:https://opensource.org/license/mit/ - OSI MIT license text.

### Standards References

- #file:../../.github/instructions/coding-best-practices.instructions.md - Code consistency and change discipline.
- #file:../../.github/instructions/markdown.instructions.md - Documentation updates.
- #file:../../.github/instructions/python.instructions.md - Python header updates.
- #file:../../.github/instructions/reactjs.instructions.md - Frontend header updates.
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards.
- #file:../../.github/instructions/taming-copilot.instructions.md - Minimal, targeted changes.

## Implementation Checklist

### [ ] Phase 1: Update license artifacts and tooling

- [ ] Task 1.1: Replace AGPL license text with MIT in COPYING.txt

  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 11-23)

- [ ] Task 1.2: Update autocopyright template and script for MIT headers

  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 25-38)

- [ ] Task 1.3: Update project metadata license to MIT
  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 40-51)

### [ ] Phase 2: Update source file headers

- [ ] Task 2.1: Apply MIT headers and adjust copyright years
  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 55-72)

### [ ] Phase 3: Update documentation and UI references

- [ ] Task 3.1: Update README License section
  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 76-87)

- [ ] Task 3.2: Update About page and tests for MIT license
  - Details: .copilot-tracking/details/20260204-mit-license-migration-details.md (Lines 89-102)

## Dependencies

- autocopyright tooling via uv
- templates directory and scripts/add-copyright

## Success Criteria

- MIT license text replaces AGPL in COPYING.txt and metadata.
- Source headers updated to MIT with correct year ranges.
- Documentation and About page display MIT license and tests pass.
