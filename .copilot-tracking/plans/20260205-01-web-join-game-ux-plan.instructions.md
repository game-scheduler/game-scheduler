---
applyTo: ".copilot-tracking/changes/20260205-01-web-join-game-ux-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Web Join Game UX with Real-Time Cross-Platform Sync

## Overview

Enable real-time synchronization of game join/leave actions across web and Discord interfaces using SSE, allowing users to see updates on web pages when they interact with Discord buttons without manual refresh.

## Objectives

- Implement SSE endpoint for real-time game update notifications
- Create RabbitMQ bridge service to push events to web clients
- Add server-side guild authorization filtering to prevent information disclosure
- Integrate EventSource in frontend for automatic UI updates
- Add join/leave buttons to GameCard component for parity with Discord
- Enable hybrid routing keys with guild_id for future scalability

## Research Summary

### Project Files

- services/api/routes/games.py - REST endpoints for join/leave actions
- services/bot/handlers/join_game.py - Discord bot writes directly to database
- services/bot/handlers/leave_game.py - Discord bot writes directly to database
- services/bot/events/publisher.py - Bot publishes game.updated events to RabbitMQ
- services/api/services/games.py - API publishes game.updated events to RabbitMQ
- shared/messaging/consumer.py - EventConsumer pattern for RabbitMQ integration
- shared/discord/client.py - get_user_guilds() with 5-min Valkey cache
- frontend/src/components/GameCard.tsx - Currently only shows "View Details" button
- frontend/src/pages/BrowseGames.tsx - Renders GameCard components
- frontend/src/pages/GameDetails.tsx - Has join/leave buttons with authorization logic

### External References

- #file:../research/20260205-01-web-join-game-ux-research.md - Complete research with architecture analysis, performance data, and implementation patterns
- FastAPI StreamingResponse for SSE - Native support, no external libraries needed
- EventSource browser API - Automatic reconnection, widely supported
- RabbitMQ topic exchanges - Support multiple queues with same routing key (fanout pattern)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - ReactJS development standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting style

## Implementation Checklist

### [ ] Phase 1: Backend SSE Infrastructure

- [ ] Task 1.1: Create SSE bridge service with RabbitMQ consumer
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 15-34)

- [ ] Task 1.2: Create SSE endpoint with FastAPI StreamingResponse
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 36-52)

- [ ] Task 1.3: Integrate SSE bridge into API service lifespan
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 54-68)

### [ ] Phase 2: RabbitMQ Integration and Routing Keys

- [ ] Task 2.1: Update routing keys to include guild_id (hybrid approach)
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 70-88)

- [ ] Task 2.2: Add web_sse_events queue to RabbitMQ initialization
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 90-100)

### [ ] Phase 3: Frontend Real-Time Updates

- [ ] Task 3.1: Create useGameUpdates React hook with EventSource
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 102-119)

- [ ] Task 3.2: Add join/leave buttons to GameCard component
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 121-138)

- [ ] Task 3.3: Integrate SSE updates in BrowseGames and MyGames pages
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 140-156)

### [ ] Phase 4: Testing and Validation

- [ ] Task 4.1: Create unit tests for SSE endpoint and bridge
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 158-172)

- [ ] Task 4.2: Verify cross-platform synchronization (Discord → Web)
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 174-186)

- [ ] Task 4.3: Validate guild authorization filtering
  - Details: .copilot-tracking/details/20260205-01-web-join-game-ux-details.md (Lines 188-200)

## Dependencies

- FastAPI (existing) - SSE endpoint implementation
- RabbitMQ (existing) - Event distribution infrastructure
- Valkey (existing) - Cached guild membership checks
- EventConsumer pattern (existing) - RabbitMQ integration
- React EventSource API (browser built-in) - SSE client

## Success Criteria

- User joins via Discord button → web page updates within 2 seconds
- User joins via web button → Discord message updates within 2 seconds
- Join/Leave buttons on GameCard provide immediate optimistic feedback
- Only authorized users receive events for their guilds (no information disclosure)
- Users kicked from guild stop receiving events within 5 minutes
- SSE connections handle disconnect/reconnect gracefully
- System handles 100+ concurrent SSE connections without performance degradation
