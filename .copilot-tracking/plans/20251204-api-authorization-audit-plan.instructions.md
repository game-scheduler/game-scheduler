---
applyTo: '.copilot-tracking/changes/20251204-api-authorization-audit-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: REST API Authorization Audit and Security Fixes

## Overview

Fix critical authorization vulnerabilities in REST API endpoints to prevent unauthorized access and information disclosure.

## Objectives

- Enforce proper authorization on all API endpoints
- Prevent unauthorized access to templates, games, and guild resources
- Prevent information disclosure about guilds user isn't member of
- Implement appropriate HTTP status codes (404 vs 403) to prevent resource enumeration
- Centralize duplicated authorization logic

## Research Summary

### Project Files
- services/api/routes/templates.py - Template endpoints with missing authorization checks
- services/api/routes/games.py - Game endpoints with missing authorization and filtering
- services/api/dependencies/permissions.py - Existing authorization dependencies
- services/api/auth/roles.py - Role verification service for permission checks

### External References
- #file:../research/20251204-api-authorization-audit-research.md - Comprehensive security audit findings

### Standards References
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Security best practices

## Implementation Checklist

### [x] Phase 1: Create Authorization Helper Functions

- [x] Task 1.1: Create require_bot_manager dependency
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 15-35)

- [x] Task 1.2: Create verify_guild_membership helper function
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 37-56)

- [x] Task 1.3: Create verify_template_access helper function
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 58-78)

- [x] Task 1.4: Create verify_game_access helper function
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 80-100)

- [x] Task 1.5: Add unit tests for authorization helpers
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 102-120)

### [x] Phase 2: Fix Template Authorization Using Helpers

- [x] Task 2.1: Add guild membership check to GET /templates/{template_id}
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 124-140)

- [x] Task 2.2: Refactor template management routes to use require_bot_manager
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 142-160)

- [x] Task 2.3: Add integration tests for template authorization
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 162-176)

### [x] Phase 3: Fix Game Authorization Using Helpers

- [x] Task 3.1: Fix game list filtering with helper functions
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 180-200)

- [x] Task 3.2: Fix game detail authorization with helper functions
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 202-220)

- [x] Task 3.3: Fix game join authorization with helper functions
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 222-242)

- [x] Task 3.4: Add integration tests for game authorization
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 244-262)

### [x] Phase 4: Migrate All Remaining Endpoints to Use Helpers

- [x] Task 4.1: Audit and migrate guild endpoints
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 266-284)

- [x] Task 4.2: Audit and migrate channel endpoints
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 286-302)

- [x] Task 4.3: Audit and migrate game management endpoints
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 304-322)

- [x] Task 4.4: Audit and migrate export endpoints
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 324-340)

- [x] Task 4.5: Verify no bespoke auth code remains in route handlers
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 342-358)

### [ ] Phase 5: Information Leak Audit

- [ ] Task 5.1: Audit all endpoints for proper 404 vs 403 usage
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 362-378)

- [ ] Task 5.2: Add comprehensive negative authorization tests
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 380-396)

### [ ] Phase 6: Documentation and Prevention

- [ ] Task 6.1: Document authorization patterns
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 400-420)

- [ ] Task 6.2: Create authorization checklist for new endpoints
  - Details: .copilot-tracking/details/20251204-api-authorization-audit-details.md (Lines 422-434)

## Dependencies

- FastAPI dependency injection framework
- RoleVerificationService for Discord role checks
- Discord OAuth2 API for guild membership verification
- SQLAlchemy for database queries
- pytest for integration tests

## Success Criteria

- All 4 critical authorization vulnerabilities fixed
- Template detail endpoint requires guild membership (returns 404 if not member)
- Game list filtered by guild membership and player roles
- Game detail endpoint requires guild membership (returns 404 if not member)
- Game join endpoint verifies player roles from template
- Bot manager authorization centralized in dependency
- All template routes use require_bot_manager dependency
- **All guild endpoints use verify_guild_membership helper**
- **All channel endpoints use verify_guild_membership helper**
- **All game management endpoints use helper functions**
- **All export endpoints use helper functions**
- **Zero bespoke authorization code remains in route handlers**
- **All authorization logic centralized in helpers/dependencies**
- All endpoints use appropriate HTTP status codes (404 vs 403)
- Comprehensive authorization tests pass (positive and negative cases)
- No information disclosure vulnerabilities remain
- Authorization patterns documented for future development
- Documentation prohibits inline authorization code in new endpoints
