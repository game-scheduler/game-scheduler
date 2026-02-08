---
applyTo: '.copilot-tracking/changes/20260207-02-public-image-endpoints-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Secure Public Image Architecture with Deduplication

## Overview

Migrate image storage from RLS-protected game_sessions table to separate game_images table without RLS, enabling secure public endpoints that follow principle of least privilege and implement hash-based deduplication with reference counting.

## Objectives

- Eliminate BYPASSRLS credential requirement for public image endpoints
- Implement content-hash deduplication to optimize storage
- Maintain reference counting for automatic image cleanup
- Enable Discord embeds with public, rate-limited image endpoints
- Preserve image size limits (5MB) and MIME type validation
- Achieve comprehensive integration test coverage (30+ tests)

## Research Summary

### Project Files

- services/api/routes/games.py - Current authenticated endpoints requiring fix
- shared/models/game.py - Lines 107-110: Images in game_sessions with RLS
- shared/database.py - Lines 56-210: BYPASSRLS credentials (security concern)
- services/bot/formatters/game_message.py - Line 404, 407: URLs to update
- frontend/src/pages/GameDetails.tsx - Line 361, 380: Image sources to update

### External References

- #file:../research/20260207-02-public-image-endpoints-research.md - Complete security analysis and architecture design
- #fetch:https://discord.com/developers/docs/resources/channel#embed-object - Discord embed requirements (public URLs, no auth)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology (Red-Green-Refactor)
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Transaction management and service patterns

## Implementation Checklist

### [x] Phase 0: Database Migration and Models

- [x] Task 0.1: Create Alembic migration for schema changes
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 20-55)

- [x] Task 0.2: Create GameImage SQLAlchemy model
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 57-80)

- [x] Task 0.3: Update GameSession model to use FK relationships
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 82-100)

### [x] Phase 1: Image Storage Service with Deduplication (TDD)

- [x] Task 1.1: Create failing integration tests for image storage
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 102-150)

- [x] Task 1.2: Run tests to verify RED phase (tests fail)
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 152-160)

- [x] Task 1.3: Implement store_image() and release_image() functions
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 162-210)

- [x] Task 1.4: Run tests to verify GREEN phase (tests pass)
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 212-220)

- [x] Task 1.5: Refactor and add edge case tests
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 222-250)

### [x] Phase 2: Game Service Integration (TDD)

- [x] Task 2.1: Create failing tests for game-image lifecycle integration
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 252-310)

- [x] Task 2.2: Update game service methods to use image storage
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 312-360)

- [x] Task 2.3: Run tests to verify integration works correctly
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 362-375)

### [ ] Phase 3: Public Image Endpoint (TDD)

- [ ] Task 3.1: Create endpoint stub returning NotImplementedError
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 377-395)

- [ ] Task 3.2: Write failing integration tests for public endpoint
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 397-450)

- [ ] Task 3.3: Run tests to verify RED phase
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 452-460)

- [ ] Task 3.4: Implement public endpoint with proper headers
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 462-500)

- [ ] Task 3.5: Register router in main.py
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 502-515)

- [ ] Task 3.6: Run tests to verify GREEN phase
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 517-525)

- [ ] Task 3.7: Add rate limiting tests
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 527-560)

- [ ] Task 3.8: Implement rate limiting with slowapi
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 562-590)

- [ ] Task 3.9: Run full test suite to verify REFACTOR phase
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 592-605)

### [ ] Phase 4: Consumer Updates

- [ ] Task 4.1: Update bot message formatter URLs and tests
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 607-635)

- [ ] Task 4.2: Update frontend image display URLs and tests
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 637-665)

- [ ] Task 4.3: Update E2E tests for new image URLs
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 667-690)

### [ ] Phase 5: Cleanup and Documentation

- [ ] Task 5.1: Remove deprecated image endpoints from games.py
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 692-715)

- [ ] Task 5.2: Update API documentation and CHANGELOG
  - Details: .copilot-tracking/details/20260207-02-public-image-endpoints-details.md (Lines 717-745)

## Dependencies

- PostgreSQL with gen_random_uuid() support
- Alembic for database migrations
- SQLAlchemy async for database operations
- FastAPI with dependency injection
- slowapi for rate limiting (new dependency)
- pytest with async support
- httpx for integration testing

## Success Criteria

- All 30+ integration tests pass (storage, deduplication, reference counting, public endpoint, rate limiting)
- Public endpoint serves images without BYPASSRLS credentials
- Images deduplicated by SHA256 content hash
- Reference counting prevents orphans and premature deletion
- Rate limiting enforced (60/min, 100/5min per IP)
- Discord embeds work with new public URLs
- Bot and frontend updated with new image URLs
- Old authenticated endpoints removed
- Zero security regressions (principle of least privilege maintained)
- Migration completes successfully (schema-only, data loss acceptable)
