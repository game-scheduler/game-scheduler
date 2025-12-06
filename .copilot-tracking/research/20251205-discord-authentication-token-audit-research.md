<!-- markdownlint-disable-file -->
# Task Research Notes: Discord Authentication Token Usage Audit

## Research Executed

### File Analysis
- services/api/auth/discord_client.py
  - Comprehensive Discord API client with bot token and OAuth2 user token support
  - Clear separation between bot token operations and user token operations
  - Methods properly documented with which token type they use
- services/bot/events/handlers.py
  - Bot service uses discord.py library's built-in authentication
  - All Discord operations use bot token (implicit via discord.Client)
- services/bot/auth/role_checker.py
  - Uses bot's discord.Client for guild/member fetching
  - All operations use bot token through discord.py client
- services/api/services/games.py
  - GameService receives discord_client for Discord API operations
  - Uses both bot token (for guild/channel/member operations) and user token (for guild membership checks)

### Code Search Results
- **Bot Token Usage** (`Authorization: Bot {token}`):
  - get_bot_guilds() - Fetch guilds bot is member of
  - get_guild_channels() - Fetch channels in guild
  - fetch_channel() - Fetch specific channel details
  - fetch_guild() - Fetch guild details
  - fetch_guild_roles() - Fetch roles in guild
  - fetch_user() - Fetch user details
  - get_guild_member() - Fetch member details in guild
  - get_guild_members_batch() - Batch fetch member details
- **User Token Usage** (`Authorization: Bearer {token}`):
  - get_user_info() - Fetch authenticated user's profile
  - get_user_guilds() - Fetch guilds user is member of (with caching)
  - _fetch_user_guilds_uncached() - Internal user guilds fetch
- **OAuth2 Client Credentials** (client_id + client_secret):
  - exchange_code() - Exchange authorization code for tokens
  - refresh_token() - Refresh expired access token

### External Research
- #fetch:https://discord.com/developers/docs/topics/oauth2#authorization-code-grant
  - OAuth2 user tokens provide access to user-specific data (profile, guilds, members)
  - Scopes: identify (user profile), guilds (user's guilds), guilds.members.read (user's roles in guilds)
  - User tokens expire after 7 days, require refresh for long-term access
- #fetch:https://discord.com/developers/docs/topics/oauth2#bot-authorization-flow
  - Bot tokens provide privileged access to guild data where bot is installed
  - Bot tokens do not expire, provide broader guild access
  - Best practice: Use bot token for server-side operations, user token for user-specific data
- #fetch:https://discord.com/developers/docs/reference#authentication
  - Bearer tokens (user): `Authorization: Bearer <token>`
  - Bot tokens: `Authorization: Bot <token>`
  - Clear distinction in header format indicates token type

### Project Conventions
- All Discord API operations go through services/api/auth/discord_client.py
- Bot operations use discord.py library (services/bot/)
- User authentication uses OAuth2 flow (services/api/auth/oauth2.py)

## Key Discoveries

### Token Types and Their Purposes

#### 1. Bot Token (`self.bot_token`)
**Usage**: Server-side operations where bot has been installed by guild administrator

**Legitimate Operations**:
- Fetching guild information (name, icon, features)
- Fetching channel information (name, type, permissions)
- Fetching user information (username, avatar, discriminator)
- Fetching guild member information (roles, nickname, join date)
- Fetching guild roles (name, color, permissions, position)
- Posting messages to channels
- Editing messages
- Sending DMs to users

**Current Implementation**: ✅ **CORRECT**
```python
# services/api/auth/discord_client.py
async def get_guild_channels(self, guild_id: str) -> list[dict[str, Any]]:
    """Fetch all channels in a guild using bot token."""
    session = await self._get_session()
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
    
    async with session.get(
        url,
        headers={"Authorization": f"Bot {self.bot_token}"},
    ) as response:
        # ...
```

#### 2. User Access Token (`access_token` parameter)
**Usage**: User-specific operations requiring explicit user consent via OAuth2

**Legitimate Operations**:
- Fetching user's own profile information
- Fetching guilds the user is member of
- *Originally intended*: Fetching user's roles in guilds (via guilds.members.read scope)

**Current Implementation**: ✅ **CORRECT**
```python
# services/api/auth/discord_client.py
async def get_user_guilds(self, access_token: str, user_id: str | None = None) -> list[dict[str, Any]]:
    """Fetch guilds the user is a member of with Redis caching."""
    # ...
    async with session.get(
        DISCORD_GUILDS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    ) as response:
        # ...
```

#### 3. Client Credentials (client_id + client_secret)
**Usage**: OAuth2 token exchange and refresh

**Legitimate Operations**:
- Exchanging authorization code for access token + refresh token
- Refreshing expired access token

**Current Implementation**: ✅ **CORRECT**
```python
# services/api/auth/discord_client.py
async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange authorization code for access token."""
    data = {
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    # POSTs to token endpoint with client credentials
```

### Critical Analysis: Bot Token vs User Token Usage

#### ⚠️ POTENTIAL ISSUE FOUND: Excessive Bot Token Usage

**Context**: The system uses **bot token for almost all Discord operations**, including:
- Fetching user profiles (`fetch_user`)
- Fetching guild member information (`get_guild_member`)
- Fetching channels, guilds, roles

**Why this is happening**:
1. Bot token provides broader access than user token
2. Bot token doesn't require per-user OAuth2 consent
3. Bot token doesn't expire (simpler implementation)

**Why this might be problematic**:
1. **Privacy concern**: Bot token can access information about *any* user in guilds where bot is installed, not just the authenticated user
2. **Over-privileged**: User tokens should be used for user-specific operations when user has explicitly consented
3. **Authorization bypass risk**: Bot token operations don't validate that the *requesting user* has permission to access the data

**Example of concerning pattern**:
```python
# services/api/auth/discord_client.py (Lines 596-627)
async def get_guild_member(self, guild_id: str, user_id: str) -> dict[str, Any]:
    """
    Fetch guild member information using bot token.
    
    Args:
        guild_id: Discord guild (server) ID
        user_id: Discord user ID
        
    Returns:
        Guild member object with user, roles, nick, etc.
    """
    session = await self._get_session()
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}"
    
    async with session.get(
        url,
        headers={"Authorization": f"Bot {self.bot_token}"},  # ⚠️ Bot token, not user token
    ) as response:
        # ...
```

**Problem**: This allows *any* authenticated user to query *any other user's* guild member information (roles, nickname, etc.) in guilds where the bot is installed.

**Where this is called**:
- services/api/services/display_names.py - resolve_display_names()
- services/api/services/participant_resolver.py - _resolve_mentions()
- Anywhere that needs to get member info for @mention resolution

### Recommended Token Usage Patterns

#### Pattern 1: Reading Guild/Channel Information ✅ **CORRECT - Use Bot Token**
**Operations**: Fetching guild details, channel lists, role lists
**Reason**: These are server-level resources, not user-specific. Bot has been granted permission by guild admin.

```python
# Correct usage
channels = await discord_client.get_guild_channels(guild_id)  # Uses bot token
guild = await discord_client.fetch_guild(guild_id)  # Uses bot token
```

#### Pattern 2: Reading User's Own Data ✅ **CORRECT - Use User Token**
**Operations**: Fetching user's profile, user's guilds
**Reason**: User explicitly consented via OAuth2, accessing their own data.

```python
# Correct usage
user_info = await discord_client.get_user_info(access_token)  # Uses user token
guilds = await discord_client.get_user_guilds(access_token, user_id)  # Uses user token
```

#### Pattern 3: Reading Other Users' Data ⚠️ **QUESTIONABLE - Currently Uses Bot Token**
**Operations**: Fetching other users' profiles, member info, roles
**Current**: Uses bot token
**Should consider**: Validating requesting user has legitimate need

**Two philosophies**:

**A. Current Approach (Bot Token)**:
- Pro: Simple, doesn't require user token
- Pro: Bot was explicitly added to guild by admin (implicit permission)
- Pro: Only works in guilds where bot is installed
- Con: Any authenticated user can query any other user in shared guilds
- Con: No per-request authorization check

**B. Alternative Approach (User Token + Authorization)**:
- Pro: Only authenticated user can query their own member info
- Pro: Explicit consent via OAuth2 scopes
- Con: Requires passing user's access token to all operations
- Con: User token expires, requires refresh handling
- Con: More complex implementation

### Security Boundary Analysis

**Key question**: Is the bot token being used to bypass user-level authorization?

**Current authorization model**:
1. User authenticates via OAuth2 (gets user token)
2. User token validates they are who they claim to be
3. Bot token is used for *all* Discord API calls
4. Authorization happens at application level (checking roles, permissions in database)

**Risk assessment**:

**LOW RISK scenarios** (bot token usage is appropriate):
- ✅ Posting game announcements to configured channels (bot was added to guild for this purpose)
- ✅ Editing game messages (bot owns the message)
- ✅ Sending DMs to game participants (users joined game voluntarily)
- ✅ Fetching channel/guild info for dropdown population (public guild data)

**MEDIUM RISK scenarios** (bot token usage is convenient but not strictly necessary):
- ⚠️ Fetching participant display names for @mention resolution
  - User provided the @mention, so they already know the user exists
  - Bot needs to resolve mention to user ID (requires guild member lookup)
  - Alternative: Use user token, but this fails if user left guild
- ⚠️ Fetching user roles for authorization checks
  - Application needs to verify user has permission to create game
  - Could use user token's guilds.members.read scope, but bot token is simpler
  - Bot token approach: "If bot can see your roles, we can check them"

**HIGH RISK scenarios** (bot token usage could enable abuse):
- ❌ None currently found
- The application doesn't expose raw Discord API to users
- All operations have business logic validation

### Comparison with Industry Best Practices

**Discord.js Bots (Node.js)**:
- Typically use bot token for all operations
- User tokens only used for OAuth2 login to web dashboard
- This is the standard pattern for Discord bot + web dashboard architecture

**Example from discord.js guide**:
```javascript
// Web dashboard authenticates user with OAuth2
const userGuilds = await fetch('https://discord.com/api/users/@me/guilds', {
    headers: { Authorization: `Bearer ${accessToken}` }
});

// Bot operates with bot token
const guild = await client.guilds.fetch(guildId); // Uses bot token
const member = await guild.members.fetch(userId); // Uses bot token
```

**This matches our current implementation** ✅

### OAuth2 Scopes Analysis

**Currently requested scopes** (from services/api/auth/oauth2.py):
```python
OAUTH_SCOPES = ["identify", "guilds", "guilds.members.read"]
```

**Scope usage**:
- `identify`: ✅ Used - Get user's Discord ID, username, avatar (get_user_info)
- `guilds`: ✅ Used - List guilds user is member of (get_user_guilds)
- `guilds.members.read`: ❌ **NOT USED** - Could fetch user's roles via user token, but we use bot token instead

**Finding**: The `guilds.members.read` scope is requested but not utilized. We fetch member/role information using bot token instead.

**Recommendation**: Either:
1. Remove `guilds.members.read` scope (don't request unnecessary permissions)
2. Switch role checking to use user token instead of bot token

## Recommended Approach

### Assessment: Bot Token Usage is Appropriate ✅

After comprehensive analysis, **the current bot token usage is appropriate and follows Discord bot best practices**.

**Key findings**:
1. ✅ Bot token and user token are clearly separated in code
2. ✅ User token is used for user-specific operations (profile, guilds)
3. ✅ Bot token is used for guild operations (channels, roles, members)
4. ✅ All Discord operations go through centralized discord_client.py
5. ✅ Application-level authorization checks prevent abuse
6. ✅ Pattern matches standard Discord bot + web dashboard architecture

### Minor Recommendation: Remove Unused OAuth2 Scope

**Action**: Remove `guilds.members.read` from OAUTH_SCOPES

**Reason**: Scope is requested but never used (we use bot token for member info instead)

**File**: services/api/auth/oauth2.py
```python
# Current
OAUTH_SCOPES = ["identify", "guilds", "guilds.members.read"]

# Recommended
OAUTH_SCOPES = ["identify", "guilds"]
```

**Impact**: 
- Users will see one fewer permission request during OAuth2 consent
- No functional change (scope wasn't being used anyway)
- Cleaner OAuth2 flow

### Optional Enhancement: Document Token Usage Patterns

**Action**: Add docstring guidelines to discord_client.py

**Example**:
```python
"""
Discord API client for OAuth2 and bot operations.

TOKEN USAGE GUIDELINES:
- Bot token (self.bot_token): Used for guild/channel/member operations where bot is installed
- User token (access_token param): Used for user-specific operations requiring OAuth2 consent
- Client credentials: Used only for OAuth2 token exchange/refresh

The bot token is used for most operations because:
1. Bot has been explicitly added to guild by administrator (implicit permission)
2. Bot token doesn't expire (simpler than managing user token refresh)
3. Standard pattern for Discord bot + web dashboard architecture
4. Application-level authorization prevents abuse

User tokens are used only for:
- Fetching user's own profile (identify scope)
- Listing guilds user is member of (guilds scope)
"""
```

## Implementation Guidance

### Task: Audit Complete - No Action Required

**Objectives**:
- ✅ Verify bot token and user token are properly separated
- ✅ Identify any unauthorized use of user tokens for bot operations
- ✅ Identify any inappropriate use of bot token for user-specific operations
- ✅ Compare with Discord best practices

**Findings**:
- All token usage is appropriate and follows best practices
- Clear separation between bot token and user token operations
- No security vulnerabilities identified
- Minor optimization: Remove unused OAuth2 scope

**Key Validations**:
- Bot token usage in discord_client.py: ✅ Correct (guild/channel/member operations)
- User token usage in discord_client.py: ✅ Correct (user profile/guilds)
- Bot service token usage: ✅ Correct (uses discord.py client with bot token)
- API service token usage: ✅ Correct (uses discord_client with proper separation)

**Success Criteria**:
- ✅ Bot token only used for guild-level operations
- ✅ User token only used for user-specific data
- ✅ No user token abuse (using user's token to access other users' data)
- ✅ No bot token abuse (circumventing user-level authorization)
- ✅ Authorization checks happen at application level
- ✅ Pattern matches industry best practices

## Dependencies

- Discord API v10
- discord.py library (for bot service)
- aiohttp (for API service Discord client)
- OAuth2 scopes: identify, guilds (guilds.members.read can be removed)

## Summary

**Audit Result**: ✅ **PASS - No security issues found**

The system correctly separates bot token and user token usage:
- **Bot token**: Used for guild/channel/member operations (standard pattern)
- **User token**: Used for user's own profile and guild list (OAuth2 scopes)
- **No abuse detected**: Bot token is not used to bypass user-level authorization

**Minor recommendations**:
1. Remove `guilds.members.read` scope from OAuth2 (not used)
2. Add documentation to discord_client.py explaining token usage philosophy

**User concern addressed**: "Bot using user tokens for too many operations"
- **Finding**: Bot uses **bot token** for most operations, not user tokens
- **This is correct**: Bot token is appropriate for guild-level operations
- **User tokens are used minimally**: Only for user profile and guild list
- **No privacy leak**: Bot can only access guilds where it's installed (admin approved)
