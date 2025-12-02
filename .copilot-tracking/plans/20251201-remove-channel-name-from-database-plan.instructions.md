---
applyTo: ".copilot-tracking/changes/20251201-remove-channel-name-from-database-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove channel_name from Database

## Overview

Remove `channel_name` column from `channel_configurations` table and rely on dynamic fetching from Discord API with existing Redis caching infrastructure.

## Objectives

- Remove database storage of channel names (eliminates staleness issues)
- Leverage existing `discord_client.fetch_channel()` method with Redis caching
- Maintain backward compatibility in API responses and frontend
- Ensure all tests pass with updated schema

## Research Summary

### Project Files

- alembic/versions/001_initial_schema.py - Defines channel_name column (Line 80)
- shared/models/channel.py - Channel model with channel_name field (Line 46)
- shared/schemas/channel.py - Pydantic schemas for API (Lines 29, 52, 68)
- services/bot/commands/config_channel.py - Stores channel_name when creating config (Lines 90, 189)
- services/api/routes/channels.py - Returns channel_name from database (Lines 89, 129, 176)
- services/api/services/config.py - Service layer that stores channel_name (Lines 254, 282)
- tests/integration/test_notification_daemon.py - SQL INSERT with channel_name (Lines 110-116)
- tests/e2e/test_game_notification_api_flow.py - SQL INSERT with channel_name (Lines 137-144)

### External References

- #file:../research/20251201-remove-channel-name-from-database-research.md - Comprehensive implementation research
- #file:../../services/api/auth/discord_client.py - Discord API client with fetch_channel() method (Lines 319-368)
- #file:../../shared/cache/ttl.py - Cache TTL configuration (DISCORD_CHANNEL = 300 seconds)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript standards

## Implementation Checklist

### [ ] Phase 1: Database Migration

- [ ] Task 1.1: Create Alembic migration to drop channel_name column
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 10-32)

### [ ] Phase 2: Update Models and Schemas

- [ ] Task 2.1: Remove channel_name field from SQLAlchemy model
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 34-47)

- [ ] Task 2.2: Update Pydantic schemas
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 49-63)

### [ ] Phase 3: Update API Routes

- [ ] Task 3.1: Update get_channel endpoint to fetch channel name dynamically
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 65-88)

- [ ] Task 3.2: Update create_channel_config endpoint
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 90-111)

- [ ] Task 3.3: Update update_channel_config endpoint
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 113-132)

### [ ] Phase 4: Update Configuration Service

- [ ] Task 4.1: Remove channel_name from create_channel_config service method
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 134-152)

- [ ] Task 4.2: Remove channel_name from update_channel_config service method
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 154-167)

### [ ] Phase 5: Update Bot Commands

- [ ] Task 5.1: Remove channel_name logic from /config-channel command
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 169-189)

- [ ] Task 5.2: Update _get_or_create_channel_config helper
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 191-211)

### [ ] Phase 6: Update Test Fixtures

- [ ] Task 6.1: Remove channel_name from integration test SQL INSERT
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 213-231)

- [ ] Task 6.2: Remove channel_name from e2e test SQL INSERT
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 233-251)

### [ ] Phase 7: Validation and Testing

- [ ] Task 7.1: Run database migration
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 253-265)

- [ ] Task 7.2: Run all tests and verify passing
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 267-284)

- [ ] Task 7.3: Manual testing - verify channel names display correctly
  - Details: .copilot-tracking/details/20251201-remove-channel-name-from-database-details.md (Lines 286-301)

## Dependencies

- Alembic for database migrations
- SQLAlchemy ORM
- Redis caching (already configured with 5-minute TTL)
- Discord API (via discord_client.fetch_channel() with caching)
- Bot token with channel read permissions

## Success Criteria

- Database schema no longer contains channel_name column
- SQLAlchemy model does not include channel_name field
- Bot commands do not store channel_name
- API responses still include channel_name (fetched from Discord with caching)
- Frontend displays channel names correctly
- All unit, integration, and e2e tests pass
- Channel name changes in Discord reflect within 5 minutes (cache TTL)
