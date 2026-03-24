<!-- markdownlint-disable-file -->

# Task Research Notes: Role-Based Scheduling Method

## Research Executed

### File Analysis

- `shared/models/signup_method.py`
  - `SignupMethod` StrEnum: `SELF_SIGNUP`, `HOST_SELECTED`
  - Note in source: TypeScript enum must be kept in sync

- `shared/models/participant.py`
  - `ParticipantType` IntEnum: `HOST_ADDED = 8000`, `SELF_ADDED = 24000`
  - Note in source: TypeScript enum at `frontend/src/types/index.ts` must be kept in sync
  - `position_type`: SmallInteger (max 32767) — sparse values leave room for new tiers
  - `position`: SmallInteger — sequential from 1 for HOST_ADDED, 0 for SELF_ADDED
  - `joined_at`: datetime, used as third sort key

- `shared/utils/participant_sorting.py`
  - `sort_participants(participants)` — pure sync sort by `(position_type, position, joined_at)`
  - `partition_participants(participants, max_players)` — calls `sort_participants`, splits into confirmed/overflow, returns `PartitionedParticipants`
  - All callers use `partition_participants`; `sort_participants` is internal
  - **These are unchanged by this feature.**

- `shared/models/template.py` — `GameTemplate`
  - `allowed_signup_methods: JSON | null` — list of allowed signup method strings (locked)
  - `default_signup_method: String(50) | null` — default method for game creation (locked)
  - Multiple existing JSON array columns (no DB-level size constraint): `notify_role_ids`, `allowed_player_role_ids`, `allowed_host_role_ids`, `reminder_minutes`

- `services/api/routes/games.py` — join endpoint
  - `POST /{game_id}/join` at line 627 — `join_game` route handler
  - Already has `role_service: RoleVerificationService` injected (used by `verify_game_access`)
  - Calls `game_service.join_game(game_id, user_discord_id)`

- `services/api/services/games.py` — `GameService.join_game`
  - Line 1844: creates participant with hardcoded `position_type=SELF_ADDED, position=0`
  - `join_game` accepts `game_id` and `user_discord_id` only; does not currently take role context

- `services/bot/handlers/join_game.py` — `handle_join_game`
  - Creates participant directly with hardcoded `position_type=SELF_ADDED, position=0`
  - Has `interaction: discord.Interaction` — in guild context `interaction.user` is `discord.Member`
  - `discord.Member.roles` is populated from the interaction payload at no API cost
  - Bot runs with `discord.Intents(guilds=True)` only — **no `GUILD_MEMBERS` privileged intent**; `guild.get_member()` returns `None` outside of interaction context

- `services/api/auth/roles.py` — `RoleVerificationService`
  - `get_user_role_ids(discord_id, guild_discord_id)` — Redis cache + Discord API fallback
  - TTL = `USER_ROLES = 300` seconds (5 min, `shared/cache/ttl.py`)
  - Already injected into the join route via `permissions_deps.get_role_service`
  - `verify_game_access` (called before join) already calls this → result is cached; subsequent call in join logic is a Redis hit

- `services/bot/auth/role_checker.py` — `RoleChecker`
  - `get_user_role_ids(user_id, guild_id)` — Redis cache + `guild.fetch_member` fallback
  - Uses `services/bot/auth/cache.py` `RoleCache` with same 5-minute pattern

- `frontend/src/types/index.ts`
  - `SignupMethod` enum and `SIGNUP_METHOD_INFO` record in sync with Python
  - `ParticipantType` enum in sync with Python
  - `GameTemplate` interface has `allowed_signup_methods` and `default_signup_method`

- `frontend/src/components/TemplateForm.tsx`
  - Does not render `allowed_signup_methods` or `default_signup_method` — pre-existing gap
  - Has existing multi-select role pickers for `notify_role_ids`, `allowed_player_role_ids`, `allowed_host_role_ids`

### Code Search Results

- `partition_participants` call sites (6 total) — **all unchanged**:
  - `services/api/services/games.py`: lines 827, 1406, 1592, 1677
  - `services/api/routes/games.py`: line 868
  - `services/bot/events/handlers.py`: lines 505, 685, 1263, 1313

- Discord rate limit research (`https://docs.discord.com/developers/topics/rate-limits`):
  - Discord does not publish specific per-route limits
  - Global limit: 50 req/sec per bot token
  - Per-route limits discovered at runtime from `X-RateLimit-*` headers
  - **Resolved**: role resolution at join time means exactly one API call per user ever (cached thereafter), not N calls per sort

### Project Conventions

- JSON columns used for all variable-length collections; no DB-level size limits
- Python/TypeScript enum sync enforced by code comment convention
- `SmallInteger` for position fields; sparse int values used for priority tiers

## Key Discoveries

### Design Decisions

1. `signup_priority_role_ids` is a **template-only locked setting** (not per-game)
2. `ROLE_BASED` activates **automatically** when `signup_priority_role_ids` is non-empty
3. Max **8 roles** enforced at API validation layer only (no DB constraint)
4. Role priority is resolved **at join time** and written directly to `position_type` / `position` in the DB — not at sort time
5. `sort_participants`, `partition_participants`, `PartitionedParticipants`, and all 6 call sites are **completely unchanged**
6. If a template's `signup_priority_role_ids` is edited after players have joined, existing participants keep their stored values — no retroactive re-resolution
7. The bot interaction payload provides member roles for free; this also warms the Redis cache as a beneficial side effect

### Role Resolution at Join Time

Role priority is resolved once when a participant is created and written to the DB:

```python
def resolve_role_position(
    user_role_ids: list[str],
    priority_role_ids: list[str],  # ordered, from template
) -> tuple[int, int]:
    """Returns (position_type, position) for a self-added participant."""
    for index, role_id in enumerate(priority_role_ids):
        if role_id in user_role_ids:
            return ParticipantType.ROLE_MATCHED, index
    return ParticipantType.SELF_ADDED, 0
```

This pure function lives in `shared/utils/participant_sorting.py`. When `priority_role_ids` is empty (non-ROLE_BASED game), callers skip it entirely and use `(SELF_ADDED, 0)` directly.

### Sort Key (DB values, no computation at sort time)

| Tier                  | `position_type` | `position`              | `joined_at` |
| --------------------- | --------------- | ----------------------- | ----------- |
| Host-added            | 8000            | sequential (1, 2, …)    | tie-breaker |
| Role-matched          | 16000           | role index (0, 1, …, 7) | tie-breaker |
| Self-added (no match) | 24000           | 0                       | tie-breaker |

### Bot Join Path (`services/bot/handlers/join_game.py`)

`interaction.user` is `discord.Member` in guild context. Member roles come free in the interaction payload — no API call needed.

```python
priority_role_ids = game.template.signup_priority_role_ids or []
if priority_role_ids and isinstance(interaction.user, discord.Member):
    user_role_ids = [str(r.id) for r in interaction.user.roles if str(r.id) != str(interaction.guild_id)]
    # Warm the role cache with the free data from the interaction payload.
    # Do NOT write directly to Redis here — the cache belongs to RoleChecker.
    # Call a new seeding method on RoleChecker instead (see note below).
    await role_checker.seed_user_roles(str(interaction.user.id), str(interaction.guild_id), user_role_ids)
    position_type, position = resolve_role_position(user_role_ids, priority_role_ids)
else:
    position_type, position = ParticipantType.SELF_ADDED, 0
```

The `GameParticipant` is then created with the resolved `position_type` and `position`.

**Cache seeding note**: `RoleChecker` gains a new `seed_user_roles(user_id, guild_id, role_ids)` method that delegates to `self.cache.set_user_roles(...)`. This keeps Redis access encapsulated inside `RoleChecker`/`RoleCache` — callers never touch Redis directly. The method is identical in behaviour to the cache-write already performed by `get_user_role_ids` after a live fetch, just invoked with caller-supplied data.

### API Join Path (`services/api/routes/games.py` → `GameService.join_game`)

`role_service` (`RoleVerificationService`) is already injected at the route. `verify_game_access` (called before join) already calls `get_user_role_ids` — the result is cached. The cleanest approach is to resolve priority in the route handler and pass `position_type`/`position` into `join_game`:

```python
priority_role_ids = game.template.signup_priority_role_ids or []
if priority_role_ids:
    user_role_ids = await role_service.get_user_role_ids(
        current_user.user.discord_id, game.guild.guild_id
    )  # Redis hit — already fetched by verify_game_access above
    position_type, position = resolve_role_position(user_role_ids, priority_role_ids)
else:
    position_type, position = ParticipantType.SELF_ADDED, 0

participant = await game_service.join_game(
    game_id=game_id,
    user_discord_id=current_user.user.discord_id,
    position_type=position_type,
    position=position,
)
```

`GameService.join_game` gains two new optional parameters with defaults `(SELF_ADDED, 0)` — existing callers are unaffected.

### DB Migration

Two migrations:

1. Add nullable JSON column to `game_templates`:

```sql
ALTER TABLE game_templates ADD COLUMN signup_priority_role_ids JSON NULL;
```

2. No changes to `game_participants` — `position_type` and `position` columns already exist.

### Frontend Changes

**`TemplateForm.tsx`** — new "Role Priority" section (locked settings area):

- Multi-select to add roles from the guild role list (same `roles` prop already passed in)
- Added roles appear as a draggable ordered list (role index = priority)
- Max 8 roles enforced in UI
- Serialized as ordered `string[]` of Discord role IDs

**`frontend/src/types/index.ts`**:

- Add `ROLE_BASED = 'ROLE_BASED'` to `SignupMethod` enum
- Add `ROLE_MATCHED = 16000` to `ParticipantType` enum
- Add `signup_priority_role_ids?: string[] | null` to `GameTemplate`, `TemplateCreateRequest`, `TemplateUpdateRequest`
- Add `SIGNUP_METHOD_INFO` entry for `ROLE_BASED`

**`GameForm.tsx`**: no structural changes needed — new method appears in dropdown automatically.

### Schemas / API

- `shared/schemas/template.py`: add `signup_priority_role_ids: list[str] | None` with `max_length=8` validator on the list
- `TemplateResponse` in `services/api/routes/templates.py`: pass through new field

## Implementation Guidance

- **Objectives**: Add `ROLE_BASED` signup method; role priority resolved once at join time and stored in existing DB columns; sort/partition logic completely unchanged
- **Key Tasks**:
  1. Add `ROLE_MATCHED = 16000` to `ParticipantType` (Python + TypeScript)
  2. Add `ROLE_BASED` to `SignupMethod` with display name/description (Python + TypeScript + `SIGNUP_METHOD_INFO`)
  3. DB migration: add `signup_priority_role_ids JSON nullable` to `game_templates`
  4. Update `GameTemplate` model and all related schemas/types
  5. Add `signup_priority_role_ids` validation (max 8) to template create/update API
  6. Add `resolve_role_position` pure function to `shared/utils/participant_sorting.py`
  7. Add `seed_user_roles(user_id, guild_id, role_ids)` method to `RoleChecker` (delegates to `self.cache.set_user_roles`)
  8. Update bot `handle_join_game` to resolve role priority from interaction payload and call `role_checker.seed_user_roles`
  9. Update `GameService.join_game` to accept optional `position_type`/`position`; update API join route to resolve and pass them
  10. Update `TemplateForm.tsx` with draggable role-priority list
- **Dependencies**: TDD applies to all Python and TypeScript changes; `test_participant_sorting.py` gains tests for `resolve_role_position`; no existing sorting tests change signatures
- **Success Criteria**: For a `ROLE_BASED` game, sort order is HOST_ADDED → ROLE_MATCHED (by role index, then `joined_at`) → SELF_ADDED (by `joined_at`); `partition_participants` and all its callers are unchanged; non-ROLE_BASED games behave identically to today

### E2E Test: `tests/e2e/test_role_based_signup.py`

An E2E test is needed to verify the full join-time role resolution flow through the real API stack (Redis, Discord API, database).

**What it tests (API path only)**:

1. Create a template with `signup_priority_role_ids` containing a role the test bot actually holds in the Discord test guild
2. Create a game from that template
3. Bot joins via `POST /games/{game_id}/join`
4. Assert the returned participant has `position_type=ROLE_MATCHED` and the correct `position` index
5. Assert DB row confirms `position_type` and `position` are persisted (not just in-memory)

**What cannot be tested in E2E (uses API path, not bot button)**:

- The bot button interaction path (`handle_join_game`) and its cache-seeding behaviour — this is covered by unit/integration tests for `handle_join_game` and `RoleChecker.seed_user_roles`

**Fixture requirements**:

- Template fixture (created directly in DB, same pattern as `test_game_authorization.py`) with `signup_priority_role_ids` set to a known role held by the admin bot in the test guild
- The role ID must be a real role in `DISCORD_GUILD_A_ID` that `DISCORD_ADMIN_BOT_TOKEN` already has — documented in `docs/developer/TESTING.md`
- Uses existing `authenticated_admin_client`, `admin_db`, `synced_guild`, `bot_discord_id` fixtures

**Parametrize for**:

- Bot has highest-priority role (index 0) → `position=0`
- Bot has second-priority role only (index 1) → `position=1`
- Bot has no matching role → `position_type=SELF_ADDED, position=0`
- Template has empty `signup_priority_role_ids` → `position_type=SELF_ADDED, position=0` (non-ROLE_BASED fallback)
