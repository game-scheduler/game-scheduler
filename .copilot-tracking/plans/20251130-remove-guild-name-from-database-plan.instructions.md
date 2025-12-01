---
applyTo: ".copilot-tracking/changes/20251130-remove-guild-name-from-database-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove guild_name from Database

## Overview

Remove `guild_name` column from `guild_configurations` table and rely on dynamic fetching from Discord API with existing Redis caching infrastructure.

## Objectives

- Remove database storage of guild names (eliminates staleness issues)
- Verify API routes already fetch guild names dynamically with caching
- Maintain backward compatibility in API responses and frontend
- Ensure all tests pass with updated schema

## Research Summary

### Project Files

- alembic/versions/001_initial_schema.py - Defines guild_name column (Line 58)
- shared/models/guild.py - Guild model with guild_name field (Line 45)
- services/bot/commands/config_guild.py - Stores guild_name when creating config (Lines 64-75, 82-83)
- tests/integration/test_notification_daemon.py - SQL INSERT with guild_name (Lines 95-101)
- tests/e2e/test_game_notification_api_flow.py - SQL INSERT with guild_name (Lines 118-126)

### External References

- #file:../research/20251130-remove-guild-name-from-database-research.md - Comprehensive implementation research
- #file:../../services/api/auth/discord_client.py - Discord API client with Redis caching (Lines 370-420)
- #file:../../shared/cache/ttl.py - Cache TTL configuration (DISCORD_GUILD = 600 seconds)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript standards

## Implementation Checklist

### [ ] Phase 1: Database Migration

- [ ] Task 1.1: Create Alembic migration to drop guild_name column

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 10-32)

### [ ] Phase 2: Update Models and Schemas

- [ ] Task 2.1: Remove guild_name field from SQLAlchemy model

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 34-47)

- [ ] Task 2.2: Verify Pydantic schemas are correct
  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 49-62)

### [ ] Phase 3: Update Bot Commands

- [ ] Task 3.1: Remove guild_name logic from /config-guild command

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 64-88)

- [ ] Task 3.2: Update _get_or_create_guild_config helper
  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 90-109)

### [ ] Phase 4: Update Test Fixtures

- [ ] Task 4.1: Remove guild_name from integration test SQL INSERT

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 111-128)

- [ ] Task 4.2: Remove guild_name from e2e test SQL INSERT
  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 130-148)

### [ ] Phase 5: Validation and Testing

- [ ] Task 5.1: Run database migration

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 150-162)

- [ ] Task 5.2: Run all tests and verify passing

  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 164-181)

- [ ] Task 5.3: Manual testing - verify guild names display correctly
  - Details: .copilot-tracking/details/20251130-remove-guild-name-from-database-details.md (Lines 183-198)

## Dependencies

- Alembic for database migrations
- SQLAlchemy ORM
- Redis caching (already configured)
- Discord API (via oauth2.get_user_guilds with caching)

## Success Criteria

- Database schema no longer contains guild_name column
- SQLAlchemy model does not include guild_name field
- Bot commands do not store guild_name
- API responses still include guild_name (fetched from Discord)
- Frontend displays guild names correctly
- All unit, integration, and e2e tests pass
- Guild name changes in Discord reflect immediately (no staleness)
