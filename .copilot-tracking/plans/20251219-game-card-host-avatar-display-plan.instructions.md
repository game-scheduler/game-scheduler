---
applyTo: ".copilot-tracking/changes/20251219-game-card-host-avatar-display-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Card Host Avatar Display Enhancement

## Overview

Add host Discord avatar display to both web frontend GameCard component and Discord bot game embeds.

## Objectives

- Display host Discord avatars in web frontend game cards
- Display host Discord avatars in Discord bot game announcement embeds
- Share avatar URL infrastructure between web and Discord implementations
- Maintain graceful fallback when avatars unavailable

## Research Summary

### Project Files

- services/api/services/display_names.py - Display name resolver service
- shared/schemas/participant.py - Participant response schemas
- frontend/src/components/GameCard.tsx - Web game card component
- services/bot/formatters/game_message.py - Discord embed formatter

### External References

- #file:../research/20251218-game-card-host-avatar-display-research.md - Comprehensive research covering both implementations
- Discord API documentation for guild member objects and avatar URLs
- Discord CDN image formatting for avatar URLs

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript standards
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices

## Implementation Checklist

### [x] Phase 1: Backend Avatar Data Collection

- [x] Task 1.1: Update DisplayNameResolver to extract avatar hashes
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 15-35)

- [x] Task 1.2: Add avatar_url to ParticipantResponse schema
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 37-52)

- [x] Task 1.3: Update game routes to return avatar URLs
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 54-69)

- [x] Task 1.4: Update caching to include avatar data
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 71-86)

### [x] Phase 2A: Web Frontend Implementation

- [x] Task 2A.1: Add avatar_url to Participant TypeScript interface
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 88-102)

- [x] Task 2A.2: Update GameCard component to display host avatar
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 104-125)

- [x] Task 2A.3: Add frontend tests for avatar display
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 127-142)

### [ ] Phase 2B: Discord Bot Embed Implementation

- [ ] Task 2B.1: Update create_game_embed to accept avatar parameters
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 144-165)

- [ ] Task 2B.2: Use embed.set_author() for host display
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 167-185)

- [ ] Task 2B.3: Update event handlers to pass avatar data
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 187-205)

- [ ] Task 2B.4: Add Discord bot tests for embed author field
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 207-222)

### [ ] Phase 3: Integration and End-to-End Testing

- [ ] Task 3.1: Add integration tests for avatar data flow
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 224-245)

- [ ] Task 3.2: Test web frontend with real Discord avatars
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 247-262)

- [ ] Task 3.3: Test Discord bot embeds in live environment
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 264-279)

- [ ] Task 3.4: Verify avatar caching and performance
  - Details: .copilot-tracking/details/20251219-game-card-host-avatar-display-details.md (Lines 281-296)

## Dependencies

- Discord API access for guild member data
- MUI Avatar component (already available)
- discord.py library for embed author field

## Success Criteria

- Backend returns avatar URLs in all game API responses
- Web GameCard displays host avatar at top with fallback to initials
- Discord embeds show host avatar using author field
- All unit tests pass for backend, frontend, and Discord bot
- All integration tests pass for full avatar data flow
- End-to-end tests verify both web and Discord implementations
- Avatar URLs properly cached with 5-minute TTL
- Graceful handling of missing/null avatars
- Performance metrics meet requirements (cache hit rate, response time)
