<!-- markdownlint-disable-file -->

# Task Details: Web Join Game UX with Real-Time Cross-Platform Sync

## Research Reference

**Source Research**: #file:../research/20260205-01-web-join-game-ux-research.md

## Phase 1: Backend SSE Infrastructure

### Task 1.1: Create SSE bridge service with RabbitMQ consumer

Create a new SSE bridge service that consumes game update events from RabbitMQ and broadcasts them to authorized SSE connections using server-side guild filtering.

- **Files**:
  - services/api/services/sse_bridge.py (NEW) - SSE bridge with EventConsumer (~150 lines)
- **Success**:
  - Bridge service connects to RabbitMQ web_sse_events queue
  - Consumes game.updated.* events using wildcard binding
  - Maintains dictionary of active SSE connections with session tokens
  - Filters events by checking cached user guild memberships
  - Broadcasts only to authorized connections
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 108-145) - SSE Bridge Service implementation pattern
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 80-106) - Security: Server-Side Guild Filtering
- **Dependencies**:
  - EventConsumer pattern from shared/messaging/consumer.py
  - oauth2.get_user_guilds() for cached guild lookups

### Task 1.2: Create SSE endpoint with FastAPI StreamingResponse

Create SSE endpoint at /api/v1/sse/game-updates that establishes long-lived connection, registers with bridge, and streams events using FastAPI StreamingResponse.

- **Files**:
  - services/api/routes/sse.py (NEW) - SSE endpoint router (~50 lines)
- **Success**:
  - Endpoint authenticates via existing get_current_user dependency
  - Registers connection with SSE bridge (queue, session_token, discord_id)
  - Returns StreamingResponse with text/event-stream media type
  - Sends keepalive pings every 30 seconds to prevent proxy timeouts
  - Cleans up connection on disconnect (finally block)
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 147-192) - SSE Endpoint implementation pattern
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 60-78) - Authentication & Session Management
- **Dependencies**:
  - Task 1.1 completion (SSE bridge service)

### Task 1.3: Integrate SSE bridge into API service lifespan

Start SSE bridge as background task in API service lifespan to consume RabbitMQ events and manage SSE connections.

- **Files**:
  - services/api/app.py - Register SSE router, start bridge in lifespan (~10 lines)
- **Success**:
  - SSE router registered with /api/v1/sse prefix
  - SSE bridge singleton initialized on startup
  - Bridge consumer started as background asyncio task
  - Bridge consumer stopped gracefully on shutdown
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 108-145) - SSE bridge lifecycle management
- **Dependencies**:
  - Task 1.1 and 1.2 completion

## Phase 2: RabbitMQ Integration and Routing Keys

### Task 2.1: Update routing keys to include guild_id (hybrid approach)

Add guild_id to event data and routing keys in both API and Bot publishers to enable future per-guild subscriptions while maintaining backward compatibility with wildcards.

- **Files**:
  - services/api/services/games.py - Add guild_id to event data and routing key (~2 lines)
  - services/bot/events/publisher.py - Add guild_id parameter and use in routing key (~5 lines)
  - services/bot/handlers/join_game.py - Pass guild_id to publisher (~2 lines)
  - services/bot/handlers/leave_game.py - Pass guild_id to publisher (~2 lines)
- **Success**:
  - All game.updated events use routing key format: game.updated.{guild_id}
  - Event data includes guild_id field for server-side filtering
  - Existing consumers using game.updated.* wildcard continue working
  - No breaking changes to event structure
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 237-263) - Routing Key Design: Hybrid Approach
- **Dependencies**:
  - None (independent of other phases)

### Task 2.2: Add web_sse_events queue to RabbitMQ initialization

Configure new RabbitMQ queue for SSE bridge with binding to game.updated.* routing keys.

- **Files**:
  - services/init/rabbitmq_setup.py - Add web_sse_events queue declaration (~5 lines)
- **Success**:
  - Queue web_sse_events created with durable=True
  - Bound to game_scheduler exchange with routing key game.updated.*
  - Multiple consumers can read from different queues (fanout pattern verified)
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 46-58) - RabbitMQ Message Flow Architecture
- **Dependencies**:
  - Task 2.1 completion (routing keys must exist first)

## Phase 3: Frontend Real-Time Updates

### Task 3.1: Create useGameUpdates React hook with EventSource

Create React hook that establishes SSE connection using EventSource API, handles incoming events, and provides callback for game updates.

- **Files**:
  - frontend/src/hooks/useGameUpdates.ts (NEW) - EventSource hook (~40 lines)
- **Success**:
  - Hook accepts guildId and onUpdate callback
  - Creates EventSource with withCredentials: true for cookie authentication
  - Parses incoming SSE messages as JSON
  - Filters events by guildId (client-side redundancy)
  - Calls onUpdate(gameId) for matching events
  - Cleans up EventSource connection on unmount
  - Handles automatic reconnection on errors
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 194-235) - Frontend Integration pattern
- **Dependencies**:
  - Phase 1 completion (SSE endpoint must exist)

### Task 3.2: Add join/leave buttons to GameCard component

Add join/leave action buttons to GameCard for parity with Discord interface, with optimistic updates for immediate feedback.

- **Files**:
  - frontend/src/components/GameCard.tsx - Add join/leave buttons with authorization logic (~50 lines)
- **Success**:
  - Join button visible when user not participant and game not full
  - Leave button visible when user is confirmed participant
  - Buttons call API endpoints /api/v1/games/{id}/join and /api/v1/games/{id}/leave
  - Optimistic updates provide immediate UI feedback before API response
  - Loading states during API calls
  - Error handling with user-friendly messages
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 20-27) - Current GameCard state and requirements
  - services/api/routes/games.py - Existing join/leave REST endpoints
  - frontend/src/pages/GameDetails.tsx - Reference implementation for authorization logic
- **Dependencies**:
  - None (uses existing API endpoints)

### Task 3.3: Integrate SSE updates in BrowseGames and MyGames pages

Add useGameUpdates hook to game listing pages to automatically refetch and update games when SSE events received.

- **Files**:
  - frontend/src/pages/BrowseGames.tsx - Add SSE hook, handle game updates (~15 lines)
  - frontend/src/pages/MyGames.tsx - Add SSE hook, handle game updates (~15 lines)
- **Success**:
  - Pages establish SSE connection on mount
  - On game_updated event, refetch specific game from API
  - Update game in local state array (in-place replacement)
  - GameCard components automatically re-render with updated data
  - No full page refresh required
  - Connection cleaned up on unmount
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 194-235) - Usage pattern in BrowseGames
- **Dependencies**:
  - Task 3.1 completion (useGameUpdates hook)
  - Task 3.2 completion (GameCard join/leave buttons)

## Phase 4: Testing and Validation

### Task 4.1: Create unit tests for SSE endpoint and bridge

Create comprehensive unit tests covering SSE endpoint authentication, connection management, and bridge filtering logic.

- **Files**:
  - tests/services/api/routes/test_sse.py (NEW) - SSE endpoint tests (~100 lines)
  - tests/services/api/services/test_sse_bridge.py (NEW) - Bridge service tests (~100 lines)
- **Success**:
  - Test SSE endpoint requires authentication (401 without session)
  - Test connection registration with bridge
  - Test event filtering by guild membership
  - Test keepalive pings sent every 30 seconds
  - Test disconnect cleanup removes connection
  - Test bridge broadcasts only to authorized users
  - Test cache-based guild membership checks
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 80-106) - Security requirements for testing
- **Dependencies**:
  - Phase 1 completion (SSE infrastructure)

### Task 4.2: Verify cross-platform synchronization (Discord → Web)

Manual testing to verify real-time synchronization when user takes action in Discord and sees immediate update on web page.

- **Success**:
  - Open BrowseGames page in browser
  - Click Discord join button for same game
  - Web page automatically updates to show user as participant within 2 seconds
  - No manual refresh required
  - Verify same behavior for leave action
  - Verify other users' join/leave actions also update the page
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 7-10) - Use case definition
- **Dependencies**:
  - Phase 3 completion (Frontend integration)

### Task 4.3: Validate guild authorization filtering

Test that users only receive SSE events for guilds they are members of, and that kicked users stop receiving events.

- **Success**:
  - User with access to Guild A receives game_updated events for Guild A games
  - User does NOT receive events for Guild B games (not a member)
  - Manually invalidate guild cache, verify user stops receiving events after cache expires
  - Test with multiple concurrent connections from different users
  - Verify no information disclosure across guild boundaries
- **Research References**:
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 80-106) - Security requirements
  - #file:../research/20260205-01-web-join-game-ux-research.md (Lines 108-145) - Cache-based filtering implementation
- **Dependencies**:
  - Phase 1 and 2 completion (SSE infrastructure and routing)

## Dependencies

- FastAPI (existing) - SSE StreamingResponse support
- RabbitMQ (existing) - Event distribution
- Valkey (existing) - Guild membership caching
- EventConsumer pattern (existing) - shared/messaging/consumer.py
- React (existing) - Frontend framework

## Success Criteria

- All phases completed and unit tests passing
- Cross-platform synchronization working bidirectionally (Discord ↔ Web)
- Server-side guild authorization prevents information disclosure
- System handles 100+ concurrent SSE connections without performance degradation
- Users see updates within 2 seconds of actions taken on either platform
- Kicked users stop receiving events within 5 minutes (cache TTL)
