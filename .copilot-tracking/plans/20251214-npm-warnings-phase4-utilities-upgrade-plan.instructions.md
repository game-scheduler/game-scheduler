---
applyTo: ".copilot-tracking/changes/20251214-npm-warnings-phase4-utilities-upgrade-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: NPM Warnings Elimination Phase 4 - Routing & Utilities Upgrade

## Overview

Evaluate and implement React Router v7 and date-fns v4 upgrades to benefit from modern features and improvements.

## Objectives

- Evaluate React Router 6→7 migration effort
- Evaluate date-fns 2→4 migration effort
- Update packages if migration effort is reasonable
- Address breaking changes in routing and date utilities
- Maintain functionality and test coverage

## Research Summary

### Project Files

- `frontend/package.json` - Router and utility dependencies
- `frontend/src/**/*.tsx` - Components using React Router and date-fns
- Routing configuration files

### External References

- #file:../research/20251214-npm-warnings-elimination-research.md (Lines 132-146) - Router and utilities analysis
- #fetch:"https://reactrouter.com/en/main/upgrading/v6-v7" - React Router v7 upgrade guide
- #fetch:"https://date-fns.org/docs/Upgrade-Guide" - date-fns upgrade guide

### Standards References

- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript coding standards
- #file:../../.github/instructions/reactjs.instructions.md - React development guidelines

## Implementation Checklist

### [x] Phase 1: React Router Assessment

- [x] Task 1.1: Audit React Router usage
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 15-26)

- [x] Task 1.2: Review React Router v7 breaking changes
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 28-39)

- [x] Task 1.3: Decide on React Router upgrade
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 41-52)

### [x] Phase 2: date-fns Assessment

- [x] Task 2.1: Audit date-fns usage
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 56-67)

- [x] Task 2.2: Review date-fns v4 breaking changes
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 69-80)

- [x] Task 2.3: Decide on date-fns upgrade
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 82-93)
  - **Result**: Approved for Phase 3 implementation

### [x] Phase 3: Implementation (React Router)

- [x] Task 3.1: Update React Router package version
  - **Completed**: react-router@7.1.1 installed
  - Simple package swap, no peer dependency conflicts

- [x] Task 3.2: Migrate React Router code
  - **Completed**: Updated 18 source files with import changes
  - All imports changed from 'react-router-dom' → 'react-router'
  - All 51 tests passing

### [x] Phase 4: MUI X Date Pickers Assessment & Upgrade

- [x] Task 4.1: Assess MUI X Date Pickers v7→v8 upgrade
  - **Completed**: Simple upgrade, minimal breaking changes for our usage

- [x] Task 4.2: Upgrade decision
  - **Decision**: PROCEED - enables date-fns v4 upgrade

### [x] Phase 5: MUI X Date Pickers v8 + date-fns v4 Implementation

- [x] Task 5.1: Upgrade MUI X Date Pickers to v8.22.0
  - **Completed**: @mui/x-date-pickers@8.22.0 installed

- [x] Task 5.2: Run MUI codemod
  - **Completed**: 1 file modified (GameForm.tsx adapter import)

- [x] Task 5.3: Upgrade date-fns to v4.1.0
  - **Completed**: date-fns@4.1.0 installed, adapter updated

- [x] Task 5.4: Fix test suite for MUI v8 DOM structure
  - **Completed**: All 6 GameForm tests updated with helper function

- [x] Task 5.5: Run tests and verify functionality
  - **Completed**: All 51 tests passing (10 test suites)

## Dependencies

- Phases 1-3 completion recommended
- Node.js (installed in dev container)
- NPM (installed in dev container)

## Success Criteria

**If deferring upgrades:**
- Decision rationale documented
- Current versions remain functional
- No immediate action required

**If upgrading:**
- React Router v7 and/or date-fns v4 installed
- All routing and date logic migrated
- Zero TypeScript errors
- All tests passing
- No functional regressions
