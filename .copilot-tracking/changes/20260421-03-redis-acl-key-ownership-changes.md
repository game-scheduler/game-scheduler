<!-- markdownlint-disable-file -->

# Changes: Redis ACL Key Ownership

## Summary

Enforces Redis key ownership at the server level by renaming API-owned keys to an `api:` prefix, removing the bot's shared write access to `user_roles:*`, and wiring per-service ACL users so the API cannot write gateway data and the bot cannot write API session/auth data.

## Phase 1: Rename API-owned session/auth/display keys to `api:` prefix

### Added

### Modified

- `shared/cache/keys.py`: Renamed 5 key prefixes: `session:` → `api:session:`, `oauth_state:` → `api:oauth:`, `display:` → `api:display:`, `user_guilds:` → `api:user_guilds:`, `"discord:app_info"` → `"api:app_info"`
- `services/api/auth/tokens.py`: Updated 4 literal `f"session:{session_token}"` strings to `f"api:session:{session_token}"`
- `services/api/auth/oauth2.py`: Updated 2 literal `f"oauth_state:{state}"` strings to `f"api:oauth:{state}"`
- `services/api/routes/maintainers.py`: Updated 2 literal session key strings and 1 scan pattern from `"session:*"` → `"api:session:*"`
- `tests/unit/shared/cache/test_keys.py`: Updated 3 key assertions for display_name, session, and oauth_state prefixes
- `tests/integration/test_auth_routes.py`: Updated 4 literal key strings (oauth_state and session) to use `api:` prefix
- `tests/integration/test_maintainers_integration.py`: Updated 4 literal session key strings to `api:session:` prefix
- `tests/unit/services/api/routes/test_maintainers_routes.py`: Updated 3 session key literals and 1 `discord:app_info` → `api:app_info` assertion
- `tests/shared/auth_helpers.py`: Updated 2 literal session key strings to `api:session:` prefix

### Removed

---

## Phase 2: Transfer `user_roles:*` ownership to API; remove bot write path

### Added

### Modified

### Removed

---

## Phase 3: Rename `discord:member:*` to `api:member:*`

### Added

### Modified

### Removed

---

## Phase 4: ACL infrastructure wiring

### Added

### Modified

### Removed
