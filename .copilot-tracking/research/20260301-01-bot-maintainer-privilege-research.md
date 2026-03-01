<!-- markdownlint-disable-file -->

# Task Research Notes: Bot Maintainer Privilege Level

## Research Executed

### File Analysis

- `services/api/routes/auth.py`
  - OAuth2 callback: `token_data` here is the raw Discord token exchange response (not Redis session). `token_data["access_token"]` at lines 100 and 122 are correct as-is — they use the fresh OAuth token to fetch user identity and create the session.
  - `get_user_info()` (line 233): same local variable `access_token` used for both `get_user_from_token()` (must stay user OAuth token) and `get_user_guilds()` (should use guild token for maintainer) — needs splitting into two variables.
  - Token refresh endpoint: operates on `refresh_token`, no guild calls, no change needed.

- `services/api/auth/tokens.py`
  - Session stored in Redis as `session:{uuid}` with fields: `user_id`, `access_token`, `refresh_token`, `expires_at`
  - `store_user_tokens()` is the single session creation point — add `can_be_maintainer` and `is_maintainer` here
  - `get_user_tokens()` returns all fields — add `can_be_maintainer` and `is_maintainer` to return dict
  - `refresh_user_tokens()` updates only `access_token` and `expires_at` — no change needed

- `services/api/dependencies/auth.py`
  - Line 84: `CurrentUser.access_token = token_data["access_token"]` — always the real user OAuth token, correct as-is

- `services/api/dependencies/permissions.py`
  - Line 104 (`verify_guild_membership`): calls `get_user_guilds(access_token)` — use `get_guild_token(token_data)`
  - Line 311 (`_require_permission`): central hub for `require_manage_guild`, `require_manage_channels`, `require_bot_manager` — short-circuit if `is_maintainer`
  - Line 447 (`get_guild_name`): calls `get_user_guilds(access_token)` for name lookup — use `get_guild_token(token_data)`
  - Line 533 (`require_game_host`): permission check — short-circuit if `is_maintainer`
  - Line 593 (`can_manage_game`): permission check — short-circuit if `is_maintainer`
  - Line 683 (`require_administrator`): permission check — short-circuit if `is_maintainer`

- `services/api/services/sse_bridge.py`
  - Line 147: checks if connected SSE client is in a guild before delivering event — use `get_guild_token(token_data)` so maintainer receives all guild events

- `shared/database.py`
  - `get_db_with_user_guilds()`: calls `oauth2.get_user_guilds(current_user.access_token, ...)` for RLS setup — use `get_guild_token()` derived from session

- `services/api/routes/guilds.py`
  - `list_guilds()`: calls `oauth2.get_user_guilds(current_user.access_token, ...)` to build guild menu — use `get_guild_token()` derived from session

- `shared/discord/client.py`
  - `DiscordAPIClient` has `bot_token`, `_get_auth_header()` auto-detects token type (2 dots → `Bot`, 1 dot → `Bearer`)
  - `_make_api_request()` accepts `cache_key` and `cache_ttl` for automatic Redis caching
  - No `get_application_info()` method exists yet

- `shared/cache/keys.py`
  - `CacheKeys.session(session_id)` → `session:{id}` — used for Redis scan in Refresh Maintainers
  - No key for `discord:app_info` yet — needs adding

- `shared/cache/ttl.py`
  - No `APP_INFO` TTL exists yet — needs adding at 3600 (1 hour)

- `frontend/src/types/index.ts` (`CurrentUser` interface, line 132)
  - Fields: `id`, `user_uuid`, `username`, `discordId?`, `discriminator?`, `avatar?`, `guilds?`
  - No maintainer fields exist yet — add `can_be_maintainer?: boolean` and `is_maintainer?: boolean`

- `frontend/src/contexts/AuthContext.tsx`
  - `AuthProvider` holds `user: CurrentUser | null` state, `loading`, `login`, `logout`, `refreshUser`
  - `refreshUser()` re-fetches `GET /api/v1/auth/user` and updates `user` state
  - Natural hook: call `refreshUser()` after toggle or refresh maintainers to propagate state change

- `frontend/src/api/client.ts`
  - Single `apiClient` axios instance with `baseURL = API_BASE_URL` (from runtime config), `withCredentials: true`
  - 401 interceptor: dispatches window event to trigger logout
  - New `maintainers.ts` module should import and use this `apiClient`

- `frontend/src/pages/GuildListPage.tsx`
  - MUI page with grid of guild cards
  - Existing pattern to follow: "Sync Servers and Channels" `Button` with `RefreshIcon` in the top `Box` alongside the page title — includes async handler with `try/catch` and `refreshUser()` on success
  - Maintainer controls live in this same `Box`, gated on `user?.can_be_maintainer`
  - MUI `Dialog` component already imported in other pages — use for Refresh Maintainers confirmation
  - Page title currently "Your Servers" — conditionally renders "All Servers (Maintainer Mode)" when `user?.is_maintainer`

### Code Search Results

- `token_data["access_token"]` — 11 real call sites (excluding research doc references)
  - 3 no-change (raw Discord exchange response or `CurrentUser` population)
  - 3 use `get_guild_token(token_data)` (guild membership / RLS / SSE)
  - 4 short-circuit if `is_maintainer` (permission checks)
  - 1 split required (`get_user_info` uses same variable for both identity and guild calls)

- `store_user_tokens` — single call site in callback, clean insertion point

- `discord_bot_token` — already available as `api_config.discord_bot_token` in API service

### Project Conventions

- `_make_api_request()` caching pattern in `DiscordAPIClient` for new `get_application_info()`
- `shared/cache/keys.py` static method pattern for new `app_info()` key
- `shared/cache/ttl.py` class constant pattern for new `APP_INFO` TTL
- FastAPI `Depends()` patterns in `permissions.py` unchanged — short-circuits return `current_user` before reaching permission check logic

## Key Discoveries

### Two Distinct Token Purposes

`token_data["access_token"]` is used for two distinct purposes today:

1. **Guild membership / RLS** — "is this user in this guild?" → bot token makes maintainer appear to be in all guilds
2. **User identity / permissions** — "check this user's Discord roles", "fetch this user's profile" → must remain real OAuth token

These map to two different change strategies.

### Call Site Classification (Complete)

**No change — correct as-is:**

- `auth.py:84` — `CurrentUser.access_token` population (real user token, always)
- `auth.py:100` — `get_user_from_token()` right after OAuth exchange (raw Discord response, not session)
- `auth.py:122` — `store_user_tokens()` call (raw Discord response, not session)

**Use `get_guild_token(token_data)` — guild membership / RLS / event routing:**

- `permissions.py:104` — `verify_guild_membership()`
- `permissions.py:447` — `get_guild_name()`
- `sse_bridge.py:147` — SSE event delivery check
- `shared/database.py` — `get_db_with_user_guilds()` RLS setup
- `routes/guilds.py` — `list_guilds()` guild menu

**Short-circuit `return current_user` if `token_data.get("is_maintainer")` — permission checks:**

- `permissions.py:311` — `_require_permission()` (covers `require_manage_guild`, `require_manage_channels`, `require_bot_manager`)
- `permissions.py:533` — `require_game_host()`
- `permissions.py:593` — `can_manage_game()`
- `permissions.py:683` — `require_administrator()`

**Split into two variables — same function needs both:**

- `auth.py:233` — `get_user_info()`: `access_token` stays for `get_user_from_token()`, `get_guild_token(token_data)` for `get_user_guilds()` call

### Session Data Shape

Current:

```json
{
  "user_id": "...",
  "access_token": "<encrypted>",
  "refresh_token": "<encrypted>",
  "expires_at": "..."
}
```

Proposed:

```json
{
  "user_id": "...",
  "access_token": "<encrypted>",
  "refresh_token": "<encrypted>",
  "expires_at": "...",
  "can_be_maintainer": false,
  "is_maintainer": false
}
```

`can_be_maintainer` set at login from `/oauth2/applications/@me`, never mutated.
`is_maintainer` starts `false` always, set by toggle endpoint after live re-validation.

### `get_guild_token()` Implementation

```python
def get_guild_token(session_data: dict) -> str:
    if session_data.get("is_maintainer"):
        return get_api_config().discord_bot_token
    return decrypt_token(session_data["access_token"])
```

Synchronous. Bot token comes from config, never stored in Redis.

### `is_app_maintainer()` Implementation

```python
async def is_app_maintainer(discord_id: str) -> bool:
    discord = get_discord_client()
    app_info = await discord.get_application_info()  # cached 1 hour
    owner_id = app_info.get("owner", {}).get("id")
    if owner_id == discord_id:
        return True
    team = app_info.get("team")
    if team:
        return any(
            m.get("user", {}).get("id") == discord_id
            for m in team.get("members", [])
        )
    return False
```

### `get_application_info()` Caching Pattern

```python
async def get_application_info(self) -> dict[str, Any]:
    return await self._make_api_request(
        method="GET",
        url=f"{DISCORD_API_BASE}/oauth2/applications/@me",
        operation_name="get_application_info",
        headers={"Authorization": self._get_auth_header()},  # bot token by default
        cache_key=cache_keys.CacheKeys.app_info(),
        cache_ttl=ttl.CacheTTL.APP_INFO,
    )
```

### Short-Circuit Pattern for Permission Checks

```python
token_data = await tokens.get_user_tokens(current_user.session_token)
if not token_data:
    raise HTTPException(...)

if token_data.get("is_maintainer"):
    return current_user  # bypass all permission checks

# ... existing permission logic unchanged
```

### Frontend Architecture

The frontend is React + MUI. Key touchpoints:

- **API calls**: `apiClient` (axios) from `frontend/src/api/client.ts` — `withCredentials: true`, 401 auto-logout. New calls go in a dedicated module (e.g. `frontend/src/api/maintainers.ts`).
- **Auth state**: `AuthContext` provides `user: CurrentUser | null` and `refreshUser()`. After any maintainer action, call `refreshUser()` to propagate state changes reactively.
- **UI location**: `GuildListPage.tsx` top `Box` — alongside existing "Sync Servers and Channels" button. The pattern: async handler → API call → `refreshUser()` → page re-renders with updated `user`.
- **Confirmation dialog**: Use MUI `Dialog` / `DialogTitle` / `DialogContent` / `DialogActions` for the "Refresh Maintainers" confirmation. Other pages in the project use this pattern.
- **Conditional rendering**: Gate entire maintainer section on `user?.can_be_maintainer`. Gate "Refresh Maintainers" button on `user?.is_maintainer`.

### Toggle Endpoint Behavior

Requires `can_be_maintainer` in session. Re-calls `is_app_maintainer()` live (hits 1-hour cache) to confirm still valid. Sets `is_maintainer: true` in Redis session if confirmed, rejects with 403 if not. This means removing someone from the Discord developer portal blocks re-elevation after cache expires (≤1 hour) even without using Refresh Maintainers.

### Refresh Maintainers Endpoint Behavior

```python
my_key = f"session:{current_user.session_token}"
async for key in redis.scan_iter("session:*"):
    if key == my_key:
        continue
    data = await redis.get_json(key)
    if data and data.get("is_maintainer"):
        await redis.delete(key)
await redis.delete(cache_keys.CacheKeys.app_info())
```

Caller's session preserved. All other `is_maintainer: true` sessions deleted. `get_application_info()` cache flushed so next login/elevation picks up Discord changes immediately. With O(1K) sessions expected, the scan completes in milliseconds.

Frontend shows confirmation: "This will refresh the maintainer list and log out all other elevated maintainers. Continue?"

## Recommended Approach

Dual-flag session approach (`can_be_maintainer` / `is_maintainer`) with `get_guild_token()` as the single indirection point for guild/RLS calls, and `is_maintainer` short-circuits for permission checks. Backed by `GET /oauth2/applications/@me` with 1-hour Redis cache. No hardcoded IDs, no extra Discord infrastructure.

## Implementation Guidance

- **Objectives**:
  - Allow Discord application owners/team members to see all bot-present guilds and bypass per-guild permission checks
  - Normal users completely unaffected — zero changes to their code paths
  - Surgical revocation via "Refresh Maintainers" endpoint
  - Re-login required to gain maintainer access; logout required for other elevated sessions on revocation

- **Key Tasks** (in dependency order):

  _Backend:_
  1. `shared/cache/ttl.py` — add `APP_INFO = 3600`
  2. `shared/cache/keys.py` — add `app_info()` returning `"discord:app_info"`
  3. `shared/discord/client.py` — add `get_application_info()` using `_make_api_request` with cache
  4. `services/api/auth/oauth2.py` — add `is_app_maintainer(discord_id)` helper
  5. `services/api/auth/tokens.py` — add `get_guild_token(session_data)` function; update `store_user_tokens()` to accept/store `can_be_maintainer`; update `get_user_tokens()` to return `can_be_maintainer` and `is_maintainer`
  6. `services/api/routes/auth.py` callback — call `is_app_maintainer()`, pass `can_be_maintainer` to `store_user_tokens()`
  7. `services/api/routes/auth.py` `get_user_info()` — split `access_token` variable: keep for `get_user_from_token()`, use `get_guild_token(token_data)` for `get_user_guilds()`; add `can_be_maintainer` and `is_maintainer` to `UserInfoResponse` schema and response
  8. `services/api/dependencies/permissions.py` — apply `get_guild_token(token_data)` at lines 104, 447; add `is_maintainer` short-circuit at lines 311, 533, 593, 683
  9. `services/api/services/sse_bridge.py` — apply `get_guild_token(token_data)` at line 147
  10. `shared/database.py` `get_db_with_user_guilds()` — use `get_guild_token()` derived from session
  11. `services/api/routes/guilds.py` `list_guilds()` — use `get_guild_token()` derived from session
  12. Add `POST /api/v1/maintainers/toggle` endpoint — requires `can_be_maintainer`, re-validates via `is_app_maintainer()`, sets `is_maintainer` in session
  13. Add `POST /api/v1/maintainers/refresh` endpoint — requires `is_maintainer`, scans Redis, deletes `is_maintainer: true` sessions (excluding caller), flushes `app_info` cache

  _Frontend:_ 14. `frontend/src/types/index.ts` — add `can_be_maintainer: boolean` and `is_maintainer: boolean` to `CurrentUser` interface 15. `frontend/src/api/maintainers.ts` — new API module with `toggleMaintainerMode()` (`POST /api/v1/maintainers/toggle`) and `refreshMaintainers()` (`POST /api/v1/maintainers/refresh`) 16. `frontend/src/pages/GuildListPage.tsx` — add maintainer controls (visible only when `user.can_be_maintainer`): - Toggle switch "Maintainer Mode" that calls `toggleMaintainerMode()` then `refreshUser()` to update auth state - "Refresh Maintainers" button (visible only when `user.is_maintainer`) with MUI `Dialog` confirmation: "This will refresh the maintainer list and log out all other elevated maintainers. Continue?" Calls `refreshMaintainers()` then `refreshUser()`

- **Dependencies**:
  - Tasks 1-2 before task 3; task 3 before task 4; task 4-5 before tasks 6-13
  - Tasks 7-11 are independent of each other once task 5 is done
  - Tasks 12-13 are independent of each other
  - Task 14 before tasks 15-16; task 7 (backend schema) before task 14 is meaningful to test end-to-end
  - Tasks 15-16 are independent of each other

- **Success Criteria**:
  - Discord application owner can log in, enable maintainer mode via toggle, see all bot-present guilds, and bypass per-guild permission checks
  - Normal user session data, token refresh, and all access controls are completely unchanged
  - "Refresh Maintainers" deletes all `is_maintainer: true` sessions except caller's and flushes app info cache
  - Toggle endpoint re-validates against Discord (cached), rejects if user was removed from app team
  - Maintainer controls only appear in the UI for users with `can_be_maintainer: true`
  - All existing tests pass; new unit tests cover `get_guild_token()`, `is_app_maintainer()`, `get_application_info()`, toggle endpoint, refresh endpoint, each modified call site, and frontend maintainer controls
