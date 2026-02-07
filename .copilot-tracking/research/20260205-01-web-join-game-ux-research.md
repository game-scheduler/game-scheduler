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

### Files to Create (5 new files)

1. `services/api/routes/sse.py` - SSE endpoint (~50 lines)
2. `services/api/services/sse_bridge.py` - RabbitMQ consumer (~150 lines)
3. `frontend/src/hooks/useGameUpdates.ts` - React hook (~40 lines)
4. `tests/integration/test_sse_bridge.py` - Integration tests (~200 lines)
5. `tests/services/api/routes/test_sse.py` - Unit tests (~100 lines - if needed)

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

### Integration Test Specifications

**Test File:** `tests/integration/test_sse_bridge.py`

**Purpose:** Validate SSE bridge infrastructure without Discord complexity

#### Test 1: SSE Connection + RabbitMQ Message Delivery

**Objective:** Verify that publishing a `game.updated.*` event to RabbitMQ results in SSE clients receiving the event within timeout.

**Implementation Pattern:**

```python
@pytest.mark.asyncio
async def test_sse_receives_rabbitmq_game_updated_events(
    authenticated_client,
    test_guild_context,
    rabbitmq_publisher
):
    """SSE client receives game.updated events published to RabbitMQ."""

    # Establish SSE connection using httpx streaming
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"{API_BASE_URL}/api/v1/sse/game-updates",
            cookies=authenticated_client.cookies,
            timeout=30.0
        ) as response:
            # Verify connection established (200 OK)
            assert response.status_code == 200

            # Publish game.updated event to RabbitMQ
            test_game_id = str(uuid4())
            await rabbitmq_publisher.publish(
                event=Event(
                    type=EventType.GAME_UPDATED,
                    data={
                        "game_id": test_game_id,
                        "guild_id": test_guild_context.discord_id
                    }
                ),
                routing_key=f"game.updated.{test_guild_context.discord_id}"
            )

            # Read SSE stream with timeout
            received_event = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])  # Strip "data: " prefix
                    if data.get("type") == "game_updated":
                        received_event = data
                        break

            # Assertions
            assert received_event is not None, "SSE event not received"
            assert received_event["game_id"] == test_game_id
            assert received_event["guild_id"] == test_guild_context.discord_id
```

**Fixtures Required:**

- `authenticated_client` - HTTP client with valid session cookie (existing in integration conftest)
- `test_guild_context` - Guild with user membership (existing pattern)
- `rabbitmq_publisher` - EventPublisher instance (create new fixture)

**Validates:**

- SSE endpoint accepts authenticated connections
- RabbitMQ → SSE bridge message routing
- Event data serialization/deserialization
- Basic authorization (user receives events for their guild)

#### Test 2: Server-Side Guild Authorization Filtering

**Objective:** Verify SSE clients only receive events for guilds they are members of (critical security test).

**Implementation Pattern:**

```python
@pytest.mark.asyncio
async def test_sse_filters_events_by_guild_membership(
    authenticated_client_guild_a,
    authenticated_client_guild_b,
    guild_a_context,
    guild_b_context,
    rabbitmq_publisher
):
    """SSE clients only receive events for guilds they're authorized to access."""

    # Track received events for each client
    guild_a_events = []
    guild_b_events = []

    async def consume_sse_events(client, cookies, event_list):
        """Helper to consume SSE events into list."""
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "GET",
                f"{API_BASE_URL}/api/v1/sse/game-updates",
                cookies=cookies,
                timeout=10.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "game_updated":
                            event_list.append(data)
                            if len(event_list) >= 2:
                                return  # Stop after 2 events max

    # Start both SSE consumers
    consumer_a = asyncio.create_task(
        consume_sse_events(authenticated_client_guild_a,
                          authenticated_client_guild_a.cookies,
                          guild_a_events)
    )
    consumer_b = asyncio.create_task(
        consume_sse_events(authenticated_client_guild_b,
                          authenticated_client_guild_b.cookies,
                          guild_b_events)
    )

    # Wait for connections to establish
    await asyncio.sleep(0.5)

    # Publish event for Guild A
    game_id_a = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            type=EventType.GAME_UPDATED,
            data={"game_id": game_id_a, "guild_id": guild_a_context.discord_id}
        ),
        routing_key=f"game.updated.{guild_a_context.discord_id}"
    )

    # Publish event for Guild B
    game_id_b = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            type=EventType.GAME_UPDATED,
            data={"game_id": game_id_b, "guild_id": guild_b_context.discord_id}
        ),
        routing_key=f"game.updated.{guild_b_context.discord_id}"
    )

    # Wait for event processing
    await asyncio.sleep(2.0)

    # Cancel consumers
    consumer_a.cancel()
    consumer_b.cancel()

    # Assertions: Each client only received events for their guild
    assert len(guild_a_events) == 1, "Guild A user should receive exactly 1 event"
    assert guild_a_events[0]["game_id"] == game_id_a
    assert guild_a_events[0]["guild_id"] == guild_a_context.discord_id

    assert len(guild_b_events) == 1, "Guild B user should receive exactly 1 event"
    assert guild_b_events[0]["game_id"] == game_id_b
    assert guild_b_events[0]["guild_id"] == guild_b_context.discord_id

    # Critical: Verify NO cross-guild leakage
    guild_a_game_ids = [e["game_id"] for e in guild_a_events]
    guild_b_game_ids = [e["game_id"] for e in guild_b_events]

    assert game_id_b not in guild_a_game_ids, "Guild A user MUST NOT receive Guild B events"
    assert game_id_a not in guild_b_game_ids, "Guild B user MUST NOT receive Guild A events"
```

**Fixtures Required:**

- `authenticated_client_guild_a` - HTTP client for user in Guild A (create new fixture)
- `authenticated_client_guild_b` - HTTP client for user in Guild B (create new fixture)
- `guild_a_context` - Guild A configuration with channel and template (existing pattern)
- `guild_b_context` - Guild B configuration with channel and template (existing pattern)
- `rabbitmq_publisher` - EventPublisher instance (shared fixture)

**Validates:**

- Server-side authorization filtering works correctly
- No information disclosure across guilds
- Events routed to correct clients based on guild membership
- Critical security boundary enforcement

#### Test 3: Multiple Concurrent SSE Connections

**Objective:** Verify SSE bridge correctly broadcasts events to multiple simultaneous clients for the same guild.

**Implementation Pattern:**

```python
@pytest.mark.asyncio
async def test_sse_broadcasts_to_multiple_clients(
    test_guild_context,
    rabbitmq_publisher,
    create_authenticated_client
):
    """SSE bridge broadcasts events to all authorized concurrent connections."""

    # Create 5 concurrent SSE connections for same guild
    num_clients = 5
    client_events = [[] for _ in range(num_clients)]

    async def consume_sse(client_id, cookies, event_list):
        """Consumer that collects SSE events."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{API_BASE_URL}/api/v1/sse/game-updates",
                cookies=cookies,
                timeout=10.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "game_updated":
                            event_list.append(data)
                            return  # Stop after first event

    # Create multiple authenticated clients for same user
    clients = []
    for i in range(num_clients):
        client = await create_authenticated_client(test_guild_context.discord_id)
        clients.append(client)

    # Start all SSE consumers
    consumer_tasks = [
        asyncio.create_task(consume_sse(i, client.cookies, client_events[i]))
        for i, client in enumerate(clients)
    ]

    # Wait for connections to establish
    await asyncio.sleep(0.5)

    # Publish single game.updated event
    test_game_id = str(uuid4())
    await rabbitmq_publisher.publish(
        event=Event(
            type=EventType.GAME_UPDATED,
            data={
                "game_id": test_game_id,
                "guild_id": test_guild_context.discord_id
            }
        ),
        routing_key=f"game.updated.{test_guild_context.discord_id}"
    )

    # Wait for all consumers to receive event (or timeout)
    await asyncio.wait(consumer_tasks, timeout=5.0)

    # Cancel any still-running tasks
    for task in consumer_tasks:
        if not task.done():
            task.cancel()

    # Assertions: All clients received the same event
    for i, events in enumerate(client_events):
        assert len(events) == 1, f"Client {i} should receive exactly 1 event"
        assert events[0]["game_id"] == test_game_id
        assert events[0]["guild_id"] == test_guild_context.discord_id

    # Verify all clients got same event
    received_game_ids = [events[0]["game_id"] for events in client_events]
    assert all(game_id == test_game_id for game_id in received_game_ids)
```

**Fixtures Required:**

- `test_guild_context` - Guild configuration (existing pattern)
- `rabbitmq_publisher` - EventPublisher instance (shared fixture)
- `create_authenticated_client` - Factory fixture to create multiple authenticated clients (create new fixture)

**Validates:**

- SSE bridge broadcasts to multiple concurrent connections
- Connection management handles multiple simultaneous clients
- No message loss during fanout
- Scalability for reasonable concurrent connection counts

#### Shared Test Fixtures

**Create in `tests/integration/conftest.py`:**

```python
@pytest.fixture
async def rabbitmq_publisher():
    """EventPublisher for integration tests."""
    publisher = EventPublisher()
    await publisher.connect()
    yield publisher
    await publisher.close()

@pytest.fixture
async def create_authenticated_client(admin_db):
    """Factory to create authenticated HTTP clients for testing."""
    created_clients = []

    async def _create_client(guild_id: str) -> httpx.AsyncClient:
        # Create test user session
        user = User(
            discord_id=str(uuid4()),
            username=f"testuser_{uuid4().hex[:8]}"
        )
        session_token = await create_test_session(admin_db, user, [guild_id])

        client = httpx.AsyncClient(base_url=API_BASE_URL)
        client.cookies.set("session_token", session_token)
        created_clients.append((client, session_token))
        return client

    yield _create_client

    # Cleanup
    for client, session_token in created_clients:
        await client.aclose()
        await cleanup_test_session(admin_db, session_token)

@pytest.fixture
async def authenticated_client_guild_a(
    admin_db,
    guild_a_context
) -> httpx.AsyncClient:
    """Authenticated client for user in Guild A."""
    user = User(
        discord_id=str(uuid4()),
        username="guild_a_user"
    )
    session_token = await create_test_session(
        admin_db, user, [guild_a_context.discord_id]
    )

    client = httpx.AsyncClient(base_url=API_BASE_URL)
    client.cookies.set("session_token", session_token)

    yield client

    await client.aclose()
    await cleanup_test_session(admin_db, session_token)

@pytest.fixture
async def authenticated_client_guild_b(
    admin_db,
    guild_b_context
) -> httpx.AsyncClient:
    """Authenticated client for user in Guild B."""
    user = User(
        discord_id=str(uuid4()),
        username="guild_b_user"
    )
    session_token = await create_test_session(
        admin_db, user, [guild_b_context.discord_id]
    )

    client = httpx.AsyncClient(base_url=API_BASE_URL)
    client.cookies.set("session_token", session_token)

    yield client

    await client.aclose()
    await cleanup_test_session(admin_db, session_token)
```

#### Test Dependencies

**Required Imports:**

```python
import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher
from shared.models.user import User
from tests.shared.auth_helpers import create_test_session, cleanup_test_session
```

**Environment Requirements:**

- API service must be running (`API_BASE_URL` from environment)
- RabbitMQ must be running and configured
- PostgreSQL with test data seeded
- SSE bridge service must be running (started by API lifespan)

#### Test Execution

**Run all SSE integration tests:**

```bash
SKIP_CLEANUP=1 scripts/run-integration-tests.sh tests/integration/test_sse_bridge.py
```

**Run specific test:**

```bash
SKIP_CLEANUP=1 scripts/run-integration-tests.sh tests/integration/test_sse_bridge.py::test_sse_receives_rabbitmq_game_updated_events
```

### Success Criteria

- User joins game via Discord button → Web page updates within 2 seconds
- User joins game via web button → Discord message updates within 2 seconds
- Join/Leave buttons on GameCard provide immediate optimistic feedback
- Only authorized users receive events for their guilds (no information disclosure)
- Users kicked from guild stop receiving events within 5 minutes
- SSE connections handle disconnect/reconnect gracefully
- System handles 100 concurrent SSE connections without performance degradation
- All authentication and authorization checks pass
- **Integration Test #1:** SSE clients receive RabbitMQ events within 5 seconds
- **Integration Test #2:** Guild authorization filtering prevents cross-guild information disclosure
- **Integration Test #3:** Multiple concurrent SSE connections receive same broadcast event
