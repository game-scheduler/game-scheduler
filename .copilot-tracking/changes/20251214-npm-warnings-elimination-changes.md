<!-- markdownlint-disable-file -->

# Release Changes: NPM Warnings Elimination Phase 1

**Related Plan**: 20251214-npm-warnings-elimination-plan.instructions.md
**Implementation Date**: 2025-12-14

## Summary

Phase 1 implementation to eliminate NPM deprecation warnings and security vulnerabilities by upgrading Vite 5→6, ESLint 8→9, and supporting packages to current stable versions.

## Changes

### Added

- frontend/eslint.config.js - New ESLint 9 flat config migrated from .eslintrc.cjs

### Modified

- frontend/package.json - Updated Vite from ^5.0.8 to ^6.0.0 to fix esbuild CORS vulnerability
- frontend/package-lock.json - Updated dependencies with npm install, esbuild now 0.25.12
- frontend/dist/ - Build output verified with Vite 6, all tests pass (51/51)
- frontend/package.json - Updated ESLint to ^9.0.0, @typescript-eslint/parser to ^8.0.0, @typescript-eslint/eslint-plugin to ^8.0.0
- frontend/package-lock.json - Installed ESLint 9.39.2 and TypeScript ESLint 8.49.0
- frontend/package.json - Added @eslint/js, typescript-eslint, and globals packages for flat config
- frontend/package.json - Updated lint scripts to remove deprecated --ext flag
- frontend/package-lock.json - Installed flat config dependencies
- frontend/package.json - Updated eslint-plugin-react-hooks from ^4.6.0 to ^7.0.0 for ESLint 9 compatibility
- frontend/package-lock.json - Installed eslint-plugin-react-hooks 7.0.1 with no peer dependency warnings
- frontend/eslint.config.js - Added caughtErrorsIgnorePattern to handle unused catch errors
- frontend/src/api/client.ts - Prefixed unused catch error with underscore (_refreshError)
- frontend/package.json - Updated prettier from ^3.6.2 to ^3.7.4, vitest from ^4.0.10 to ^4.0.15, jsdom from ^27.2.0 to ^27.3.0, eslint-plugin-react-refresh from ^0.4.5 to ^0.4.25
- frontend/package-lock.json - Installed updated supporting packages (prettier 3.7.4, vitest 4.0.15, jsdom 27.3.0, eslint-plugin-react-refresh 0.4.25)
- Verification completed: npm ci shows zero targeted deprecation warnings (inflight, @humanwhocodes/*, rimraf, glob, eslint@8 all eliminated)

### Removed

- frontend/.eslintignore - Removed deprecated file, using ignores in eslint.config.js instead
- frontend/.eslintrc.cjs - Removed old ESLint config after migration to flat config

## Release Summary

_To be completed after all phases are marked complete [x]_
