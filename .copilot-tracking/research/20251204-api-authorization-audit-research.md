<!-- markdownlint-disable-file -->
# Task Research Notes: REST API Authorization Audit

## Research Executed

### File Analysis
- services/api/routes/*.py
  - Analyzed all API route files (auth.py, guilds.py, channels.py, templates.py, games.py, export.py)
  - Identified authorization patterns using FastAPI Depends()
  - Documented permission checks for each endpoint
- services/api/dependencies/auth.py
  - get_current_user() - Base authentication dependency checking session_token cookie
- services/api/dependencies/permissions.py
  - require_manage_guild() - Requires MANAGE_GUILD Discord permission
  - require_manage_channels() - Requires MANAGE_CHANNELS Discord permission
  - require_game_host() - Template-based host permission with inheritance
  - can_manage_game() - Checks if user is game host or bot manager
  - can_export_game() - Checks if user is host, participant, or bot manager
- services/api/auth/roles.py
  - RoleVerificationService.has_permissions() - Discord permission checks via OAuth2
  - RoleVerificationService.check_bot_manager_permission() - Bot manager role verification
  - RoleVerificationService.check_game_host_permission() - Template host role verification

### Code Search Results
- "Depends\(" pattern search
  - 93 matches across API routes
  - Identified all dependency injection patterns
  - Documented which endpoints use which authorization dependencies
- "@router\." pattern search
  - 20+ endpoint definitions across 6 route files
  - Catalogued all HTTP methods and paths
  - Mapped authorization requirements to each endpoint

### External Research
- Discord API Documentation (discord.com/developers/docs)
  - MANAGE_GUILD permission (0x0000000000000020)
  - MANAGE_CHANNELS permission (0x0000000000000010)
  - ADMINISTRATOR permission (0x0000000000000008) - grants all permissions

### Project Conventions
- Standards referenced: Python coding guidelines, FastAPI dependency injection patterns
- Instructions followed: Security best practices, principle of least privilege
- Recent fix: services/api/services/games.py create_game() authorization bug discovered during UI cleanup
  - Missing template role restriction check
  - Fixed to use check_game_host_permission with template.allowed_host_role_ids

## Key Discoveries

### Authorization Architecture

The API uses a three-tier authorization model:

1. **Authentication** (services/api/dependencies/auth.py)
   - `get_current_user()` - Validates session_token HTTPOnly cookie
   - Returns CurrentUser with user model, access_token, and session_token
   - Used by ALL protected endpoints

2. **Permission Dependencies** (services/api/dependencies/permissions.py)
   - FastAPI Depends() injection for declarative authorization
   - Wraps Discord permission checks and role verifications
   - Provides reusable authorization logic across routes

3. **Role Service** (services/api/auth/roles.py)
   - RoleVerificationService - Centralized permission verification
   - Caches user roles in Redis for performance
   - Queries Discord API for up-to-date permissions
   - Handles template-based role restrictions

### Complete Endpoint Authorization Matrix

#### Authentication Endpoints (/api/v1/auth)
| Endpoint | Method | Authorization | Notes |
|----------|--------|---------------|-------|
| /login | GET | Public | Initiates OAuth2 flow |
| /callback | GET | Public | Completes OAuth2 flow |
| /refresh | POST | get_current_user | Refreshes access token |
| /logout | POST | get_current_user | Clears session |
| /user | GET | get_current_user | Returns user info and guilds |

**Analysis**: Appropriately public OAuth2 endpoints with protected session management.

#### Guild Endpoints (/api/v1/guilds)
| Endpoint | Method | Authorization | Notes |
|----------|--------|---------------|-------|
| / | GET | get_current_user | Lists user's guilds |
| /{guild_id} | GET | get_current_user | Basic guild info |
| /{guild_id}/config | GET | require_manage_guild | ⚠️ Sensitive config data |
| / | POST | require_manage_guild | Creates guild config |
| /{guild_id} | PUT | require_manage_guild | Updates guild config |
| /{guild_id}/channels | GET | get_current_user | Lists guild channels |
| /{guild_id}/roles | GET | get_current_user | Lists guild roles |
| /sync | POST | get_current_user | Syncs user's guilds |
| /{guild_id}/validate-mention | POST | get_current_user | Validates @mention |

**Analysis**: 
- ✅ Configuration endpoints properly require MANAGE_GUILD permission
- ✅ Read-only endpoints verify guild membership via Discord API
- ✅ Sync operation only affects user's own guilds

#### Channel Endpoints (/api/v1/channels)
| Endpoint | Method | Authorization | Notes |
|----------|--------|---------------|-------|
| /{channel_id} | GET | get_current_user | Channel details |
| / | POST | require_manage_channels | Creates channel config |
| /{channel_id} | PUT | require_manage_channels | Updates channel config |

**Analysis**:
- ✅ Configuration changes require MANAGE_CHANNELS permission
- ✅ Read access verified via guild membership check
- ℹ️ Channel IDs are database UUIDs, resolved to Discord IDs for permission checks

#### Template Endpoints (/api/v1/templates, /api/v1/guilds/{guild_id}/templates)
| Endpoint | Method | Authorization | Permission Check | Notes |
|----------|--------|---------------|------------------|-------|
| /guilds/{guild_id}/templates | GET | get_current_user | ✅ Role-based filtering | Returns only templates user can access |
| /templates/{template_id} | GET | get_current_user | ⚠️ NO PERMISSION CHECK | **SECURITY ISSUE** |
| /guilds/{guild_id}/templates | POST | get_current_user | ✅ check_bot_manager_permission | Requires bot manager role |
| /templates/{template_id} | PUT | get_current_user | ✅ check_bot_manager_permission | Requires bot manager role |
| /templates/{template_id} | DELETE | get_current_user | ✅ check_bot_manager_permission | Requires bot manager role |
| /templates/{template_id}/set-default | POST | get_current_user | ✅ check_bot_manager_permission | Requires bot manager role |
| /templates/reorder | POST | get_current_user | ✅ check_bot_manager_permission | Requires bot manager role |

**Analysis**:
- ⚠️ **CRITICAL**: GET /templates/{template_id} missing permission check
  - Any authenticated user can view any template by ID
  - Should verify user has access via guild membership or template role restrictions
  - Exposes template configuration including role IDs

#### Game Endpoints (/api/v1/games)
| Endpoint | Method | Authorization | Permission Check | Notes |
|----------|--------|---------------|------------------|-------|
| / | POST | get_current_user | ✅ check_game_host_permission | Recently fixed in UI cleanup |
| / | GET | get_current_user | ⚠️ NO FILTERING | Lists all games |
| /{game_id} | GET | get_current_user | ⚠️ NO PERMISSION CHECK | **SECURITY ISSUE** |
| /{game_id} | PUT | get_current_user | ✅ can_manage_game | Host or bot manager |
| /{game_id} | DELETE | get_current_user | ✅ can_manage_game | Host or bot manager |
| /{game_id}/join | POST | get_current_user | ⚠️ NO ROLE CHECK | **SECURITY ISSUE** |
| /{game_id}/leave | POST | get_current_user | ✅ Self-service | OK |

**Analysis**:
- ⚠️ **CRITICAL**: GET /games?guild_id=X returns ALL games regardless of template restrictions
  - Should filter by allowed_player_role_ids from template
  - Currently exposes games user shouldn't see
- ⚠️ **CRITICAL**: GET /games/{game_id} missing permission check
  - Any authenticated user can view any game
  - Should verify user has access via guild membership or player role restrictions
- ⚠️ **CRITICAL**: POST /games/{game_id}/join missing role verification
  - Doesn't check template.allowed_player_role_ids
  - Users can join games they're not authorized for
  - Game creation properly checks host roles but join doesn't check player roles
- ✅ Create game properly checks check_game_host_permission with template restrictions
- ✅ Update/delete properly verify host or bot manager

#### Export Endpoints (/api/v1/export)
| Endpoint | Method | Authorization | Permission Check | Notes |
|----------|--------|---------------|------------------|-------|
| /game/{game_id} | GET | get_current_user | ✅ can_export_game | Host, participant, or bot manager |

**Analysis**:
- ✅ Properly verifies user is host, participant, or bot manager
- ✅ Uses centralized permission helper

#### Health Endpoint
| Endpoint | Method | Authorization | Notes |
|----------|--------|---------------|-------|
| /health | GET | Public | Monitoring endpoint |

**Analysis**: ✅ Appropriately public for health checks

### Security Issues Discovered

#### 1. Template Visibility - CRITICAL
**File**: services/api/routes/templates.py
**Endpoint**: GET /api/v1/templates/{template_id}
**Issue**: No permission check - any authenticated user can view any template
**Impact**: 
- Exposes template configuration to unauthorized users
- Reveals role IDs configured for templates
- Information disclosure of guild configuration
- Allows discovery of guilds user isn't member of
**Recommendation**: Add guild membership verification, return 404 if not member

#### 2. Game List Filtering - CRITICAL
**File**: services/api/routes/games.py
**Endpoint**: GET /api/v1/games
**Issue**: Returns all games without filtering by guild membership or template player role restrictions
**Impact**:
- Users see games in guilds they're not members of
- Information disclosure of scheduled games across all guilds
- Reveals existence of guilds user doesn't belong to
- UI shows games user cannot access or join
**Recommendation**: Filter by guild membership first, then template.allowed_player_role_ids
#### 3. Game Detail Visibility - CRITICAL
**File**: services/api/routes/games.py
**Endpoint**: GET /api/v1/games/{game_id}
**Issue**: No permission check - any authenticated user can view any game
**Impact**:
- Exposes game details including participant list
- Reveals Discord user IDs and guild information
- Allows discovery of guilds user isn't member of
- Information disclosure vulnerability
**Recommendation**: Verify guild membership first, return 404 if not member (not 403)
**Recommendation**: Verify user has access via guild membership or player role restrictions
#### 4. Game Join Authorization - CRITICAL
**File**: services/api/routes/games.py
**Endpoint**: POST /api/v1/games/{game_id}/join
**Issue**: Doesn't verify guild membership or required player roles from template
**Impact**:
- Users could join games in guilds they're not members of
- Bypasses template role restrictions
- Authorization bypass vulnerability
- Potential for joining games in unknown guilds
**Recommendation**: Verify guild membership first, then template.allowed_player_role_ids
**Recommendation**: Add check against template.allowed_player_role_ids

### Authorization Patterns Observed

#### Correct Pattern - Guild Configuration
```python
@router.get("/{guild_id}/config")
async def get_guild_config(
    guild_id: str,
    current_user: CurrentUser = Depends(permissions.require_manage_guild),
    db: AsyncSession = Depends(database.get_db),
):
```
Uses FastAPI Depends() for declarative authorization before endpoint executes.

#### Correct Pattern - Template Management
```python
@router.post("/guilds/{guild_id}/templates")
async def create_template(
    guild_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    # Check bot manager permission in endpoint
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="Bot manager role required")
```
Imperative check within endpoint for complex authorization logic.

#### Incorrect Pattern - Missing Authorization
```python
@router.get("/{game_id}")
async def get_game(
    game_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    game_service: GameService = Depends(_get_game_service),
):
    game = await game_service.get_game(game_id)
    # ⚠️ No permission check - any authenticated user can view
    return await _build_game_response(game)
```
Only authenticates user, doesn't verify authorization to access resource.

### Recent Authorization Fix

During UI cleanup task, authorization bug was fixed in services/api/services/games.py:

**Before**: create_game() didn't properly check template role restrictions
**After**: Added proper check_game_host_permission call with template.allowed_host_role_ids
**Impact**: Game creation now properly enforces template-specific host role requirements

This fix demonstrates the importance of this audit - similar issues exist in other endpoints.

## Recommended Approach

**Comprehensive Authorization Remediation with Defense in Depth**

### Priority 1: Critical Security Fixes (Immediate)

Fix all 4 critical endpoints directly in route files without helper functions:

1. **Template Detail Endpoint** (services/api/routes/templates.py)
   - GET /templates/{template_id}: Add guild membership verification
   - Fetch template, check user is member of template's guild via Discord API
   - Return 404 (not 403) if user not in guild to avoid information disclosure

2. **Game List Filtering** (services/api/routes/games.py)
   - GET /games: Filter results by template role restrictions
   - Only return games where user meets template.allowed_player_role_ids
   - Avoid exposing existence of games in guilds user isn't member of

3. **Game Detail Endpoint** (services/api/routes/games.py)
   - GET /games/{game_id}: Add permission check
   - Verify user is guild member and meets player role requirements
   - Return 404 (not 403) if user not in guild to avoid information disclosure

4. **Game Join Authorization** (services/api/routes/games.py)
   - POST /games/{game_id}/join: Add role verification
   - Check template.allowed_player_role_ids before allowing join
   - Return 404 if game not found or user not in guild

**Information Disclosure Prevention**:
- Use 404 errors instead of 403 for resources in guilds user doesn't belong to
- Never reveal existence of guilds, templates, or games to non-members
- Filter list endpoints to only show resources user is authorized to see

### Priority 2: Centralize Existing Authorization Patterns

**Current Issue**: Route-specific authorization code duplicated across endpoints

**Template Routes** (services/api/routes/templates.py) - 6 endpoints with duplicated code:
```python
# Repeated in: create_template, update_template, delete_template, 
# set_default_template, reorder_templates, list_templates (admin check)
role_service = roles_module.get_role_service()
has_permission = await role_service.check_bot_manager_permission(
    current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
)
if not has_permission:
    raise HTTPException(status_code=403, detail="Bot manager role required...")
```

**Solution**: Create `require_bot_manager` dependency in services/api/dependencies/permissions.py
- Similar to existing require_manage_guild and require_manage_channels
- Accepts guild_id parameter (can be from path or fetched from resource)
- Returns CurrentUser if authorized, raises HTTPException if not
- Eliminates 30+ lines of duplicated authorization code

**Benefit**: Consistent authorization logic, easier to audit, prevents authorization bugs

### Priority 3: Information Leak Audit

Review all endpoints for guild membership information leaks:

1. **Guild Endpoints** - Verify all return 404 for non-member access
2. **Channel Endpoints** - Verify guild membership before exposing channel data
3. **Template Endpoints** - Already filtered by list endpoint, verify detail endpoint
4. **Game Endpoints** - Filter all responses to user's guilds only

### Priority 4: Authorization Helpers (Optional Refactoring)

After critical fixes are proven, optionally create helpers for common patterns:
1. **can_view_template()** - Verify guild membership for template access
2. **can_view_game()** - Verify guild membership and player role requirements
3. **can_join_game()** - Verify player role requirements from template

### Priority 5: Prevention & Documentation

1. Document authorization patterns in .github/instructions/
2. Create authorization checklist for new endpoints
3. Add authorization tests for all endpoints
4. Consider middleware for resource-level authorization

### Implementation Strategy

**Phase 1: Critical Fixes (Immediate)**
- Fix 4 critical endpoints directly in route files
- Add 404 responses for non-member access to prevent information disclosure
- Filter all list endpoints by user's guild membership
- Add integration tests verifying authorization enforcement
- Deploy fixes to production

**Phase 2: Centralize Authorization (Immediate Follow-up)**
- Create require_bot_manager dependency
- Refactor template routes to use dependency
- Eliminate duplicated authorization code
- Verify no behavior changes (tests still pass)

**Phase 3: Information Leak Audit (Follow-up)**
- Systematically review all endpoints for guild membership checks
- Verify 404 vs 403 response codes are used correctly
- Test that non-members cannot discover guild/resource existence
- Add negative authorization tests (user should NOT see resource)

**Phase 4: Optional Additional Helpers**
- After fixes proven stable, evaluate if more helpers needed
- Create authorization helper functions if new duplication patterns emerge
- Refactor endpoints to use helpers while maintaining security
- Add comprehensive test coverage

**Phase 5: Documentation & Prevention**
- Document authorization patterns and rationale (404 vs 403)
- Create authorization checklist for new endpoints
- Add pre-commit authorization checks
- Security review process for new endpoints
### Additional Security Consideration: 404 vs 403

**Critical Pattern**: Use 404 (Not Found) instead of 403 (Forbidden) when:
- User is not a member of the guild containing the resource
- Resource exists but user shouldn't know it exists

**Why**: 403 reveals resource existence to unauthorized users. 404 prevents information leakage.

**Examples**:
- User requests game in guild they don't belong to → 404 (not 403)
- User requests template in guild they don't belong to → 404 (not 403)
- User is guild member but lacks role to modify → 403 (appropriate)

**Current Issue**: Many endpoints would return 403, revealing guild/resource existence.

### Middleware for Authorization - Not Recommended

**Question**: Could authorization be moved to middleware instead of dependencies?

**Answer**: No, this would be a poor architectural choice for several reasons:

**1. Resource-Specific Authorization**
- Authorization depends on the specific resource being accessed (game_id, template_id, guild_id)
- Middleware runs before route matching, so resource IDs aren't available yet
- Would need to parse URL path manually and duplicate routing logic

**2. Complex Permission Logic**
- Different endpoints require different permission checks:
  - GET /games/{game_id} → Check guild membership + player roles
  - PUT /games/{game_id} → Check if host or bot manager
  - POST /templates → Check bot manager role
  - GET /guilds/{guild_id}/config → Check MANAGE_GUILD permission
- Middleware would need a massive routing table mapping paths to authorization rules

**3. Breaks FastAPI Design Patterns**
- FastAPI dependencies are designed for exactly this use case
- Dependencies are composable, testable, and declarative
- Dependencies can access path parameters, request body, database connections
- Middleware is for cross-cutting concerns (logging, CORS, timing), not resource authorization

**4. Loss of Type Safety and Documentation**
- Dependencies appear in OpenAPI documentation
- Type hints and validation work automatically
- Middleware is opaque to API documentation

**5. Database Access Complexity**
- Authorization often requires database lookups (fetch game, fetch template, check guild)
- Middleware would need to duplicate database session management
- Dependencies already have clean database access via Depends(get_db)

**Example of Why It Doesn't Work**:
```python
# Middleware can't do this - path params not available yet
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    game_id = ???  # Not available - route not matched yet
    game = await db.query(Game).get(game_id)  # Where does db come from?
    if game.guild_id not in user_guilds:  # How do we know user_guilds?
        return Response(status_code=404)
```

**Current Approach is Correct**:
- Use `get_current_user` dependency for authentication (all protected endpoints)
- Use specific permission dependencies for declarative authorization (require_manage_guild)
- Use imperative checks in route handlers for complex resource-specific logic
- This is the FastAPI recommended pattern and works well

**Recommendation**: Keep dependency-based authorization. Focus on:
1. Fixing missing authorization checks (4 critical endpoints)
2. Creating require_bot_manager dependency to eliminate duplication
3. Ensuring consistent 404 vs 403 usage
4. Adding comprehensive authorization tests

Middleware is appropriate for the existing AuthorizationMiddleware (logging) but not for resource-level authorization decisions.

## Implementation Guidance

- **Objectives**: 
  1. Enforce proper authorization on all API endpoints
  2. Prevent unauthorized access to resources
  3. Prevent information disclosure about guilds user isn't member of
  4. Use appropriate HTTP status codes (404 vs 403)
- **Key Tasks**: 
  1. Add guild membership check to template detail endpoint (return 404 if not member)
  2. Filter game list by guild membership AND player role restrictions
  3. Add guild membership check to game detail endpoint (return 404 if not member)
  4. Verify guild membership and player roles in game join endpoint
  5. Create require_bot_manager dependency to centralize template authorization
  6. Refactor 6 template endpoints to use require_bot_manager dependency
  7. Audit all endpoints for information leakage
  8. Add comprehensive authorization tests including negative tests
- **Dependencies**: 
  - RoleVerificationService for role checks
  - Discord API (via oauth2.get_user_guilds) for guild membership verification
  - Template model for role restriction data
  - Proper HTTP status code usage (404 vs 403)
- **Success Criteria**: 
  - All endpoints enforce proper authorization
  - No information disclosure vulnerabilities
  - Users cannot discover existence of guilds they don't belong to
  - 404 used appropriately to prevent information leakage
  - Authorization tests pass (both positive and negative cases)
  - No unauthorized access possible via API
  - No unauthorized access possible via API
