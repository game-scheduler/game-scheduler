---
applyTo: ".copilot-tracking/changes/20251222-discord-client-token-unification-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Client Token Unification

## Overview

Unify Discord API client to accept both bot and OAuth tokens through a single consistent interface, eliminating artificial method duplication.

## Objectives

- Implement automatic token type detection based on Discord token format
- Consolidate duplicate bot/OAuth methods into unified operations
- Enable E2E tests to use admin bot tokens without special handling
- Reduce code complexity and improve maintainability
- Maintain backward compatibility during migration

## Research Summary

### Project Files

- [shared/discord/client.py](shared/discord/client.py) - Current implementation with artificial bot/OAuth split

### External References

- #file:../research/20251222-discord-client-token-unification-research.md - Token unification analysis
- #fetch:https://discord.com/developers/docs/resources/guild - Discord API accepts any valid token
- #fetch:https://discord.com/developers/docs/resources/channel - No authentication type restrictions
- #fetch:https://discord.com/developers/docs/resources/user - No authentication type restrictions

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment guidelines

## Implementation Checklist

### [x] Phase 1: Token Detection Infrastructure

- [x] Task 1.1: Implement `_get_auth_header()` method
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 11-30)

- [x] Task 1.2: Add token detection unit tests
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 32-49)
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 32-49)

### [x] Phase 2: Add Optional Token Parameters

- [x] Task 2.1: Add token parameter to `fetch_guild()`
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 51-67)

- [x] Task 2.2: Add token parameter to `fetch_channel()`
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 69-84)

- [x] Task 2.3: Add token parameter to `fetch_user()`
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 86-101)

### [x] Phase 3: Consolidate Guild Methods

- [x] Task 3.1: Create unified `get_guilds()` method
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 103-125)

- [x] Task 3.2: Update callers to use `get_guilds()`
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 127-145)

- [x] Task 3.3: Deprecate `get_bot_guilds()` and `get_user_guilds()`
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 147-164)

### [x] Phase 4: Integration Testing

- [x] Task 4.1: Verify bot token functionality
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 166-181)

- [x] Task 4.2: Verify OAuth token functionality
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 183-198)

### [x] Phase 5: Cleanup

- [x] Task 5.1: Remove deprecated methods
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 200-215)

- [x] Task 5.2: Update documentation
  - Details: [.copilot-tracking/details/20251222-discord-client-token-unification-details.md](../.copilot-tracking/details/20251222-discord-client-token-unification-details.md) (Lines 217-230)

## Dependencies

- Python 3.11+
- Existing Discord API client infrastructure
- Test fixtures for bot and OAuth tokens

## Success Criteria

- All existing tests pass with refactored client
- Production behavior unchanged (backward compatible)
- New E2E tests can use admin bot token without special handling
- Code complexity reduced (fewer methods, less duplication)
- API surface simplified and more consistent
