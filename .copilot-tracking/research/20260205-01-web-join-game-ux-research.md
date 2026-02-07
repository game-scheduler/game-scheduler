<!-- markdownlint-disable-file -->
# Task Research Notes: Web Join Game UX with Real-Time Cross-Platform Sync

## Research Executed

### Use Case Definition
**Scenario:** Same user views web game listing with "Join" button, then joins via Discord button. Web page should automatically update to show "Leave" button without manual refresh.

**This is NOT a multi-user problem** - it's cross-platform state synchronization for a single user across Discord and web interfaces.

### File Analysis
- **frontend/src/components/GameCard.tsx** - Only shows "View Details" button, no join/leave actions on card
- **frontend/src/pages/BrowseGames.tsx** - Renders GameCard components, inherits card-only actions
- **frontend/src/pages/GameDetails.tsx** - Has join/leave buttons with proper gating logic
- **services/api/routes/games.py** - Join/leave REST endpoints exist with authorization
- **services/bot/handlers/join_game.py** - Discord join button writes DIRECTLY to database, publishes to RabbitMQ
- **services/bot/handlers/leave_game.py** - Discord leave button writes DIRECTLY to database, publishes to RabbitMQ
- **services/bot/events/publisher.py** - Bot publishes `game.updated` events to RabbitMQ
- **services/api/services/games.py** - API publishes `game.updated` events to RabbitMQ
- **shared/cache/ttl.py** - USER_GUILDS cache TTL = 300 seconds (5 minutes)
- **shared/discord/client.py** - get_user_guilds() uses Valkey cache with 5-min TTL

### Code Search Results
- **Two Independent Write Paths Discovered:**
  - Web join: Browser → API → Database → RabbitMQ → Bot updates Discord
  - Discord join: Discord button → Bot → Database → RabbitMQ → Bot updates Discord
  - Both paths publish to same RabbitMQ exchange with `game.updated` routing key

- **No Real-Time UI Infrastructure:**
  - No WebSocket endpoints found
  - No SSE (Server-Sent Events) endpoints found
  - No polling mechanisms in frontend
  - Game lists render from one-time fetch, require manual refresh to see updates

- **RabbitMQ Architecture:**
  - Bot consumes from `bot_events` queue with bindings: `game.*`, `notification.*`
  - EventConsumer pattern established in `shared/messaging/consumer.py`
  - Topic exchange routing with wildcard support
  - Current routing keys: `game.updated`, `game.created`, etc. (no guild_id)

### External Research
- **SSE vs WebSocket comparison** - Verified SSE is standard for unidirectional server→client push
- **FastAPI StreamingResponse** - Native SSE support confirmed, no external libraries needed
- **EventSource browser API** - Automatic reconnection built-in, widely supported

### Project Conventions
- Session-based authentication using HTTPOnly cookies (`session_token`)
- RabbitMQ event-driven architecture for service coordination
- Valkey/Redis caching layer with defined TTL constants
- FastAPI dependency injection for authentication and database sessions

## Key Discoveries

### Critical Architectural Finding: Two Write Paths

**The system has TWO independent services that can mutate game participation state:**

1. **API Service Path** (Web actions):
```python
# services/api/routes/games.py
POST /api/v1/games/{id}/join
  → API writes to PostgreSQL
  → API publishes GAME_UPDATED to RabbitMQ
  → Bot consumes event → Updates Discord message
```

2. **Bot Service Path** (Discord actions):
```python
# services/bot/handlers/join_game.py
Discord Join Button Click
  → Bot writes DIRECTLY to PostgreSQL
  → Bot publishes GAME_UPDATED to RabbitMQ
  → Bot consumes its own event → Updates Discord message
```

**This validates the need for real-time sync** - web frontend must see changes made through EITHER path.

### RabbitMQ Message Flow Architecture

**Current Event Flow:**
```
API/Bot publishes → Exchange: "game_scheduler"
                      ↓ (topic routing)
                   Queue: "bot_events"
                      ↓
                   Bot consumes (single consumer)
```

**Proposed SSE Flow:**
```
API/Bot publishes → Exchange: "game_scheduler"
                      ↓ (topic routing - fanout to multiple queues)
                      ├─→ Queue: "bot_events" → Bot Service
                      └─→ Queue: "web_sse_events" → SSE Bridge Service
```

**Key insight:** RabbitMQ topic exchanges support multiple queues with same routing key - message is COPIED to all matching queues, not split between them.

### Authentication & Session Management

**How SSE authenticates:**
- Browser automatically sends `session_token` HTTPOnly cookie with EventSource request
- FastAPI `get_current_user` dependency validates cookie via Valkey lookup
- No custom headers needed - EventSource doesn't support them anyway
- Session expiration handled by existing token infrastructure

**Flow:**
```
Browser: new EventSource('/api/v1/sse/game-updates', {withCredentials: true})
  → Cookie: session_token=abc123 (automatic)
  → FastAPI: Depends(get_current_user) validates
  → Returns CurrentUser with access_token
  → Fetch user's guilds via oauth2.get_user_guilds() (cached 5 min)
```

### Security: Server-Side Guild Filtering

**CRITICAL SECURITY REQUIREMENT:** Cannot broadcast all game_ids to all SSE connections.

**Must filter server-side:**
```python
# INSECURE - DON'T DO THIS:
for connection in all_connections:
    await connection.send(event)  # Leaks game IDs from other guilds!

# SECURE - Filter by authorized guilds:
for connection in all_connections:
    user_guilds = await get_user_guilds(connection.token)
    if event.guild_id in user_guilds:
        await connection.send(event)
```

**Why this matters:**
- Information disclosure: Game IDs reveal guild activity to unauthorized users
- Privacy violation: Private guild events must not leak
- Authorization bypass risk: Knowing game IDs could enable attacks

### Cache-Based Guild Revocation Strategy

**Problem:** User gets kicked from guild, should stop receiving events.

**Solution:** Check guild membership on EVERY event using Valkey cache:

```python
async def _broadcast_to_clients(self, event):
    guild_id = event.data["guild_id"]

    for client_id, (queue, session_token, discord_id) in self.connections.items():
        # Fetch guilds from cache (0.2ms - 99% cache hit rate)
        user_guilds = await oauth2.get_user_guilds(access_token, discord_id)

        if guild_id in {g["id"] for g in user_guilds}:
            await queue.put(message)
```

**Why this works:**
- Cache TTL = 5 minutes (CacheTTL.USER_GUILDS = 300 seconds)
- User kicked from guild → cache expires within 5 min → stops receiving events
- Cache hit latency ~0.2ms (Valkey localhost)
- Performance cost negligible: 100 connections × 10 events/min = 1,000 cache reads/min = 0.3% CPU

**Alternative rejected:** Storing guilds once at connection time
- Pros: Zero cache overhead during events
- Cons: User continues receiving events after being kicked until browser disconnect
- Verdict: Not acceptable - kicked users should stop receiving updates promptly

## Implementation Patterns

### SSE Endpoint with FastAPI StreamingResponse

```python
# services/api/routes/sse.py (NEW FILE - ~50 lines)
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/sse", tags=["sse"])

@router.get("/game-updates")
async def game_updates(
    current_user: CurrentUser = Depends(get_current_user)
):
    """SSE endpoint for real-time game updates."""

    client_id = f"{current_user.user.discord_id}_{uuid.uuid4()}"
    queue = asyncio.Queue(maxsize=100)

    bridge = get_sse_bridge()
    bridge.connections[client_id] = (
        queue,
        current_user.session_token,
        current_user.user.discord_id
    )

    async def event_stream():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"  # Prevent proxy timeout
        finally:
            # FastAPI automatically triggers on disconnect
            bridge.connections.pop(client_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

### SSE Bridge Service (RabbitMQ Consumer)

```python
# services/api/services/sse_bridge.py (NEW FILE - ~150 lines)
class SSEGameUpdateBridge:
    def __init__(self):
        self.connections: dict[str, tuple[asyncio.Queue, str, str]] = {}
        self.consumer: EventConsumer | None = None

    async def start_consuming(self):
        """Background task: consume RabbitMQ game.* events"""
        self.consumer = EventConsumer(queue_name="web_sse_events")
        await self.consumer.connect()

        # Use wildcard for initial implementation
        await self.consumer.bind("game.updated.*")

        self.consumer.register_handler(
            EventType.GAME_UPDATED,
            self._broadcast_to_clients
        )

        await self.consumer.start_consuming()

    async def _broadcast_to_clients(self, event):
        """Push event to authorized SSE connections."""
        guild_id = event.data.get("guild_id")
        if not guild_id:
            return

        message = json.dumps({
            "type": "game_updated",
            "game_id": event.data["game_id"],
            "guild_id": guild_id
        })

        # Loop over all connections (application-level filtering)
        for client_id, (queue, session_token, discord_id) in self.connections.items():
            try:
                # Fetch from cache (5-min TTL)
                token_data = await tokens.get_user_tokens(session_token)
                if not token_data:
                    continue

                user_guilds = await oauth2.get_user_guilds(
                    token_data["access_token"],
                    discord_id
                )

                # Server-side authorization
                if guild_id in {g["id"] for g in user_guilds}:
                    await queue.put(message)

            except Exception as e:
                logger.warning(f"Failed to check guild membership: {e}")
```

### Frontend Integration

```typescript
// frontend/src/hooks/useGameUpdates.ts (NEW FILE - ~40 lines)
export function useGameUpdates(
  guildId: string,
  onUpdate: (gameId: string) => void
) {
  useEffect(() => {
    const eventSource = new EventSource('/api/v1/sse/game-updates', {
      withCredentials: true  // Sends session cookie automatically
    });

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.guild_id === guildId) {
        onUpdate(data.game_id);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE connection error');
      // EventSource automatically reconnects
    };

    return () => eventSource.close();
  }, [guildId, onUpdate]);
}

// Usage in BrowseGames.tsx
function BrowseGames() {
  const [games, setGames] = useState<Game[]>([]);
  const { guildId } = useParams();

  useGameUpdates(guildId, async (updatedGameId) => {
    const updated = await apiClient.get(`/api/v1/games/${updatedGameId}`);
    setGames(prev =>
      prev.map(g => g.id === updatedGameId ? updated.data : g)
    );
  });

  return <GameCard components>...
}
```

### Routing Key Design: Hybrid Approach

**Current routing keys:** `game.updated` (no guild isolation)

**Proposed routing keys:** `game.updated.{guild_id}` (future-ready)

**Why add guild_id NOW even if not using it:**
- Enables future per-guild subscriptions without republisher changes
- Better observability in RabbitMQ monitoring
- Zero performance cost - wildcards work the same
- No breaking changes later

**Implementation:**
```python
# services/api/services/games.py - MODIFY
await self.publisher.publish(
    event=event,
    routing_key=f"game.updated.{game.guild_id}"  # Add guild_id
)

# services/bot/events/publisher.py - MODIFY
async def publish_game_updated(self, game_id: str, guild_id: str, ...):
    routing_key = f"game.updated.{guild_id}"
    await self.publisher.publish(event=event, routing_key=routing_key)

# Consumers still use wildcards
await consumer.bind("game.updated.*")  # Matches all guilds
```

## Performance Analysis

### Valkey Cache Hit Performance

**Single-instance Valkey (typical deployment):**
- GET operations: 80,000-100,000 ops/second
- Latency (localhost): 0.1-0.5ms (sub-millisecond)
- P99 latency: < 1ms

**Project's cache infrastructure:**
- Valkey 9.0.1 (latest stable)
- Docker container on typical hardware
- Expected: 50,000+ ops/sec easily

### SSE Event Broadcasting Performance

**Scenario:** 100 concurrent SSE connections, 10 game updates/minute

**Shared queue with application filtering:**
```
10 events/min × 100 connections = 1,000 operations/minute

Per event:
  - Loop over 100 connections: O(N) iteration (negligible)
  - 100 cache reads: 100 × 0.2ms = 20ms (assuming cache hits)
  - 100 hash checks: 100 × 0.001ms = 0.1ms
  - ~20 queue puts: 20 × 0.001ms ≈ 0ms

Total: ~20ms per event
Total CPU: 10 events/min × 20ms = 200ms/minute = 0.3% of one core
```

**Performance verdict:** Negligible overhead at reasonable scale.

### Scaling Thresholds

**When would shared queue become a bottleneck?**
- 1,000+ concurrent SSE connections
- 100+ game updates/second
- = 100,000+ cache reads/second (approaching Valkey limits)

**For Discord game scheduler:** Will never hit these numbers. Shared queue is appropriate.

### RabbitMQ Queue Architecture Trade-offs

**Shared Queue (Recommended):**
- 1 queue: `web_sse_events`
- 1 EventConsumer
- All events delivered, filtered in Python
- Pros: Simple, no lifecycle management, works for all use cases
- Cons: Wastes bandwidth (~5% efficiency), small CPU for filtering

**Per-Client Queues (Future Optimization):**
- N queues: `web_sse_user{id}_conn{uuid}` (one per connection)
- N EventConsumers (one per connection)
- RabbitMQ routes only relevant events per queue
- Pros: No filtering overhead, efficient delivery
- Cons: Complex (dynamic queue creation/deletion), 100+ connections = 100+ queues

**Recommendation:** Start with shared queue, optimize only if monitoring shows >5% CPU on filtering.

## Recommended Approach

### Solution: SSE with RabbitMQ Bridge and Cache-Based Authorization

**Architecture:**
1. Add SSE endpoint at `/api/v1/sse/game-updates` using FastAPI StreamingResponse
2. Create SSE bridge service that consumes from new `web_sse_events` RabbitMQ queue
3. Bridge subscribes to `game.updated.*` routing keys (wildcard for all guilds)
4. On each event, bridge checks user's guild memberships via cached `get_user_guilds()`
5. Only sends events to connections where user is member of event's guild
6. Frontend uses EventSource to connect, receives game_id notifications
7. Frontend refetches only the updated game, updates in-place
8. Add optimistic updates for join/leave actions (immediate UI feedback)

**Why SSE over WebSocket:**
- Unidirectional: Server only needs to push updates, client uses REST for commands
- Simpler: Native EventSource API, automatic reconnection built-in
- Standard: FastAPI StreamingResponse, no protocol upgrade negotiation
- Sufficient: Don't need bidirectional for this use case

**Why RabbitMQ Integration:**
- Fits existing event-driven architecture
- Both Bot and API already publish GAME_UPDATED events
- Adding another consumer (SSE bridge) is the pattern
- No duplicate notification paths - single source of truth

**Why Cache-Based Guild Checks:**
- Security: Server-side authorization prevents information disclosure
- Performance: 0.2ms per check with 99% cache hit rate
- Timely revocation: Kicked users stop receiving events within 5 minutes
- Simple: No complex connection lifecycle management

## Implementation Guidance

### Complexity Estimate

**New code:** ~340 lines
**Modified code:** ~96 lines
**Total:** ~436 lines across 10 files

**Time estimate:** 5-8 hours (one solid workday)

**Difficulty: 4/10 - Moderate**

**Why not harder:**
- ✅ FastAPI has native SSE support
- ✅ RabbitMQ infrastructure already exists
- ✅ EventConsumer pattern established
- ✅ Cache infrastructure handles guild checks
- ✅ Join/Leave API endpoints already exist

**Why not easier:**
- ⚠️ New architectural component (SSE bridge)
- ⚠️ Managing long-lived connections
- ⚠️ Error handling for connection failures
- ⚠️ Frontend state management for real-time updates

### Files to Create (4 new files)

1. `services/api/routes/sse.py` - SSE endpoint (~50 lines)
2. `services/api/services/sse_bridge.py` - RabbitMQ consumer (~150 lines)
3. `frontend/src/hooks/useGameUpdates.ts` - React hook (~40 lines)
4. `tests/services/api/routes/test_sse.py` - Unit tests (~100 lines)

### Files to Modify (6+ files)

1. `services/api/app.py` - Register SSE router, start bridge in lifespan (~10 lines)
2. `services/api/services/games.py` - Add guild_id to GAME_UPDATED event data and routing key (~2 lines)
3. `services/bot/events/publisher.py` - Add guild_id parameter and routing key (~5 lines)
4. `services/bot/handlers/join_game.py` - Pass guild_id to publisher (~2 lines)
5. `services/bot/handlers/leave_game.py` - Pass guild_id to publisher (~2 lines)
6. `frontend/src/components/GameCard.tsx` - Add Join/Leave buttons (~50 lines)
7. `frontend/src/pages/BrowseGames.tsx` - Add SSE hook (~15 lines)
8. `frontend/src/pages/MyGames.tsx` - Add SSE hook (~15 lines)

### Key Implementation Tasks

**Backend:**
1. Create SSE bridge service with EventConsumer for `web_sse_events` queue
2. Implement server-side guild filtering using cached `get_user_guilds()`
3. Create SSE endpoint with FastAPI StreamingResponse
4. Add keepalive pings every 30 seconds to prevent proxy timeouts
5. Handle disconnect cleanup (FastAPI finally block)
6. Start bridge consumer as background task in API lifespan
7. Add guild_id to event data and routing keys (hybrid approach)
8. Update bot publisher to accept and use guild_id in routing key

**Frontend:**
1. Create useGameUpdates React hook with EventSource
2. Handle SSE events: parse game_id, refetch updated game
3. Add Join/Leave buttons to GameCard component
4. Implement optimistic updates for immediate feedback
5. Handle connection errors and automatic reconnection

**Infrastructure:**
1. RabbitMQ queue setup handled by init service (add `web_sse_events` queue)
2. Binding to `game.updated.*` routing key

### Success Criteria

- User joins game via Discord button → Web page updates within 2 seconds
- User joins game via web button → Discord message updates within 2 seconds
- Join/Leave buttons on GameCard provide immediate optimistic feedback
- Only authorized users receive events for their guilds (no information disclosure)
- Users kicked from guild stop receiving events within 5 minutes
- SSE connections handle disconnect/reconnect gracefully
- System handles 100 concurrent SSE connections without performance degradation
- All authentication and authorization checks pass
