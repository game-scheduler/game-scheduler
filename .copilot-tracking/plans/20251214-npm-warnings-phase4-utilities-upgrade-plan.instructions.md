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

### [ ] Phase 2: date-fns Assessment

- [ ] Task 2.1: Audit date-fns usage
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 56-67)

- [ ] Task 2.2: Review date-fns v4 breaking changes
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 69-80)

- [ ] Task 2.3: Decide on date-fns upgrade
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 82-93)

### [x] Phase 3: Implementation (React Router)

- [x] Task 3.1: Update React Router package version
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 110-121)

- [x] Task 3.2: Migrate React Router code
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 123-135)

- [ ] Task 3.3: Migrate date-fns code (SKIPPED - date-fns assessment not completed)
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 137-149)

- [ ] Task 3.4: Run tests and verify functionality
  - Details: .copilot-tracking/details/20251214-npm-warnings-phase4-utilities-upgrade-details.md (Lines 136-147)

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
