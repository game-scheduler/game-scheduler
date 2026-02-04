<!-- markdownlint-disable-file -->
# Task Research Notes: Staging Session Cookie Authentication Failure

## Research Executed

### File Analysis
- services/api/routes/auth.py (lines 120-145)
  - OAuth callback sets `session_token` cookie after successful Discord authentication
  - Cookie configuration: `httponly=True`, `secure=is_production` (based on environment), `samesite="lax"`, `max_age=86400`
  - `secure` flag only enabled when `config.environment == "production"`, disabled for development

- services/api/dependencies/auth.py (lines 1-80)
  - `get_current_user` dependency extracts `session_token` from Cookie
  - Validation error occurs here when cookie not present

- services/api/config.py (lines 1-60)
  - `environment` field determines cookie `secure` flag behavior
  - Defaults to "development" if `ENVIRONMENT` variable not set

- services/api/middleware/cors.py (lines 1-60)
  - CORS configured with `allow_credentials=True` (required for cookie transmission)
  - Allowed origins includes `config.frontend_url` + localhost variants
  - Cannot use wildcard with credentials enabled

- frontend/src/api/client.ts (lines 1-50)
  - Axios client configured with `withCredentials: true`
  - Uses runtime config `BACKEND_URL` from `/config.js` or fallback to `VITE_BACKEND_URL`

- docker/frontend-entrypoint.sh
  - Generates `/config.js` from `BACKEND_URL` environment variable at runtime
  - Frontend uses this for API base URL

- config/env.staging (lines 1-200)
  - `ENVIRONMENT=staging`
  - `FRONTEND_URL=https://staging.mydomain.com`
  - `BACKEND_URL=https://staging.mydomain.com`

### Code Search Results
- `session_token cookie` searches
  - Cookie set in OAuth callback endpoint: `response.set_cookie(key="session_token", ...)`
  - Cookie deleted on logout: `response.delete_cookie(key="session_token", samesite="lax")`
  - Cookie validated in `get_current_user` dependency via FastAPI Cookie parameter

- `secure cookie` searches
  - `secure` flag controlled by `is_production = config.environment == "production"`
  - Development and staging environments run with `secure=False`
  - Production environment runs with `secure=True`

- CORS configuration searches
  - `allow_credentials=True` required for cookie transmission
  - Specific origins configured (no wildcard allowed with credentials)
  - CORS middleware properly configured for cookie-based auth

### Network Trace Analysis
- **Actual staging URLs confirmed**:
  - Frontend: `https://staging.game-scheduler.daddog.com`
  - API: `https://api.staging.game-scheduler.daddog.com`
  - Different subdomains require explicit cookie domain configuration

- **Request headers** (from failing `/api/v1/auth/user` call):
  - NO `Cookie:` header present (browser not sending session cookie)
  - `Origin: https://staging.game-scheduler.daddog.com`
  - `Referer: https://staging.game-scheduler.daddog.com/`

- **Response headers**:
  - `Access-Control-Allow-Credentials: true` ✓
  - `Access-Control-Allow-Origin: https://staging.game-scheduler.daddog.com` ✓
  - CORS configured correctly but cookie not being sent

- **Deployment architecture**:
  - User → HTTPS → nginx reverse proxy
  - Nginx → HTTP → backend services
  - Cookie set by backend (HTTP) but user sees HTTPS
  - Requires `secure=True` because user's connection is HTTPS

### External Research
- #fetch:https://fastapi.tiangolo.com/tutorial/cookie-params/
  - FastAPI Cookie parameters validated via Pydantic
  - Missing required cookies return 422 validation error with field details

- #fetch:https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
  - Cookies with `Secure` flag only sent over HTTPS connections
  - `SameSite=lax` allows cookies on top-level navigation but blocks cross-site requests
  - Cookies with `Secure` flag will NOT be set by browser if received over HTTP

### Project Conventions
- Standards referenced: Self-explanatory code commenting, FastAPI transaction patterns
- Cookie security: HTTPOnly + Secure (production) + SameSite=lax pattern established in initial implementation
- Environment-based configuration: Use `ENVIRONMENT` variable to control behavior differences

## Key Discoveries

### Cookie Secure Flag Behavior

**Critical Finding**: The `secure` flag is ONLY enabled when `config.environment == "production"`:

```python
# services/api/routes/auth.py
config = get_api_config()
is_production = config.environment == "production"

response.set_cookie(
    key="session_token",
    value=session_token,
    httponly=True,
    secure=is_production,  # False for staging!
    samesite="lax",
    max_age=86400,
)
```

### Environment Variable Configuration

```python
# services/api/config.py
self.environment = os.getenv("ENVIRONMENT", "development")
```

From `config/env.staging`:
```bash
ENVIRONMENT=staging
```

Since `environment == "staging"` not `"production"`, the `secure` flag will be `False`.

### Cookie Secure Flag Behavior (Clarification)

**Important**: The `secure=False` flag is NOT causing this issue!

**Browser Behavior with Secure Flag**:
- `secure=True`: Cookie ONLY sent over HTTPS connections
- `secure=False`: Cookie sent over BOTH HTTP and HTTPS connections

**Current Staging Setup**:
- Backend sets cookie with `secure=False`
- Reverse proxy forwards Set-Cookie header to user over HTTPS
- Browser receives and stores cookie successfully
- **Cookie with `secure=False` WILL be sent over HTTPS** (it just also allows HTTP)

**Why secure=False has worked fine**: Browsers accept and send cookies with `secure=False` over HTTPS without issue. The `secure=False` setting is more permissive (allows both HTTP and HTTPS), not restrictive.

### Potential Root Causes

#### 1. Cross-Subdomain Cookie Scope (PRIMARY ISSUE)

**This is the actual problem**: Cookie set without explicit `domain` parameter.

When API at `api.staging.game-scheduler.daddog.com` sets cookie:
- Without `domain` parameter: Cookie scoped to `api.staging.game-scheduler.daddog.com` ONLY
- Browser will NOT send cookie when frontend at `staging.game-scheduler.daddog.com` makes requests
- Different subdomains = different cookie scopes = cookie not shared

**Evidence**: Network trace shows NO `Cookie:` header in request from frontend to API.

#### 2. CORS Configuration Mismatch (VERIFY)

Check that `FRONTEND_URL` in staging matches actual frontend domain:
```bash
# Should be:
FRONTEND_URL=https://staging.game-scheduler.daddog.com

# Not:
FRONTEND_URL=https://staging.mydomain.com  # Wrong domain!
```

If CORS origin doesn't match, browser blocks credential transmission.

### CORS Configuration Validation

CORS properly configured for cookie transmission:
```python
# services/api/middleware/cors.py
origins = [
    config.frontend_url,  # https://staging.mydomain.com
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # ✓ Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### OAuth Callback Flow

1. User redirects to Discord OAuth (`/api/v1/auth/login`)
2. Discord redirects back to `/api/v1/auth/callback?code=XXX`
3. API exchanges code for tokens
4. API stores tokens in Redis with session UUID
5. API sets `session_token` cookie on response
6. Frontend redirects to dashboard
7. Frontend makes `/api/v1/auth/me` request
8. **Cookie should be included** via `withCredentials: true`

If cookie not included → validation error on step 8.

## Actual Deployment Architecture (CRITICAL UPDATE)

### Confirmed Setup from Network Trace

**Frontend**: `https://staging.game-scheduler.daddog.com`
**API**: `https://api.staging.game-scheduler.daddog.com`

**Key Observations**:
1. **Different subdomains**: Frontend and API are on separate subdomains
2. **No Cookie header in request**: Browser is NOT sending the session cookie
3. **Reverse proxy architecture**:
   - User → HTTPS → nginx reverse proxy
   - Nginx → HTTP → backend services
   - Cookie set by backend over HTTP but received by user over HTTPS
4. **CORS working correctly**: `Access-Control-Allow-Credentials: true` and proper origin headers present

### Root Cause Identified

**Cross-Subdomain Cookie Issue**: When a cookie is set without an explicit `domain` parameter, it's scoped to the exact hostname that set it. In this case:
- Cookie set by: `api.staging.game-scheduler.daddog.com`
- Cookie scoped to: `api.staging.game-scheduler.daddog.com` only
- Frontend on: `staging.game-scheduler.daddog.com`
- Result: Browser does NOT send cookie because domains don't match

**Browser Cookie Behavior**:
- Cookie without `domain`: Only sent to exact hostname
- Cookie with `domain=.game-scheduler.daddog.com`: Sent to all subdomains of `game-scheduler.daddog.com`

## Recommended Approach

### Phase 1: Configure Cookie Domain for Subdomain Sharing (PRIMARY FIX)

**Problem**: Cookie set by `api.staging.game-scheduler.daddog.com` not accessible to frontend on `staging.game-scheduler.daddog.com`.

**Solution**: Add explicit domain parameter with leading dot:

```python
# services/api/config.py - Add cookie domain configuration
self.cookie_domain = os.getenv("COOKIE_DOMAIN", None)

# services/api/routes/auth.py - OAuth callback
config = get_api_config()

response.set_cookie(
    key="session_token",
    value=session_token,
    httponly=True,
    secure=False,  # Keep as-is for now (not the issue)
    samesite="lax",
    max_age=86400,
    domain=config.cookie_domain,  # CRITICAL FIX: enables subdomain sharing
)
```

**Environment Configuration** (`config/env.staging`):
```bash
# Cookie domain for subdomain sharing (leading dot is critical)
COOKIE_DOMAIN=.game-scheduler.daddog.com
```

**Rationale**:
- Leading dot (`.game-scheduler.daddog.com`) makes cookie available to all subdomains
- Cookie will be sent from `staging.game-scheduler.daddog.com` to `api.staging.game-scheduler.daddog.com`
- `secure=False` is FINE - not causing the issue (cookies with secure=False work over HTTPS)
- `httponly=True` maintains security (no JavaScript access)
- `samesite="lax"` prevents CSRF while allowing navigation

**Note on Secure Flag**: While setting `secure=True` for HTTPS deployments is a security best practice, it's NOT required to fix this issue. The `secure=False` setting has been working fine for you because browsers will send cookies with `secure=False` over HTTPS without problem. You can optionally change it later, but the domain fix is the critical change.

### Phase 2: Update Logout Endpoint for Consistency

**Solution**: Apply same cookie configuration to logout:

```python
# services/api/routes/auth.py - Logout endpoint
@router.post("/logout")
async def logout(response: Response, current_user: CurrentUser = Depends(get_current_user)):
    await tokens.delete_user_tokens(current_user.session_token)

    config = get_api_config()
    response.delete_cookie(
        key="session_token",
        samesite="lax",
        domain=config.cookie_domain,  # Must match set_cookie domain
    )
    return {"success": True}
```

### Phase 3: CORS Origin Configuration

**Current CORS setup** already allows the frontend origin:
```python
# services/api/middleware/cors.py
origins = [
    config.frontend_url,  # Must be https://staging.game-scheduler.daddog.com
    "http://localhost:3000",
    "http://localhost:3001",
]
```

**Verify** `config/env.staging` has correct frontend URL:
```bash
FRONTEND_URL=https://staging.game-scheduler.daddog.com
BACKEND_URL=https://api.staging.game-scheduler.daddog.com
```

### Phase 4: Add Debugging and Validation

**Add comprehensive logging**:

```python
# services/api/routes/auth.py (after setting cookie)
config = get_api_config()
logger.info(
    "Set session cookie for user %s: secure=%s, domain=%s, frontend=%s",
    discord_id,
    config.environment in ("production", "staging"),
    config.cookie_domain or "(none - scoped to exact hostname)",
    config.frontend_url,
)

# services/api/dependencies/auth.py (enhanced debugging)
from fastapi import Request

async def get_current_user(
    request: Request,
    session_token: str = Cookie(None),  # Make optional for debugging
    db: AsyncSession = _db_dependency,
) -> CurrentUser:
    all_cookies = request.cookies

    if not session_token:
        logger.error(
            "Missing session_token cookie. Request from %s. Available cookies: %s. Headers: Origin=%s, Referer=%s",
            request.client.host,
            list(all_cookies.keys()),
            request.headers.get("origin"),
            request.headers.get("referer"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no session cookie",
        )

    # ... rest of function
```

### Phase 5: Verification Steps

**After deploying changes**:

1. **Check cookie set in OAuth callback**:
   - Open browser DevTools → Application/Storage → Cookies
   - Complete OAuth flow
   - Verify cookie properties:
     - Name: `session_token`
     - Domain: `.game-scheduler.daddog.com` (with leading dot)
     - Secure: ✓ (checked)
     - HttpOnly: ✓ (checked)
     - SameSite: Lax

2. **Verify cookie sent in API requests**:
   - DevTools → Network tab
   - Make request to `/api/v1/auth/user`
   - Check Request Headers for `Cookie: session_token=...`

3. **Check API logs**:
   - Look for "Set session cookie" message with domain info
   - Verify no "Missing session_token cookie" errors

## Alternative Solutions (If Primary Fix Doesn't Work)

### Option A: Same-Domain Architecture

Deploy both frontend and API on same domain:
- Frontend: `https://staging.game-scheduler.daddog.com/`
- API: `https://staging.game-scheduler.daddog.com/api/`

No cookie domain configuration needed (same origin).

### Option B: Use API Subdomain as Primary

Serve everything from API subdomain:
- Frontend: `https://api.staging.game-scheduler.daddog.com/`
- API: `https://api.staging.game-scheduler.daddog.com/api/`

Cookie automatically shared (same hostname).

## Implementation Guidance

- **Objectives**:
  - Enable cross-subdomain cookie sharing between `staging.game-scheduler.daddog.com` and `api.staging.game-scheduler.daddog.com`
  - Set secure flag for HTTPS deployments (staging and production)
  - Maintain development experience (localhost HTTP, no domain)

- **Key Tasks**:
  1. Add `cookie_domain` configuration to APIConfig
  2. Modify cookie setting in OAuth callback to include domain parameter
  3. Modify cookie deletion in logout to include domain parameter
  4. Configure `COOKIE_DOMAIN` in staging environment file
  5. Verify `FRONTEND_URL` matches actual frontend domain
  6. Add comprehensive logging for debugging
  7. Test OAuth flow and verify cookie transmission

- **Dependencies**:
  - Environment variable: `COOKIE_DOMAIN`
  - Files to modify:
    - `services/api/config.py`
    - `services/api/routes/auth.py` (2 locations: callback + logout)
    - `services/api/dependencies/auth.py` (enhanced logging)
    - `config/env.staging`

- **Success Criteria**:
  - OAuth callback sets cookie with correct domain
  - Browser sends cookie with requests to API subdomain
  - No 422 validation errors for missing `session_token`
  - Cookie visible in DevTools with domain `.game-scheduler.daddog.com`
  - API logs show cookie received in requests
