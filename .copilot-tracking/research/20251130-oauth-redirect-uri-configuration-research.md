<!-- markdownlint-disable-file -->
# Task Research Notes: OAuth Redirect URI Configuration Issue

## Research Executed

### File Analysis
- `.env`
  - Contains `DISCORD_REDIRECT_URI=http://172.16.1.24:8000/api/v1/auth/callback`
  - Contains `FRONTEND_URL=http://172.16.1.24:3000`
  - Contains `API_URL=http://172.16.1.24:8000`
  - All URLs use internal NAT address and HTTP protocol

- `frontend/src/pages/LoginPage.tsx`
  - Constructs redirect_uri from `window.location.origin`: `const REDIRECT_URI = ${window.location.origin}/auth/callback`
  - This correctly uses the browser's current URL (public HTTPS URL)
  - Passes this to API via query parameter

- `services/api/routes/auth.py`
  - `/api/v1/auth/login` endpoint receives `redirect_uri` as query parameter
  - Passes it to `oauth2.generate_authorization_url(redirect_uri)`
  - Does NOT use any configuration values for redirect_uri

- `services/api/auth/oauth2.py`
  - `generate_authorization_url()` receives redirect_uri from frontend
  - Uses received redirect_uri in Discord OAuth params
  - Does NOT override with config values

- `docker-compose.base.yml`
  - API container exposes port mapping: `"${API_HOST_PORT:-8000}:8000"`
  - API container has environment: `API_URL: ${API_URL:-http://localhost:8000}`
  - Frontend container has environment: `API_URL: ${API_URL:-}`

- `frontend/src/api/client.ts`
  - Uses `window.__RUNTIME_CONFIG__?.API_URL` for API base URL
  - This comes from `/config.js` generated at container startup

- `docker/frontend-entrypoint.sh`
  - Generates `/usr/share/nginx/html/config.js` using `API_URL` env var
  - Template: `window.__RUNTIME_CONFIG__ = { API_URL: '${API_URL}' };`

### Code Search Results
- `API_URL` in docker-compose
  - Frontend build arg: `VITE_API_URL: ${API_URL}`
  - Frontend runtime env: `API_URL: ${API_URL:-}`
  - API container env: `API_URL: ${API_URL:-http://localhost:8000}`

- `DISCORD_REDIRECT_URI` usage
  - Only used in bot service environment
  - NOT used by API service

### External Research
- N/A (Internal configuration issue)

### Project Conventions
- Standards referenced: OAuth2 flow implementation
- Instructions followed: Environment variable configuration

## Key Discoveries

### Root Cause Analysis

**The Problem**: Frontend is making API requests to internal NAT address (http://172.16.1.24:8000) instead of public HTTPS URL.

**Why This Happens**:
1. `.env` file has `API_URL=http://172.16.1.24:3000` (internal NAT address, HTTP)
2. Docker Compose passes this to frontend container as `API_URL` environment variable
3. Frontend entrypoint script generates `/config.js` with this value
4. Frontend loads config.js and sets `window.__RUNTIME_CONFIG__.API_URL = "http://172.16.1.24:8000"`
5. Frontend's `apiClient` uses this as `baseURL` for all API requests
6. When LoginPage calls `/api/v1/auth/login`, it goes to `http://172.16.1.24:8000/api/v1/auth/login`

**Why redirect_uri is Correct**:
- LoginPage correctly constructs `REDIRECT_URI = ${window.location.origin}/auth/callback`
- `window.location.origin` is the public HTTPS URL the user accessed
- This gets passed as query parameter to the API
- The API receives and uses this correct value

**The Confusion**:
- `DISCORD_REDIRECT_URI` in `.env` is NOT used by the API service
- It's only used by the bot service
- The redirect_uri that matters comes from the frontend's query parameter

### Implementation Patterns

**Current OAuth Flow**:
```typescript
// LoginPage.tsx
const REDIRECT_URI = `${window.location.origin}/auth/callback`;
// e.g., "https://game-scheduler.boneheads.us:3000/auth/callback"

await apiClient.get('/api/v1/auth/login', {
  params: { redirect_uri: REDIRECT_URI }
});
// This makes request to the API_URL configured in config.js
```

**API Client Configuration**:
```typescript
// client.ts
const API_BASE_URL = 
  window.__RUNTIME_CONFIG__?.API_URL ||  // Runtime config from container
  import.meta.env.VITE_API_URL ||        // Build-time env var
  '';                                     // Fallback (proxy mode)
```

**Runtime Config Generation**:
```bash
# frontend-entrypoint.sh
envsubst '${API_URL}' < /etc/nginx/templates/config.template.js > /usr/share/nginx/html/config.js
```

### Configuration Examples

**Current .env (WRONG)**:
```env
FRONTEND_URL=http://172.16.1.24:3000
API_URL=http://172.16.1.24:8000
DISCORD_REDIRECT_URI=http://172.16.1.24:8000/api/v1/auth/callback
```

**Required .env (CORRECT)**:
```env
FRONTEND_URL=https://game-scheduler.boneheads.us:3000
API_URL=https://game-scheduler.boneheads.us:8000
DISCORD_REDIRECT_URI=https://game-scheduler.boneheads.us:8000/api/v1/auth/callback
```

### Technical Requirements

**Environment Variables That Need Updating**:
1. `API_URL` - Must be public HTTPS URL (used by frontend to make API calls)
2. `FRONTEND_URL` - Must be public HTTPS URL (used by CORS, API redirects)
3. `DISCORD_REDIRECT_URI` - Must be public HTTPS URL (used by bot, must match Discord app config)

**Why All Three Matter**:
- `API_URL`: Frontend needs to know where to send API requests
- `FRONTEND_URL`: API needs to know allowed CORS origins
- `DISCORD_REDIRECT_URI`: Discord OAuth requires exact match with app configuration

**Port Configuration**:
- If using standard HTTPS (port 443), ports can be omitted from URLs
- If using custom ports (e.g., :3000, :8000), they must be included
- Current setup shows :3000 and :8000 in URLs, suggesting non-standard ports

## Recommended Approach

**Solution**: Update `.env` file to use public HTTPS URLs instead of internal NAT addresses.

**Step-by-Step Fix**:
1. Edit `.env` file
2. Replace all `http://172.16.1.24` references with `https://game-scheduler.boneheads.us`
3. Ensure port numbers match your reverse proxy/load balancer configuration
4. Restart containers to pick up new environment variables
5. Verify Discord Developer Portal has matching redirect URI configured

**Expected Changes**:
```diff
- FRONTEND_URL=http://172.16.1.24:3000
+ FRONTEND_URL=https://game-scheduler.boneheads.us:3000

- API_URL=http://172.16.1.24:8000
+ API_URL=https://game-scheduler.boneheads.us:8000

- DISCORD_REDIRECT_URI=http://172.16.1.24:8000/api/v1/auth/callback
+ DISCORD_REDIRECT_URI=https://game-scheduler.boneheads.us:8000/api/v1/auth/callback
```

**Important Notes**:
- If your reverse proxy/load balancer terminates SSL and forwards to containers on standard ports, you may need different port numbers or omit ports entirely
- The `DISCORD_REDIRECT_URI` must EXACTLY match what's configured in Discord Developer Portal OAuth2 settings
- After changing these values, restart all containers: `docker compose down && docker compose up -d`

## Implementation Guidance

**Objectives**:
- Fix frontend API client to use public HTTPS URL
- Fix CORS configuration to allow public frontend URL
- Ensure Discord OAuth redirect URI matches public URL

**Key Tasks**:
1. Update `.env` with public HTTPS URLs
2. Verify Discord Developer Portal redirect URI configuration
3. Restart containers to apply changes
4. Test OAuth flow from public URL

**Dependencies**:
- Valid SSL certificates for public domain
- Reverse proxy/load balancer properly configured
- DNS pointing to server's public IP
- Discord Developer Portal access to verify redirect URI

**Success Criteria**:
- Frontend loads from public HTTPS URL
- API requests go to public HTTPS URL (not internal NAT address)
- "Login with Discord" button initiates OAuth flow successfully
- Discord redirects back to public callback URL
- Authentication completes without errors
