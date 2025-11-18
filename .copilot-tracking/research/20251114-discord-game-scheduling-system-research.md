<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Game Scheduling System

## Research Executed

### External Research

- #fetch:"https://discord.com/developers/docs/intro"
  - Discord API provides two interaction models: WebSocket Gateway and HTTP webhooks
  - Modern approach uses Application Commands (slash commands), Message Components (buttons/select menus), and Modals
  - Message reactions still supported through Gateway events for emoji-based interactions
  - Interactions require security validation with Ed25519 signatures
- #fetch:"https://discord.com/developers/docs/resources/message"
  - Reaction events: MESSAGE_REACTION_ADD, MESSAGE_REACTION_REMOVE
  - Reactions contain emoji information (unicode or custom emoji ID)
  - Messages can be edited to update game session information
- #fetch:"https://github.com/Rapptz/discord.py"

  - Leading Python Discord library with 15.8k stars, 53.5k+ dependents
  - Async/await based architecture for concurrent operations
  - Strong typing support and extensive documentation
  - Mature ecosystem with comprehensive examples
  - Active development with regular updates

- #fetch:"https://fastapi.tiangolo.com/"
  - FastAPI: Modern async Python web framework (91.9k GitHub stars)
  - Built on Starlette (web) and Pydantic (validation)
  - Automatic OpenAPI/Swagger documentation generation
  - High performance comparable to NodeJS and Go
  - Native async/await support throughout
  - Excellent type hint integration and editor support
  - Used by Microsoft, Uber, Netflix for production services
- #fetch:"https://www.sqlalchemy.org/"
  - SQLAlchemy 2.0: Mature Python ORM with 20+ years development
  - Full async support in SQLAlchemy 2.0+
  - Supports multiple database backends (PostgreSQL, MySQL, SQLite)
  - Both ORM and Core (SQL expression language) patterns
  - Powerful query builder and migration support via Alembic
  - Type stubs available for mypy type checking
- #fetch:"https://docs.celeryq.dev/"
  - Celery: Distributed task queue for Python (23k+ GitHub stars)
  - Async task execution with multiple broker support (RabbitMQ, Redis)
  - Periodic task scheduling with Celery Beat
  - Task routing, priority queues, and result backends
  - Proven at scale with millions of messages per day
  - Monitoring tools (Flower) for task management
- #fetch:"https://apscheduler.readthedocs.io/"

  - APScheduler: Python job scheduling library
  - Cron-like, interval-based, and date-based scheduling
  - Lightweight alternative to Celery for simpler use cases
  - Integrates well with async frameworks like FastAPI
  - Multiple job stores (memory, database, Redis)

- #fetch:"https://www.rabbitmq.com/"
  - RabbitMQ: Enterprise-grade message broker (AMQP protocol)
  - Reliable message delivery with acknowledgments and persistence
  - Flexible routing patterns (direct, topic, fanout, headers)
  - Clustering for high availability and scalability
  - Battle-tested by millions worldwide
  - Excellent Python client library (pika, aio-pika for async)
- #fetch:"https://redis.io/"

  - Redis: In-memory data store used as cache, message broker, and database
  - Pub/Sub messaging for real-time communication
  - Used as Celery broker and result backend
  - Sub-millisecond latency for caching and sessions
  - Persistence options for durability
  - Python client: redis-py with async support

- #fetch:"https://www.postgresql.org/about/"
  - PostgreSQL: ACID-compliant relational database with 35+ years development
  - Strong support for JSON/JSONB for flexible schema portions
  - Robust date/time handling with timezone support
  - Powerful indexing and query optimization
- #fetch:"https://react.dev/"
  - React: Component-based UI library (most popular for web UIs)
  - Can be used standalone or with full-stack frameworks
  - Extensive ecosystem and community support
- #fetch:"https://mui.com/"
  - Material-UI: Comprehensive React component library
  - 5.8M weekly downloads, 93.9k GitHub stars
  - Production-ready components with extensive customization
  - Accessibility built-in, excellent documentation
- #fetch:"https://discord.com/developers/docs/topics/oauth2"
  - OAuth2 Authorization Code Flow: Standard web authentication pattern
  - Required scopes: `identify` (user info), `guilds` (server list), `guilds.members.read` (roles)
  - Bot adds users automatically, OAuth2 for web dashboard authentication
  - Access tokens expire (1 week), refresh tokens for long-term sessions
  - User authorization returns: user ID, username, avatar, email (optional), guilds list
- #fetch:"https://discord.com/developers/docs/topics/permissions"
  - Role-based permission system with bitwise flags
  - Roles have hierarchy (position field) determining precedence
  - Guild members can have multiple roles, highest permissions apply
  - Permission checking: Guild > Channel overwrites > Role hierarchy
  - Common permissions: MANAGE_GUILD, ADMINISTRATOR, MANAGE_CHANNELS, SEND_MESSAGES
- #fetch:"https://discord.com/developers/docs/resources/guild#guild-member-object"
  - Guild Member object contains: user, nick, avatar, roles array, joined_at, permissions
  - GET /guilds/{guild_id}/members/{user_id} returns member with role IDs
  - Guild roles endpoint: GET /guilds/{guild_id}/roles returns all guild roles
  - Role object: id, name, permissions bitfield, color, hoist, position
- #fetch:"https://discord.com/developers/docs/resources/user"
  - User object: id (snowflake), username, discriminator, avatar, global_name
  - Display names: Guild members have optional nick (guild-specific nickname)
  - Display priority: nick (guild) > global_name > username
  - User IDs (snowflakes) are globally unique and permanent
  - Usernames/display names can change, always use ID for internal references

## Key Discoveries

### Discord Bot Implementation Patterns

**Discord Buttons (Selected Approach)**

- Buttons are the modern Discord best practice for user interactions
- More reliable than reactions: guaranteed delivery, better UX
- Support custom IDs for tracking interactions with database records
- Can be disabled/updated dynamically (e.g., when game is full)
- Better accessibility with screen reader support
- Mobile-friendly: easier to tap than small emoji reactions
- Clearer user intent with labeled buttons vs emoji interpretation
- Built-in interaction acknowledgment within 3-second window

**Implementation Benefits**

- Discord Gateway delivers INTERACTION_CREATE events reliably
- No missed reactions due to caching or network issues
- Can disable buttons to prevent further interactions (game full, game started)
- Visual feedback with button states (enabled, disabled, loading)
- Analytics and tracking easier with structured interaction events
- Better moderation: interactions are logged and attributable

**Authentication and Message Management**

- Discord messages can be posted by bot in configured channel
- Bot requires permissions: Send Messages, Embed Links, Use External Emojis
- Channel configuration stored in database per guild (server)
- Messages can be edited to update participant lists and button states in real-time
- Message components (buttons) persist across bot restarts

**Permission Checking in Interactions**

- `Interaction.permissions` contains computed permissions for the invoking user in the interaction context
- `Member.guild_permissions` contains server-level permissions (may not reflect channel-specific overwrites)
- `Interaction.permissions` is more reliable as it reflects actual permissions in the interaction's channel
- Best practice: Prefer `interaction.permissions` with fallback to `member.guild_permissions` when available
- In some contexts (DMs, bot restarts), `interaction.user` may not be a full `Member` object
- Permission checking should handle both guild and DM contexts gracefully

### Discord User Identity and Display Names

**User Identification Best Practices**

- User IDs (snowflakes) are globally unique, permanent identifiers
- Display names are context-dependent and mutable:
  - Guild nickname (optional, set per guild by user or admins)
  - Global display name (user's preferred name across Discord)
  - Username (unique identifier, guaranteed to exist)
- Display name resolution priority: `guild_nickname > global_name > username`

**Storage Strategy**

- Database: Store ONLY discordId (snowflake) for all user references
- Never cache usernames, global names, or avatars in database
- These values change frequently and must be fetched at render time
- User table contains only discordId and application-specific data (preferences, etc.)

**Discord Message Rendering (Bot)**

- Use mention format: `<@user_id>` in all messages
- Discord automatically resolves mentions to correct display name for that guild
- Example message construction:
  ```python
  participants_text = "\n".join([f"<@{user.discordId}>" for user in participants])
  message = f"**Participants:**\n{participants_text}"
  # Discord renders: "@GuildNick1\n@GlobalName2\n@Username3"
  ```
- Benefits: Zero latency, always accurate, handles name changes automatically

**Web Interface Rendering (API)**

- Fetch display names at render time using Discord API
- Implementation pattern:
  1. Query database for participant list (returns discordIds)
  2. Call `/guilds/{guild_id}/members` with user IDs to fetch member data
  3. Resolve each user's display name: `member.nick || user.global_name || user.username`
  4. Cache resolved names in Redis (5-minute TTL) to reduce API calls
  5. Return API response with both `discordId` and `displayName` fields
- Cache invalidation: TTL-based (5 minutes) is sufficient, name changes are not real-time critical
- Graceful degradation: If user left guild, show "Unknown User" or fallback to discordId

**Display Name Resolution Service**

```python
class DisplayNameResolver:
    def __init__(self, redis: Redis, discord_api: DiscordAPIClient):
        self.redis = redis
        self.discord_api = discord_api

    async def resolve_display_names(
        self,
        guild_id: str,
        user_ids: list[str]
    ) -> dict[str, str]:
        """Resolve Discord user IDs to display names for a guild"""
        result = {}
        uncached_ids = []

        # Check cache first
        for user_id in user_ids:
            cache_key = f"display:{guild_id}:{user_id}"
            cached = await self.redis.get(cache_key)
            if cached:
                result[user_id] = cached
            else:
                uncached_ids.append(user_id)

        # Batch fetch uncached from Discord API
        if uncached_ids:
            try:
                members = await self.discord_api.get_guild_members(
                    guild_id,
                    user_ids=uncached_ids
                )

                for member in members:
                    user_id = member["user"]["id"]
                    display_name = (
                        member.get("nick") or
                        member["user"].get("global_name") or
                        member["user"]["username"]
                    )
                    result[user_id] = display_name

                    # Cache for 5 minutes
                    cache_key = f"display:{guild_id}:{user_id}"
                    await self.redis.setex(cache_key, 300, display_name)

                # Handle users not found (left guild)
                found_ids = {m["user"]["id"] for m in members}
                for user_id in uncached_ids:
                    if user_id not in found_ids:
                        result[user_id] = "Unknown User"
                        # Don't cache missing users (they might rejoin)

            except DiscordAPIError as e:
                # Fallback: return user IDs if API fails
                logger.error(f"Failed to fetch display names: {e}")
                for user_id in uncached_ids:
                    result[user_id] = f"User#{user_id[-4:]}"

        return result

    async def resolve_single(self, guild_id: str, user_id: str) -> str:
        """Resolve single user display name"""
        result = await self.resolve_display_names(guild_id, [user_id])
        return result.get(user_id, "Unknown User")
```

**API Response Pattern**

```python
# Bad: Only returning discordId forces frontend to fetch names
{
  "participants": [
    {"discordId": "123456789"},
    {"discordId": "987654321"}
  ]
}

# Good: Backend resolves display names before returning
{
  "participants": [
    {"discordId": "123456789", "displayName": "GuildNickname1"},
    {"discordId": "987654321", "displayName": "GlobalName2"}
  ]
}
```

**Frontend Rendering**

```typescript
// Frontend receives resolved display names from API
interface Participant {
  discordId: string;
  displayName: string;
  joinedAt: string;
}

// Simple rendering - no additional API calls needed
function ParticipantList({ participants }: { participants: Participant[] }) {
  return (
    <List>
      {participants.map((p) => (
        <ListItem key={p.discordId}>
          <ListItemText primary={p.displayName} />
        </ListItem>
      ))}
    </List>
  );
}
```

**Discord OAuth2 Authentication Flow**

- Web dashboard uses OAuth2 Authorization Code Flow for user authentication
- Required OAuth2 scopes:
  - `identify`: Get user ID, username, discriminator, avatar
  - `guilds`: List guilds user is member of (for guild selection)
  - `guilds.members.read`: Read user's role assignments in guilds
- Authentication process:
  1. User clicks "Login with Discord" on web dashboard
  2. Redirect to Discord OAuth2 authorization URL with client_id and scopes
  3. User approves, Discord redirects back with authorization code
  4. Backend exchanges code for access_token and refresh_token
  5. Access token valid for 7 days, refresh token for long-term sessions
  6. Store tokens securely (encrypted in database or session storage)
- After authentication, fetch user's guild memberships and roles via Discord API
- Cache role data in Redis with TTL to avoid excessive API calls

**Bot Authorization: "Requires OAuth2 Code Grant" Setting**

- This is a security setting in Discord Application's Bot settings page
- Controls how the bot can be added to servers
- **When DISABLED (Default - Recommended for this project)**:
  - Users add bot via simple invite link
  - Format: `https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=PERMISSIONS&scope=bot`
  - Bot is added immediately without authorization code exchange
  - Simpler flow, standard for typical bots
  - Sufficient when bot only needs bot-level permissions (not user-specific data)
- **When ENABLED**:
  - Requires full OAuth2 Authorization Code Flow to add bot
  - User redirected to Discord, then back with authorization code
  - Code must be exchanged for access token server-side
  - More complex, required only if bot needs to act on behalf of users
  - Needed for accessing user-specific data (DMs, Spotify, etc.)
- **For Game Scheduler Bot**: Keep DISABLED
  - Bot authenticates with bot token (not OAuth2 user tokens)
  - Bot needs only bot permissions (send messages, manage messages, etc.)
  - OAuth2 Code Grant is for web dashboard user authentication, not bot authorization
  - Users should add bot via simple invite link with required permissions

**Role-Based Authorization System**

- Discord roles determine user permissions within the application
- Authorization checks required for:
  - Creating games: Check if user has configured "Game Host" roles
  - Managing guild settings: Check for MANAGE_GUILD or ADMINISTRATOR permission
  - Configuring channels: Check for MANAGE_CHANNELS permission
- Role checking implementation:
  1. Fetch user's Discord guild member object via `/guilds/{guild_id}/members/{user_id}`
  2. Member object contains array of role IDs user has in that guild
  3. Fetch guild roles via `/guilds/{guild_id}/roles` (cached)
  4. Match user's role IDs against configured allowed roles in database
  5. Check role permissions bitfield for administrative operations
- Store allowed role configurations per guild and per channel in database
- Default: Users with MANAGE_GUILD permission can configure settings
- Flexible: Guild admins can designate specific roles as "Game Hosts"

**Pre-populating Participants at Game Creation**

Game hosts can pre-populate participant slots when creating a game with two types of entries:

1. **Discord User Mentions** (@username format):

   - Format: `@username` or `@displayname` (case-insensitive partial matching)
   - Validation: Must resolve to valid guild member before game creation succeeds
   - Search strategy: Query guild members by username/global_name/nickname
   - If mention doesn't match any guild member, creation fails with validation error
   - Error response includes invalid mention names for correction
   - Failed request preserves all form data for re-submission after correction

2. **Placeholder Strings** (non-@ format):
   - Format: Any text without @ prefix (e.g., "Reserved", "TBD", "Guest Slot")
   - Storage: Stored as GameParticipant with NULL userId and displayName field
   - Purpose: Reserve slots for non-Discord users, guests, or pending confirmations
   - Conversion: Can be replaced by Discord users joining later via button/web

**Discord Username Resolution Strategy**

Discord usernames are complex due to multiple naming systems:

- **Username**: Global unique identifier (e.g., "player123")
- **Global Name**: User's preferred display name across Discord (e.g., "Cool Player")
- **Guild Nickname**: Per-guild custom name set by user or admins (e.g., "TeamCaptain")

Resolution approach for @mentions:

1. Strip @ prefix and normalize input (lowercase, trim whitespace)
2. Search guild members via `/guilds/{guild_id}/members/search?query={input}&limit=10`
3. Match against: username, global_name, and guild nickname (case-insensitive contains)
4. If single match found: Use that member's discordId
5. If multiple matches: Return validation error with list of candidates for disambiguation
6. If no matches: Return validation error indicating user not found in guild

**Database Schema Extension**

Extend GameParticipant table to support pre-populated slots:

```python
GameParticipant
- id (primary key)
- gameSessionId (foreign key to GameSession)
- userId (foreign key to User, NULLABLE)  # NULL for placeholder entries
- displayName (string, NULLABLE)  # Used only for placeholder entries
- joinedAt (timestamptz UTC)
- status (JOINED | DROPPED | WAITLIST | PLACEHOLDER)
- isPrePopulated (boolean, default False)  # True if added at creation time
- Note: If userId is NULL, displayName must be set (placeholder)
- Note: If userId is set, displayName should be NULL (resolved at render)
```

**API Request/Response Pattern**

```python
# Request payload for game creation
class CreateGameRequest(BaseModel):
    title: str
    description: str
    scheduled_at: datetime
    guild_id: str
    channel_id: str
    max_players: Optional[int] = None
    reminder_minutes: Optional[list[int]] = None
    rules: Optional[str] = None
    initial_participants: Optional[list[str]] = []  # List of @mentions or placeholder strings

# Success response
{
  "game_id": "uuid",
  "title": "D&D Session",
  "participants": [
    {"discordId": "123456", "displayName": "GameHost", "isPrePopulated": False},
    {"discordId": "789012", "displayName": "PlayerOne", "isPrePopulated": True},
    {"discordId": None, "displayName": "Reserved", "isPrePopulated": True}
  ],
  ...
}

# Validation error response (422 Unprocessable Entity)
{
  "error": "invalid_mentions",
  "message": "Some @mentions could not be resolved",
  "invalid_mentions": [
    {
      "input": "@nonexistentuser",
      "reason": "User not found in guild",
      "suggestions": []
    },
    {
      "input": "@john",
      "reason": "Multiple matches found",
      "suggestions": [
        {"discordId": "111111", "username": "john_doe", "displayName": "John Doe"},
        {"discordId": "222222", "username": "johnny", "displayName": "John Smith"}
      ]
    }
  ],
  "valid_participants": ["@alice", "Reserved", "@bob"],  # Successfully resolved
  "form_data": { /* Echo back all submitted form data */ }
}
```

**Frontend Error Recovery Pattern**

```typescript
// Web Dashboard: Game creation form with error recovery
const [formData, setFormData] = useState({
  title: "",
  description: "",
  scheduledAt: new Date(),
  initialParticipants: "", // Comma or newline separated list
  // ... other fields
});

const [validationErrors, setValidationErrors] = useState(null);

const handleSubmit = async () => {
  try {
    const response = await axios.post("/api/v1/games", {
      ...formData,
      initial_participants: formData.initialParticipants
        .split(/[,\n]/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    });

    // Success: redirect to game details
    navigate(`/games/${response.data.game_id}`);
  } catch (error) {
    if (
      error.response?.status === 422 &&
      error.response.data.error === "invalid_mentions"
    ) {
      // Preserve form data, show validation errors with suggestions
      setValidationErrors(error.response.data);

      // Optionally auto-remove invalid mentions from form
      setFormData({
        ...formData,
        initialParticipants: error.response.data.valid_participants.join(", "),
      });
    } else {
      // Other error types
      showErrorToast(error.message);
    }
  }
};

// Render validation errors with disambiguation UI
{
  validationErrors && (
    <Alert severity="error">
      <AlertTitle>Could not resolve some @mentions</AlertTitle>
      {validationErrors.invalid_mentions.map((err, idx) => (
        <Box key={idx} mb={1}>
          <strong>{err.input}</strong>: {err.reason}
          {err.suggestions.length > 0 && (
            <Box ml={2}>
              <Typography variant="caption">Did you mean:</Typography>
              {err.suggestions.map((sugg) => (
                <Chip
                  label={`@${sugg.username} (${sugg.displayName})`}
                  onClick={() => replaceMention(err.input, `@${sugg.username}`)}
                />
              ))}
            </Box>
          )}
        </Box>
      ))}
    </Alert>
  );
}
```

**Backend Validation Service**

```python
class ParticipantResolver:
    def __init__(self, discord_api: DiscordAPIClient):
        self.discord_api = discord_api

    async def resolve_initial_participants(
        self,
        guild_id: str,
        participant_inputs: list[str]
    ) -> tuple[list[dict], list[dict]]:
        """
        Resolve initial participant list from @mentions and placeholders.

        Returns: (valid_participants, validation_errors)
        """
        valid_participants = []
        validation_errors = []

        for input_text in participant_inputs:
            input_text = input_text.strip()

            if not input_text:
                continue

            if input_text.startswith("@"):
                # Discord mention - validate and resolve
                mention_text = input_text[1:].lower()

                try:
                    # Search guild members
                    members = await self.discord_api.search_guild_members(
                        guild_id,
                        query=mention_text,
                        limit=10
                    )

                    if len(members) == 0:
                        validation_errors.append({
                            "input": input_text,
                            "reason": "User not found in guild",
                            "suggestions": []
                        })
                    elif len(members) == 1:
                        # Single match - use it
                        valid_participants.append({
                            "type": "discord",
                            "discord_id": members[0]["user"]["id"],
                            "original_input": input_text
                        })
                    else:
                        # Multiple matches - disambiguation needed
                        suggestions = [
                            {
                                "discordId": m["user"]["id"],
                                "username": m["user"]["username"],
                                "displayName": m.get("nick") or m["user"].get("global_name") or m["user"]["username"]
                            }
                            for m in members[:5]
                        ]
                        validation_errors.append({
                            "input": input_text,
                            "reason": "Multiple matches found",
                            "suggestions": suggestions
                        })

                except Exception as e:
                    validation_errors.append({
                        "input": input_text,
                        "reason": f"API error: {str(e)}",
                        "suggestions": []
                    })
            else:
                # Placeholder string - always valid
                valid_participants.append({
                    "type": "placeholder",
                    "display_name": input_text,
                    "original_input": input_text
                })

        return valid_participants, validation_errors

    async def create_participant_records(
        self,
        db: AsyncSession,
        game_session_id: uuid.UUID,
        participants: list[dict]
    ) -> list[GameParticipant]:
        """Create GameParticipant records for validated participants."""
        records = []

        for participant in participants:
            if participant["type"] == "discord":
                # Ensure User exists
                user = await self.ensure_user_exists(db, participant["discord_id"])

                record = GameParticipant(
                    gameSessionId=game_session_id,
                    userId=user.id,
                    displayName=None,  # Resolved at render time
                    joinedAt=datetime.now(timezone.utc),
                    status="JOINED",
                    isPrePopulated=True
                )
            else:  # placeholder
                record = GameParticipant(
                    gameSessionId=game_session_id,
                    userId=None,
                    displayName=participant["display_name"],
                    joinedAt=datetime.now(timezone.utc),
                    status="PLACEHOLDER",
                    isPrePopulated=True
                )

            records.append(record)

        db.add_all(records)
        return records
```

**Placeholder Slot Replacement**

When a Discord user joins a game that has placeholder slots:

```python
async def join_game_with_placeholder_handling(
    game_id: uuid.UUID,
    user_discord_id: str,
    db: AsyncSession
):
    """Join game, optionally replacing a placeholder slot."""

    game = await db.get(GameSession, game_id)
    user = await ensure_user_exists(db, user_discord_id)

    # Check if user already joined
    existing = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.gameSessionId == game_id)
        .where(GameParticipant.userId == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Already joined this game")

    # Check if game is full (count non-placeholder participants)
    participant_count = await db.execute(
        select(func.count(GameParticipant.id))
        .where(GameParticipant.gameSessionId == game_id)
        .where(GameParticipant.userId.isnot(None))  # Exclude placeholders
    )
    count = participant_count.scalar()

    max_players = resolve_max_players(game)  # With inheritance

    if count >= max_players:
        raise HTTPException(400, "Game is full")

    # Add as regular participant (placeholder slots don't count toward limit)
    participant = GameParticipant(
        gameSessionId=game_id,
        userId=user.id,
        displayName=None,
        joinedAt=datetime.now(timezone.utc),
        status="JOINED",
        isPrePopulated=False
    )

    db.add(participant)
    await db.commit()

    return participant
```

### Architecture Approaches

**Microservices Architecture (Selected)**

- Separate Python services for distinct responsibilities
- Discord Bot Service: Handles all Discord Gateway interactions and commands
- Web API Service: FastAPI REST API for web dashboard
- Scheduler Service: Celery workers for background jobs and notifications
- Shared PostgreSQL database or message broker for inter-service communication
- Better scalability: scale each service independently
- Clear separation of concerns and easier team division
- More complex deployment but worth it for maintainability

**Communication Patterns**

- RabbitMQ for reliable async messaging between services
- Direct database access for reading shared data (game sessions, users)
- REST API calls between services when synchronous responses needed
- Redis for caching frequently accessed data and session storage

### Database Schema Design

**Core Entities**

```typescript
User (Discord integration)
- id (primary key)
- discordId (unique, snowflake string)
- notificationPreferences (json)
- createdAt (timestamp UTC)
- updatedAt (timestamp UTC)
- Note: Do NOT store username, globalName, or avatar - fetch at render time

GuildConfiguration
- id (primary key)
- guildId (Discord server ID, unique)
- guildName
- defaultMaxPlayers (inherited by channels and games)
- defaultReminderMinutes (json array - e.g., [60, 15])
- defaultRules (text - inherited by games)
- allowedHostRoleIds (json array - role IDs that can create games)
- requireHostRole (boolean - if true, must have role to create games)
- createdAt (timestamp UTC)
- updatedAt (timestamp UTC)

ChannelConfiguration
- id (primary key)
- guildId (foreign key to GuildConfiguration)
- channelId (Discord channel ID, unique)
- channelName
- isActive (boolean - enable/disable game posting in channel)
- maxPlayers (nullable - overrides guild default if set)
- reminderMinutes (json array - nullable, overrides guild if set)
- defaultRules (text - nullable, overrides guild if set)
- allowedHostRoleIds (json array - nullable, overrides guild if set)
- gameCategory (string - e.g., "D&D", "Board Games" - for filtering)
- createdAt (timestamp UTC)
- updatedAt (timestamp UTC)

GameSession
- id (primary key)
- title
- description
- scheduledAt (timestamptz UTC - game start time)
- maxPlayers (inherited from channel or guild if not specified)
- guildId (foreign key to GuildConfiguration)
- channelId (foreign key to ChannelConfiguration)
- messageId (Discord message ID)
- hostId (foreign key to User)
- rules (text - inherited from channel or guild if not specified)
- reminderMinutes (json array - inherited from channel or guild)
- status (SCHEDULED | IN_PROGRESS | COMPLETED | CANCELLED)
- createdAt (timestamptz UTC)
- updatedAt (timestamptz UTC)

GameParticipant (join table)
- id (primary key)
- gameSessionId (foreign key)
- userId (foreign key to User, NULLABLE)
- displayName (string, NULLABLE - used only for placeholder entries)
- joinedAt (timestamptz UTC)
- status (JOINED | DROPPED | WAITLIST | PLACEHOLDER)
- isPrePopulated (boolean, default False)
- Constraint: If userId is NULL, displayName must be set (placeholder entry)
- Constraint: If userId is set, displayName should be NULL (resolved at render time)

UserGuildRole (caching table for Discord roles)
- id (primary key)
- userId (foreign key to User)
- guildId (foreign key to GuildConfiguration)
- roleIds (json array - Discord role IDs user has)
- lastSynced (timestamp UTC)
- ttl (timestamp UTC - cache expiry)
```

**Settings Inheritance Hierarchy**

Settings flow from Guild → Channel → Game with each level able to override:

1. **Guild Level** (GuildConfiguration):
   - Default max players for all games in guild
   - Default reminder times (e.g., 60 min, 15 min before)
   - Default game rules/guidelines
   - Allowed host roles (who can create games)
2. **Channel Level** (ChannelConfiguration):
   - Can override guild's max players
   - Can override guild's reminder times
   - Can override guild's default rules
   - Can override guild's allowed host roles (channel-specific hosts)
   - Additional: game category for channel-specific game types
3. **Game Level** (GameSession):
   - Can override channel's (or guild's) max players
   - Can override channel's (or guild's) reminder times
   - Can override channel's (or guild's) rules
   - Host always has final control over their specific game

**Inheritance Resolution Logic**

```python
# Example: Resolve maxPlayers for a game
def resolve_max_players(game, channel, guild):
    if game.maxPlayers is not None:
        return game.maxPlayers  # Game-level override
    if channel.maxPlayers is not None:
        return channel.maxPlayers  # Channel-level override
    return guild.defaultMaxPlayers  # Guild default

# Example: Resolve allowed host roles
def can_user_host_game(user_roles, channel, guild):
    # Check channel-specific roles first
    if channel.allowedHostRoleIds:
        return any(role in channel.allowedHostRoleIds for role in user_roles)
    # Fall back to guild roles
    if guild.allowedHostRoleIds:
        return any(role in guild.allowedHostRoleIds for role in user_roles)
    # If no roles configured, check for MANAGE_GUILD permission
    return has_manage_guild_permission(user_roles)
```

**Multi-Channel Support Architecture**

- Single guild can have multiple active channels for game announcements
- Each channel can be configured independently with its own:
  - Game category (D&D channel, Board Games channel, Video Games channel)
  - Custom max players (10 for video games, 6 for tabletop)
  - Custom reminder times (30 min for casual, 2 hours for scheduled campaigns)
  - Custom allowed host roles (different moderators per channel)
- Games inherit channel's configuration, allowing channel-specific defaults
- Users can browse games across all channels or filter by channel/category
- Bot posts game announcements to the specific channel configured for that game
- Display name resolution handled by service described in "Discord User Identity and Display Names" section

**Timezone Handling Strategy**

- Store all timestamps in UTC in database (PostgreSQL `TIMESTAMPTZ` type)
- No manual timezone conversion in application code
- Discord: Use Discord's native timestamp formatting (`<t:unix_timestamp:F>`)
  - Discord automatically displays time in each user's local timezone
  - Format codes: F (full), f (short), R (relative), etc.
- Web Browser: Send UTC ISO timestamps to frontend
  - JavaScript `Date` objects handle browser's local timezone automatically
  - Material-UI DateTimePicker works with timezone-aware Date objects
- Notifications: Calculate based on UTC game time, Discord handles display

**Discord Timestamp Formatting Examples**

Discord's native timestamp feature automatically converts to user's local timezone:

```python
# Python: Convert datetime to Unix timestamp for Discord
from datetime import datetime

game_time = datetime(2025, 11, 15, 19, 0, 0)  # UTC
unix_timestamp = int(game_time.timestamp())

# Discord message formats:
# <t:1731700800:F> → "Friday, November 15, 2025 7:00 PM" (user's local time)
# <t:1731700800:f> → "November 15, 2025 7:00 PM"
# <t:1731700800:R> → "in 2 hours" (relative time)
# <t:1731700800:D> → "11/15/2025"
# <t:1731700800:T> → "7:00 PM"
```

**Web Frontend Timezone Handling**

```javascript
// Frontend receives UTC ISO string from API
const gameTime = "2025-11-15T19:00:00Z";

// Browser's Date object automatically uses local timezone
const date = new Date(gameTime);
// Displays in user's browser timezone: "11/15/2025, 2:00 PM" (EST)

// Material-UI DateTimePicker handles timezone automatically
<DateTimePicker
  value={date}
  onChange={(newDate) => {
    // Send back to API as UTC ISO string
    const utcString = newDate.toISOString();
  }}
/>;
```

### Technology Stack Recommendations

**Python Microservices Stack**

_Discord Bot Service_

- discord.py v2.x: Async Discord bot framework with comprehensive features
- Benefits: Mature, well-documented, excellent async support, active community
- Handles: Discord Gateway, slash commands, message components/reactions
- Libraries: discord.py-interactions for modern interaction patterns

_Web API Service_

- FastAPI: High-performance async web framework
- Benefits: Automatic API docs, Pydantic validation, excellent performance
- Features: OAuth2 support, CORS middleware, background tasks
- Uvicorn: ASGI server for production deployment

_Database Layer_

- PostgreSQL: Primary data store
- SQLAlchemy 2.0: Async ORM with strong typing
- Alembic: Database migration tool
- asyncpg: High-performance async PostgreSQL driver

_Message Broker & Task Queue_

- RabbitMQ: Message broker for service communication
- Celery: Distributed task queue for async jobs
- Redis: Cache and Celery result backend
- aio-pika: Async RabbitMQ client for Python

_Scheduling_

- Celery Beat: Periodic task scheduler
- APScheduler: Alternative for simpler scheduling needs
- Both support cron-style scheduling patterns

_Frontend_

- React: UI library
- Material-UI: Component library
- Axios: HTTP client for API calls
- React Router: Client-side routing

**Deployment Architecture**

- Docker containers for each service
- Docker Compose for local development
- Kubernetes or Docker Swarm for production orchestration
- Separate containers: bot, api, celery-worker, celery-beat, postgres, rabbitmq, redis

## Recommended Approach

### Discord OAuth2 Authentication Implementation

**OAuth2 Authorization Code Flow**

```python
# Step 1: Generate authorization URL
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
redirect_uri = "https://your-app.com/api/v1/auth/callback"
scopes = ["identify", "guilds", "guilds.members.read"]
state = generate_random_state()  # CSRF protection

auth_url = f"{DISCORD_OAUTH_URL}?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={' '.join(scopes)}&state={state}"

# Step 2: Exchange code for tokens
token_response = requests.post(
    "https://discord.com/api/oauth2/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
    },
)
# Returns: {"access_token": "...", "refresh_token": "...", "expires_in": 604800}

# Step 3: Fetch user information
user_info = requests.get(
    "https://discord.com/api/users/@me",
    headers={"Authorization": f"Bearer {access_token}"},
).json()
# Returns: {"id": "...", "username": "...", "avatar": "...", "discriminator": "..."}

# Step 4: Fetch user's guilds
guilds = requests.get(
    "https://discord.com/api/users/@me/guilds",
    headers={"Authorization": f"Bearer {access_token}"},
).json()
# Returns: [{"id": "...", "name": "...", "icon": "...", "owner": true, "permissions": "..."}]

# Step 5: Fetch user's roles in specific guild (bot's token required)
member = requests.get(
    f"https://discord.com/api/guilds/{guild_id}/members/{user_id}",
    headers={"Authorization": f"Bot {BOT_TOKEN}"},
).json()
# Returns: {"user": {...}, "nick": "...", "roles": ["role_id_1", "role_id_2"], ...}
```

**Token Management Strategy**

- Store access_token and refresh_token encrypted in database or Redis session
- Access tokens expire after 7 days, implement token refresh before expiry
- Refresh token endpoint: POST to Discord with grant_type=refresh_token
- Cache user's role data in Redis with 5-minute TTL to reduce API calls
- Invalidate role cache when user performs privileged action (force fresh check)

**Role Authorization Middleware**

```python
# FastAPI dependency for role checking
async def check_game_host_permission(
    user_id: str,
    guild_id: str,
    channel_id: str,
    db: AsyncSession,
    redis: Redis,
) -> bool:
    # Check cache first
    cache_key = f"user_roles:{user_id}:{guild_id}"
    cached_roles = await redis.get(cache_key)

    if cached_roles is None:
        # Fetch from Discord API
        member = await discord_api.get_guild_member(guild_id, user_id)
        user_role_ids = member["roles"]
        await redis.setex(cache_key, 300, json.dumps(user_role_ids))  # 5-min TTL
    else:
        user_role_ids = json.loads(cached_roles)

    # Check channel-specific allowed roles first
    channel_config = await db.get(ChannelConfiguration, channelId=channel_id)
    if channel_config.allowedHostRoleIds:
        return any(role_id in channel_config.allowedHostRoleIds for role_id in user_role_ids)

    # Fall back to guild allowed roles
    guild_config = await db.get(GuildConfiguration, guildId=guild_id)
    if guild_config.allowedHostRoleIds:
        return any(role_id in guild_config.allowedHostRoleIds for role_id in user_role_ids)

    # If no roles configured, check for MANAGE_GUILD permission
    guild_roles = await discord_api.get_guild_roles(guild_id)
    for role_id in user_role_ids:
        role = next((r for r in guild_roles if r["id"] == role_id), None)
        if role and (role["permissions"] & 0x00000020):  # MANAGE_GUILD permission
            return True

    return False
```

### Settings Inheritance Implementation

**Inheritance Resolution Service**

```python
# Service to resolve settings with inheritance
class SettingsResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_game_settings(
        self,
        game_session: GameSession,
        channel_config: ChannelConfiguration,
        guild_config: GuildConfiguration
    ) -> ResolvedGameSettings:
        """Resolve final game settings using inheritance hierarchy"""

        return ResolvedGameSettings(
            max_players=self._resolve_max_players(game_session, channel_config, guild_config),
            reminder_minutes=self._resolve_reminders(game_session, channel_config, guild_config),
            rules=self._resolve_rules(game_session, channel_config, guild_config),
            allowed_host_roles=self._resolve_host_roles(channel_config, guild_config),
        )

    def _resolve_max_players(self, game, channel, guild) -> int:
        """Game > Channel > Guild"""
        if game.maxPlayers is not None:
            return game.maxPlayers
        if channel.maxPlayers is not None:
            return channel.maxPlayers
        return guild.defaultMaxPlayers or 10  # Fallback default

    def _resolve_reminders(self, game, channel, guild) -> list[int]:
        """Game > Channel > Guild"""
        if game.reminderMinutes:
            return game.reminderMinutes
        if channel.reminderMinutes:
            return channel.reminderMinutes
        return guild.defaultReminderMinutes or [60, 15]  # Default: 1hr, 15min

    def _resolve_rules(self, game, channel, guild) -> str:
        """Game > Channel > Guild"""
        if game.rules:
            return game.rules
        if channel.defaultRules:
            return channel.defaultRules
        return guild.defaultRules or ""

    def _resolve_host_roles(self, channel, guild) -> list[str]:
        """Channel > Guild (no game-level override)"""
        if channel.allowedHostRoleIds:
            return channel.allowedHostRoleIds
        return guild.allowedHostRoleIds or []
```

**Game Creation with Inheritance**

```python
# API endpoint example
@router.post("/api/v1/games")
async def create_game(
    game_data: CreateGameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch configurations
    guild_config = await db.get(GuildConfiguration, guildId=game_data.guild_id)
    channel_config = await db.get(ChannelConfiguration, channelId=game_data.channel_id)

    # Check authorization
    if not await check_game_host_permission(user.discordId, guild_config, channel_config):
        raise HTTPException(403, "Insufficient permissions to create game")

    # Create game with inherited settings
    resolver = SettingsResolver(db)

    # User provides only overrides, inherit the rest
    game = GameSession(
        title=game_data.title,
        description=game_data.description,
        scheduledAt=game_data.scheduled_at,
        guildId=guild_config.id,
        channelId=channel_config.id,
        hostId=user.id,
        # These can be None to use inheritance
        maxPlayers=game_data.max_players,  # None = inherit
        reminderMinutes=game_data.reminder_minutes,  # None = inherit
        rules=game_data.rules,  # None = inherit
    )

    db.add(game)
    await db.commit()

    # Resolve final settings for event publishing
    final_settings = await resolver.resolve_game_settings(game, channel_config, guild_config)

    # Publish game.created event with resolved settings
    await publish_event("game.created", {
        "game_id": str(game.id),
        "final_settings": final_settings.dict(),
        ...
    })

    return game
```

### Selected Technology Stack (Python Microservices)

- **Language**: Python 3.11+ (async/await, type hints, mature ecosystem)
- **Bot Framework**: discord.py v2.x (leading Python Discord library)
- **Web Framework**: FastAPI (high-performance async REST API framework)
- **Frontend**: React + Material-UI (comprehensive component library)
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async ORM, type-safe)
- **Message Broker**: RabbitMQ (reliable AMQP messaging between services)
- **Task Queue**: Celery + Redis (distributed background job processing)
- **Scheduling**: APScheduler or Celery Beat (periodic task scheduling)
- **Timezone**: Python `datetime` with UTC (no pytz/zoneinfo needed for storage)
- **Discord Timestamps**: Unix epoch for Discord's `<t:timestamp:F>` formatting
- **Frontend Dates**: ISO 8601 UTC strings, browser handles local display
- **Authentication**: Discord OAuth2 for web dashboard (users already on Discord)
- **API Gateway**: Optional nginx or Traefik for routing to services

### Discord Interaction Pattern: Buttons (Modern)

Use Discord's Button components for all player interactions:

**Benefits**

- Modern Discord best practice
- Better UX: clear labels, disabled states, visual feedback
- Reliable: no lost reactions, guaranteed event delivery
- Trackable: custom IDs link directly to database records
- Accessible: screen reader support, keyboard navigation
- Mobile-friendly: easier to tap buttons than small emoji reactions
- State management: buttons can be disabled when game is full or started
- Analytics: structured interaction events for tracking user engagement

**Implementation**

- Game announcement message includes "Join Game" and "Leave Game" buttons
- Buttons have custom IDs: `join_game_{sessionId}` and `leave_game_{sessionId}`
- Game time displayed using Discord timestamp: `<t:{unix_timestamp}:F>`
- When clicked, bot receives INTERACTION_CREATE event via Discord Gateway
- Bot must respond within 3 seconds (deferred response pattern)
- Bot publishes event to RabbitMQ for async processing by worker
- Worker updates database, publishes response back to bot
- Bot edits message to show updated participant count and list
- "Join Game" button disabled when game reaches maxPlayers
- Both buttons disabled when game status changes to IN_PROGRESS or COMPLETED

**Button Component Structure**

```python
# discord.py button implementation
from discord.ui import Button, View

class GameView(View):
    def __init__(self, game_id: str, is_full: bool):
        super().__init__(timeout=None)  # Persistent view

        # Join button
        join_button = Button(
            style=discord.ButtonStyle.success,
            label="Join Game",
            custom_id=f"join_game_{game_id}",
            disabled=is_full
        )

        # Leave button
        leave_button = Button(
            style=discord.ButtonStyle.danger,
            label="Leave Game",
            custom_id=f"leave_game_{game_id}"
        )

        self.add_item(join_button)
        self.add_item(leave_button)
```

**Example Discord Message**

```
🎮 **D&D Campaign Session**

📅 **When:** <t:1731700800:F> (<t:1731700800:R>)
👥 **Players:** 3/5
📍 **Channel:** #voice-channel-1

**Participants:**
<@123456789012345678>
<@234567890123456789>
<@345678901234567890>

[Join Game] [Leave Game]
```

Discord automatically displays each `<@user_id>` as the user's guild-specific display name (nickname if set, otherwise global name or username).

### Microservices Architecture Details

**Service Breakdown**

_Discord Bot Service (discord.py)_

- Responsibilities:
  - Maintain Discord Gateway WebSocket connection
  - Handle slash commands (/list-games, /my-games, /config-guild, /config-channel)
  - Process button interaction events (INTERACTION_CREATE)
  - Send/edit Discord messages with user mentions (`<@user_id>` format)
  - Create and update persistent button views on messages
  - Send notification DMs to users
  - Sync guild/channel configurations when bot joins new server
  - Check user roles for authorization via Discord API
  - Respond to interactions within 3-second Discord timeout
  - Never store usernames/display names - use mentions for auto-resolution
- Communication:
  - Publishes events to RabbitMQ (game_created, player_joined, etc.)
  - Subscribes to notification queue for sending reminders
  - Reads game data directly from PostgreSQL database
  - Caches user role data in Redis (5-minute TTL)
- Deployment: Single container, auto-restarts on failure

_Web API Service (FastAPI)_

- Responsibilities:
  - REST API endpoints for web dashboard
  - Discord OAuth2 authentication flow (authorization code grant)
  - Token management (access token, refresh token storage)
  - User role verification via Discord API
  - Game CRUD operations with authorization checks
  - Guild and channel configuration management
  - List games with filtering (by guild, channel, category)
  - User profile management
  - Display name resolution service for web interface rendering
  - Fetch guild member data to resolve display names at render time
- Communication:
  - Publishes events to RabbitMQ when games created/modified via web
  - Direct PostgreSQL database access for queries
  - Redis for session storage, role caching, and display name caching
  - Discord API calls to fetch member data for display name resolution
- Deployment: Multiple instances behind load balancer

_Scheduler Service (Celery Workers + Beat)_

- Responsibilities:
  - Celery Beat: Periodic check for upcoming games needing notifications
  - Celery Workers: Process notification tasks asynchronously
  - Send reminder notifications via bot service
  - Update game statuses (scheduled → in_progress → completed)
  - Sync Discord role cache (refresh UserGuildRole table)
  - Clean up old completed games
- Communication:
  - Publishes notification requests to RabbitMQ
  - Direct database access for game queries
  - Receives tasks via Celery (RabbitMQ broker)
- Deployment: Separate containers for Beat scheduler and worker pool

**Message Flow Examples**

_Player Joins Game via Discord Button:_

1. User clicks "Join Game" button on Discord message
2. Discord Bot receives INTERACTION*CREATE event with custom_id `join_game*{session_id}`
3. Bot immediately sends deferred response to Discord (prevents 3-second timeout)
4. Bot validates user can join (not already joined, game not full, game status is SCHEDULED)
5. Bot publishes `game.player_joined` event to RabbitMQ with user and game details
6. Celery worker picks up event, updates database (add GameParticipant record)
7. Worker publishes `game.updated` event back to RabbitMQ with new participant list
8. Bot receives update, fetches latest participant list from database
9. Bot edits Discord message with updated participant count and mentions
10. If game now full (reached maxPlayers), bot disables "Join Game" button
11. Bot sends followup response to interaction: "You've joined the game!"

_Host Creates Game via Web Dashboard:_

1. User authenticates via Discord OAuth2 on web dashboard
2. API fetches user's guild memberships and roles via Discord API
3. User selects guild and channel from their available guilds
4. API checks user has permission to create game (allowed host role or MANAGE_GUILD)
5. User selects game time using browser's DateTimePicker (e.g., "Nov 15, 2025 2:00 PM EST")
6. Browser converts to UTC ISO string: "2025-11-15T19:00:00Z"
7. API resolves game settings using inheritance (game → channel → guild)
8. FastAPI validates input and creates GameSession in database with UTC timestamp
9. API publishes `game.created` event to RabbitMQ with Unix timestamp and channel ID
10. API returns success response to web client
11. Discord Bot service subscribed to `game.created` events receives message
12. Bot formats game announcement with Discord timestamp: `<t:1731700800:F>`
13. Bot posts message to the specific channel configured for that game
14. Bot updates GameSession in database with messageId for tracking
15. Each Discord user sees the time in their local timezone automatically
16. Scheduler service picks up new game and schedules notification tasks

_Automated Game Reminder:_

1. Celery Beat scheduler runs periodic task (every 5 minutes)
2. Task queries database for games starting in next hour (UTC comparison)
3. For each game, creates Celery task to send notifications
4. Celery worker processes task, gets participant Discord IDs
5. Worker publishes `notification.send_dm` events to RabbitMQ
6. Discord Bot receives notification requests
7. Bot formats DM with Discord timestamp: "Your game starts <t:1731700800:R>"
8. Discord shows each user relative time in their timezone: "in 45 minutes"
9. Bot marks notifications as sent in database to avoid duplicates

**Inter-Service Communication**

_Synchronous Communication:_

- Web API ← → Database (SQLAlchemy async queries)
- Bot Service ← → Database (SQLAlchemy async queries for read operations)
- All services → Redis (caching, session storage)

_Asynchronous Communication:_

- All services → RabbitMQ (event publishing)
- All services ← RabbitMQ (event consumption via subscriptions)
- Celery tasks via RabbitMQ broker

**Event Schema Examples**

```python
# game.created event
{
  "event_type": "game.created",
  "timestamp": "2025-11-14T10:30:00Z",  # Event time in UTC
  "data": {
    "game_id": "uuid-here",
    "title": "D&D Session",
    "guild_id": "discord-guild-id",
    "host_id": "discord-user-id",
    "scheduled_at": "2025-11-15T19:00:00Z",  # Game time in UTC ISO
    "scheduled_at_unix": 1731700800  # Unix timestamp for Discord
  }
}

# game.player_joined event
{
  "event_type": "game.player_joined",
  "timestamp": "2025-11-14T10:35:00Z",
  "data": {
    "game_id": "uuid-here",
    "player_id": "discord-user-id",
    "player_count": 3,
    "max_players": 5
  }
}

# notification.send_dm event
{
  "event_type": "notification.send_dm",
  "timestamp": "2025-11-15T18:00:00Z",
  "data": {
    "user_id": "discord-user-id",
    "game_id": "uuid-here",
    "game_title": "D&D Session",
    "game_time_unix": 1731700800,  # For Discord <t:timestamp:R>
    "notification_type": "1_hour_before"
  }
}
```

## Implementation Guidance

### Objectives

- Enable Discord users to create game sessions through web dashboard and join games via Discord buttons
- Implement Discord OAuth2 authentication for web dashboard with role-based authorization
- Use Discord guild roles to determine user permissions (game host, admin)
- Support multiple channels per guild with independent configurations
- Implement hierarchical settings inheritance (Guild → Channel → Game)
- Provide game hosts with web dashboard to create and manage sessions
- Handle timezone conversion for global participants using UTC storage and platform display
- Send timely notifications before games start with inherited reminder settings
- Maintain reliable participant tracking and game state across services

### Key Tasks

**Phase 1: Infrastructure Setup**

- Set up Docker development environment with docker-compose.yml
- Configure PostgreSQL database with initial schema
- Set up RabbitMQ message broker with exchanges and queues
- Configure Redis for caching and Celery backend
- Create shared Python package for data models (SQLAlchemy models)
- Set up Alembic for database migrations
- Implement service health checks and monitoring

**Phase 2: Discord Bot Service**

- Initialize discord.py bot with Discord Application credentials
- Implement Gateway connection with auto-reconnect
- Create slash commands:
  - /list-games - List games in current channel or all channels
  - /my-games - Show user's hosted and joined games
  - /config-guild - Configure guild-level settings (admin only)
  - /config-channel - Configure channel-level settings (admin only)
- Implement role authorization checks via Discord API
- Build message formatter for game announcements with buttons
- Create persistent button views (discord.ui.View with timeout=None)
- Implement button interaction handlers:
  - Handle INTERACTION_CREATE events from Discord Gateway
  - Defer response immediately (within 3 seconds) to prevent timeout
  - Validate user not already joined/at capacity
  - Publish join/leave events to RabbitMQ for async processing
  - Edit message with updated participant list and button states
- Use Discord mention format (`<@user_id>`) for all user references in messages
- Set up RabbitMQ event publishing (game events)
- Subscribe to notification queue for sending DMs
- Add guild and channel configuration management
- Cache user roles in Redis with 5-minute TTL
- Never store or cache usernames/display names in database
- Implement button state management (disable when full, started, or completed)**Phase 3: Web API Service**

- Initialize FastAPI application with CORS and middleware
- Implement Discord OAuth2 authentication flow:
  - Authorization endpoint redirect with required scopes
  - Token exchange endpoint (code → access_token + refresh_token)
  - Token refresh endpoint for expired access tokens
  - User info endpoint (fetch user details and guilds)
- Implement role-based authorization middleware
- Create REST API endpoints (versioned as `/api/v1/...`):
  - POST /api/v1/auth/login - Initiate OAuth2 flow
  - GET /api/v1/auth/callback - Handle OAuth2 callback
  - POST /api/v1/auth/refresh - Refresh access token
  - GET /api/v1/auth/user - Get current user info
  - GET /api/v1/guilds - List user's guilds with bot
  - GET /api/v1/guilds/{guild_id}/channels - List configured channels in guild
  - POST /api/v1/guilds/{guild_id}/config - Update guild configuration
  - POST /api/v1/channels/{channel_id}/config - Update channel configuration
  - POST /api/v1/games - Create game (with authorization check)
    - Accept initial_participants array with @mentions and placeholder strings
    - Validate all @mentions resolve to valid guild members
    - Return 422 validation error with suggestions if mentions invalid
    - Preserve form data in error response for client re-submission
    - Create GameParticipant records for validated participants
  - GET /api/v1/games - List games (filterable by guild, channel, category)
  - GET /api/v1/games/{id} - Get game details
  - PUT /api/v1/games/{id} - Update game (host only)
  - DELETE /api/v1/games/{id} - Cancel game (host only)
  - GET /api/v1/games/{id}/participants - List participants
  - POST /api/v1/games/{id}/join - Join game (web interface)
- Integrate SQLAlchemy async for database operations
- Implement Pydantic models for request/response validation
- Set up Redis session storage and role caching
- Configure RabbitMQ event publishing
- Implement settings inheritance resolution logic
- Implement display name resolution service:
  - Fetch guild member data for user IDs when rendering responses
  - Resolve display names using priority: nick > global_name > username
  - Cache resolved display names in Redis with 5-minute TTL
  - Provide batch resolution for lists of participants
  - Never store display names in database, only discordId

**Phase 4: Scheduler Service**

- Set up Celery worker application with RabbitMQ broker
- Configure Celery Beat for periodic tasks
- Implement notification check task (runs every 5 minutes):
  - Query games with scheduled_at within notification window
  - Resolve reminder times using inheritance (game → channel → guild)
  - Create notification tasks for each game's participants
- Implement notification delivery task:
  - Publish notification events to bot service queue
  - Track notification delivery status in database
- Add game status update tasks:
  - Mark games as in_progress when start time reached
  - Mark games as completed after duration
- Implement role cache sync task (refresh UserGuildRole table every 15 minutes)
- Implement cleanup task for old completed games

**Phase 5: Web Dashboard Frontend**

- Set up React application with Material-UI
- Implement Discord OAuth2 login flow with redirect handling
- Create pages:
  - Login: Discord OAuth2 login button
  - Guild Selection: Choose guild to manage (list user's guilds with bot)
  - Guild Dashboard: View/edit guild configuration, list channels
  - Channel Configuration: Edit channel-specific settings
  - Browse Games: Filter by guild, channel, category
  - My Games: Host's game management interface
  - Create Game: Form with guild/channel selector, DateTimePicker (browser timezone-aware)
    - Include multi-line text field for initial participants (@mentions or placeholders)
    - Validate @mentions on submit, show errors with disambiguation UI
    - Preserve all form data on validation error for re-submission
    - Allow quick correction of invalid mentions without re-entering all data
    - Show suggestions for ambiguous mentions with click-to-select chips
  - Game Details: View participants, edit/cancel game (host only)
- Display inherited settings on create game form (show what's inherited vs custom)
- Implement display name resolution for all user references:
  - Fetch display names from API when rendering participant lists
  - API returns both discordId and resolved displayName for each user
  - Show loading state while fetching display names
  - Handle users who have left the guild gracefully (show ID or "Unknown User")
- Send/receive UTC ISO timestamps to/from API
- Browser automatically displays in user's local timezone
- No manual timezone conversion needed in frontend code
- Implement responsive design for mobile access
- Show user's roles and permissions clearly

**Phase 6: Integration & Testing**

- Integration tests for inter-service communication
- End-to-end tests: create game → join via Discord button → receive notifications
- Load testing for concurrent Discord button interactions
- Test failure scenarios (service downtime, message delivery failures)
- Test button interaction timeout handling (3-second response window)
- Test button state management (disabled states, visual feedback)
- Test OAuth2 flow with role permissions
- Test settings inheritance across guild → channel → game
- Test multi-channel game posting and filtering
- Test display name resolution with various scenarios:
  - Users with guild nicknames
  - Users without nicknames (using global names)
  - Users who have changed their display names
  - Users who have left the guild
- Test pre-populated participants feature:
  - Create game with valid @mentions (should succeed)
  - Create game with invalid @mentions (should fail with suggestions)
  - Create game with ambiguous @mentions (should fail with disambiguation)
  - Create game with placeholder strings (should succeed)
  - Create game with mix of @mentions and placeholders (should validate Discord users only)
  - Test form data preservation on validation error
  - Test replacing placeholder slots with Discord users joining
  - Test participant count limits with placeholder slots (placeholders don't count toward limit)
- Monitoring and logging setup (Prometheus, Grafana, ELK stack)

**Phase 7: Advanced Features**

- Waitlist support when game reaches maxPlayers
- Game templates for recurring sessions (inherit from previous game)
- Calendar export (iCal format) for game schedules
- Participant rating and feedback system
- Game history and statistics dashboard per guild/channel
- Advanced role configuration (custom role names, permission overrides)
- Channel categories with shared settings
- Game search and filtering by multiple criteria

### Dependencies

- Python 3.11+
- PostgreSQL 15+
- RabbitMQ 3.12+
- Redis 7+
- Docker and Docker Compose for containerization
- Discord Application with bot token and OAuth2 credentials

### Success Criteria

- Users authenticate via Discord OAuth2 with role-based permissions
- Game hosts can create games via web dashboard with timezone support
- Discord bot posts announcements to specific configured channels with buttons
- Discord messages use mention format (`<@user_id>`) for automatic display name resolution
- Web interface resolves and displays correct guild-specific display names for all users
- Players can join/leave via buttons with immediate feedback (< 3 seconds)
- Participant list stays synchronized between Discord and database
- Notifications sent reliably at scheduled times before games (inherited from channel/guild)
- Web dashboard shows all host's games with management controls
- System supports multiple channels per guild with independent configurations
- Game settings properly inherit from channel → guild hierarchy
- Role-based authorization works for game creation and management
- System handles multiple guilds with separate configurations
- Display names update automatically when users change nicknames
- System handles users leaving guilds gracefully (shows placeholder instead of crashing)
- Game hosts can pre-populate participants with @mentions at creation time
- Invalid @mentions fail game creation with clear validation errors and suggestions
- Ambiguous @mentions show disambiguation UI with selectable options
- Placeholder strings (non-@ format) can be added to reserve slots for non-Discord users
- All form data preserved on validation error for easy correction and re-submission
- Placeholder slots don't count toward maxPlayers limit but are visible in participant list
- Discord users can join games with placeholder slots and both appear in participant list
- Services can be deployed and scaled independently
- System recovers gracefully from individual service failures
- Message delivery guaranteed via RabbitMQ acknowledgments
- User role cache updates automatically and permissions refresh correctly
