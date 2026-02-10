---
applyTo: '.copilot-tracking/changes/20260210-01-channel-links-in-game-location-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Channel Links in Game Location Field

## Overview

Enable users to reference Discord channels in game location field using `#channel-name` format, with backend validation that converts mentions to clickable Discord channel links (`<#channel_id>`) in game announcements.

## Objectives

- Allow users to type `#channel-name` in location field
- Validate channel mentions against guild's Discord channels on game creation
- Provide disambiguation for ambiguous channel names with suggestions
- Convert validated mentions to Discord link format (`<#channel_id>`) for embed display
- Maintain backward compatibility with plain text locations

## Research Summary

### Project Files

- services/api/services/participant_resolver.py - ParticipantResolver pattern for mention validation
- services/bot/formatters/game_message.py - Already uses `<#channel_id>` format for voice channels
- shared/discord/client.py - Discord API client with `get_guild_channels()` method
- frontend/src/components/GameForm.tsx - Location field (TextField, 500 char max)

### External References

- #file:../research/20260210-01-channel-links-in-game-location-research.md - Complete research findings
- #fetch:https://discord.com/developers/docs/reference#message-formatting - Discord channel mention format
- #fetch:https://discord.com/developers/docs/resources/channel#get-channel - Channel API documentation

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Service layer patterns

## Implementation Checklist

### [x] Phase 1: Backend Channel Resolver Service

- [x] Task 1.1: Create ChannelResolver service stub
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 15-30)

- [x] Task 1.2: Write failing tests for ChannelResolver
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 32-55)

- [x] Task 1.3: Implement channel mention parsing and resolution
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 57-78)

- [x] Task 1.4: Update tests to verify actual behavior
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 80-92)

- [x] Task 1.5: Refactor and add edge case tests
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 102-120)

### [x] Phase 2: Game Service Integration

- [x] Task 2.1: Add channel resolution to GameService.create_game
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 122-145)

- [x] Task 2.2: Write integration tests for game creation with channel mentions
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 147-170)

- [x] Task 2.3: Add error handling for validation failures
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 172-190)

### [x] Phase 3: Frontend Error Display

- [x] Task 3.1: Update GameForm to display channel validation errors
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 165-190)

- [x] Task 3.2: Add helper text indicating channel mention support
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 192-211)
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 212-225)

### [x] Phase 4: End-to-End Testing

- [x] Task 4.1: Add E2E test for channel mention in Discord embed
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 227-250)

- [x] Task 4.2: Verify backward compatibility with plain text locations
  - Details: .copilot-tracking/details/20260210-01-channel-links-in-game-location-details.md (Lines 252-265)

## Dependencies

- Python 3.13+ with asyncio
- Discord API client (DiscordAPIClient)
- ParticipantResolver pattern (validation error format)
- Material-UI components (frontend)
- discord.py library (E2E tests)

## Success Criteria

- Users can type `#channel-name` in location field
- Backend validates channel exists in guild on game creation
- Returns structured error with suggestions if channel not found
- Returns disambiguation error if multiple matching channels
- Discord embed displays clickable `<#channel_id>` link
- Plain text locations continue to work without modification
- All unit, integration, and E2E tests pass
- No regressions in existing game creation flow
