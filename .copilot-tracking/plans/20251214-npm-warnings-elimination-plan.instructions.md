---
applyTo: ".copilot-tracking/changes/20251214-npm-warnings-elimination-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: NPM Warnings Elimination Phase 1

## Overview

Eliminate NPM deprecation warnings and security vulnerabilities by upgrading Vite, ESLint, and supporting packages to current stable versions.

## Objectives

- Resolve esbuild CORS vulnerability (GHSA-67mh-4wv8-2f99) by upgrading Vite 5→6
- Eliminate ESLint end-of-life security risk by upgrading ESLint 8→9
- Remove 6 deprecated package warnings (inflight, glob, rimraf, @humanwhocodes/*)
- Update supporting packages to latest compatible versions
- Maintain full test coverage and CI/CD pipeline functionality

## Research Summary

### Project Files

- `frontend/package.json` - NPM dependencies and version constraints
- `frontend/.eslintrc.js` - ESLint 8 configuration (requires migration to flat config)
- `frontend/vite.config.ts` - Vite configuration
- `frontend/tsconfig.json` - TypeScript configuration

### External References

- #file:../research/20251214-npm-warnings-elimination-research.md - Comprehensive package analysis and migration strategy
- #fetch:"https://github.com/advisories/GHSA-67mh-4wv8-2f99" - esbuild CORS vulnerability details
- #fetch:"https://eslint.org/docs/latest/use/migrate-to-9.0.0" - ESLint 9 migration guide

### Standards References

- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript coding standards
- #file:../../.github/instructions/reactjs.instructions.md - React development guidelines
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding practices

## Implementation Checklist

### [x] Phase 1: Vite Upgrade

- [x] Task 1.1: Update Vite 5→6 in package.json
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 15-27)

- [x] Task 1.2: Install dependencies and verify esbuild version
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 29-40)

- [x] Task 1.3: Test Vite functionality
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 42-55)

### [x] Phase 2: ESLint Migration

- [x] Task 2.1: Install ESLint 9 and TypeScript ESLint v8
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 59-71)

- [x] Task 2.2: Convert .eslintrc.js to eslint.config.js (flat config)
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 73-97)

- [x] Task 2.3: Update ESLint plugins to ESLint 9 compatible versions
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 99-110)

- [x] Task 2.4: Test ESLint across codebase
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 112-122)

### [x] Phase 3: Supporting Packages

- [x] Task 3.1: Update minor version packages
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 126-138)

- [x] Task 3.2: Verify no new deprecation warnings
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 140-149)

### [ ] Phase 4: Testing & Validation

- [ ] Task 4.1: Run full frontend test suite
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 153-163)

- [ ] Task 4.2: Verify Docker builds
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 165-175)

- [ ] Task 4.3: Test CI/CD pipeline
  - Details: .copilot-tracking/details/20251214-npm-warnings-elimination-details.md (Lines 177-187)

## Dependencies

- Node.js (installed in dev container)
- NPM (installed in dev container)
- Docker (for build verification)
- GitHub Actions (for CI/CD verification)

## Success Criteria

- Zero npm deprecation warnings for ESLint-related packages
- Zero npm deprecation warnings for transitive dependencies (glob, rimraf, inflight)
- esbuild vulnerability GHSA-67mh-4wv8-2f99 resolved
- ESLint 8 end-of-life warning eliminated
- All frontend tests passing
- Docker frontend build successful
- CI/CD pipeline green
- No new warnings or errors introduced
