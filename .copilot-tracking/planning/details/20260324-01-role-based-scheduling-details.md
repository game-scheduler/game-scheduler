<!-- markdownlint-disable-file -->

# Task Details: Role-Based Scheduling Method

## Research Reference

**Source Research**: #file:../research/20260324-01-role-based-scheduling-research.md

## Phase 1: Enum Updates (Python + TypeScript)

### Task 1.1: Add ROLE_MATCHED to Python ParticipantType

Add `ROLE_MATCHED = 16000` between `HOST_ADDED = 8000` and `SELF_ADDED = 24000` in
`shared/models/participant.py`. The sparse values preserve the sort tier ordering:
HOST_ADDED (8000) < ROLE_MATCHED (16000) < SELF_ADDED (24000).

- **Files**:
  - `shared/models/participant.py` — add `ROLE_MATCHED = 16000` to `ParticipantType` IntEnum
- **Success**:
  - `ParticipantType.ROLE_MATCHED == 16000`
  - Existing `HOST_ADDED` (8000) and `SELF_ADDED` (24000) values are unchanged
  - Update the TypeScript sync comment to include `ROLE_MATCHED`
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 10-14) — ParticipantType current values
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 108-114) — Sort key tier table
- **Dependencies**:
  - None

### Task 1.2: Add ROLE_BASED to Python SignupMethod

Add `ROLE_BASED = 'ROLE_BASED'` to the `SignupMethod` StrEnum in `shared/models/signup_method.py`.

- **Files**:
  - `shared/models/signup_method.py` — add `ROLE_BASED = 'ROLE_BASED'`
- **Success**:
  - `SignupMethod.ROLE_BASED` is accessible
  - Existing `SELF_SIGNUP` and `HOST_SELECTED` values are unchanged
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 4-7) — SignupMethod current values
- **Dependencies**:
  - None

### Task 1.3: Sync TypeScript Enums and SIGNUP_METHOD_INFO

Update `frontend/src/types/index.ts`:

- Add `ROLE_BASED = 'ROLE_BASED'` to `SignupMethod` TypeScript enum
- Add `ROLE_MATCHED = 16000` to `ParticipantType` TypeScript enum
- Add an entry for `ROLE_BASED` in `SIGNUP_METHOD_INFO` with a display name and description
- Add `signup_priority_role_ids?: string[] | null` to `GameTemplate`,
  `TemplateCreateRequest`, and `TemplateUpdateRequest` interfaces

- **Files**:
  - `frontend/src/types/index.ts` — enum and interface updates
- **Success**:
  - TypeScript and Python enums are in sync
  - `SIGNUP_METHOD_INFO[SignupMethod.ROLE_BASED]` returns a valid display entry
  - `signup_priority_role_ids` field is present in all three template interfaces
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 68-73) — Frontend enum sync
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 186-198) — Frontend type additions
- **Dependencies**:
  - Task 1.1 and 1.2 complete

## Phase 2: Database Migration and Model/Schema Updates

### Task 2.1: Alembic Migration for signup_priority_role_ids

Create a new Alembic migration that adds a nullable JSON column `signup_priority_role_ids`
to the `game_templates` table. No changes to `game_participants` — the `position_type` and
`position` columns already exist.

```sql
ALTER TABLE game_templates ADD COLUMN signup_priority_role_ids JSON NULL;
```

- **Files**:
  - `alembic/versions/<revision>_add_signup_priority_role_ids.py` — new migration file
- **Success**:
  - `uv run alembic upgrade head` applies cleanly on a fresh DB
  - Downgrade migration removes the column without error
  - Column exists with `NULL` default
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 179-183) — DB migration design
- **Dependencies**:
  - None

### Task 2.2: Update GameTemplate SQLAlchemy Model

Add `signup_priority_role_ids: Mapped[list[str] | None]` to `shared/models/template.py`
`GameTemplate` class using `JSON` type and `nullable=True`, matching the pattern of
existing JSON array columns (`notify_role_ids`, `allowed_player_role_ids`, etc.).

- **Files**:
  - `shared/models/template.py` — add `signup_priority_role_ids` column mapping
- **Success**:
  - Model reads/writes the column correctly
  - Existing model tests pass unchanged
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 26-29) — GameTemplate existing JSON column pattern
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Update Pydantic Schemas and TemplateResponse

Add `signup_priority_role_ids: list[str] | None = None` to template create/update schemas
in `shared/schemas/template.py` with a validator that rejects lists longer than 8 entries.
Update `TemplateResponse` in `services/api/routes/templates.py` to expose the new field.

- **Files**:
  - `shared/schemas/template.py` — add field with max-8 validator
  - `services/api/routes/templates.py` — add field to `TemplateResponse`
- **Success**:
  - Submitting `signup_priority_role_ids` with more than 8 entries returns HTTP 422
  - Field round-trips correctly through create and retrieve
  - `TemplateResponse` includes `signup_priority_role_ids`
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 200-203) — Schema and API specification
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Core Logic (TDD)

### Task 3.1: TDD resolve_role_position

Following TDD: write failing (xfail) tests in `tests/unit/test_participant_sorting.py` first,
then implement the function.

Add `resolve_role_position(user_role_ids: list[str], priority_role_ids: list[str]) -> tuple[int, int]`
to `shared/utils/participant_sorting.py`. Returns `(position_type, position)`:

- If a `priority_role_ids` entry is in `user_role_ids`, return `(ROLE_MATCHED, index_of_first_match)`
- Otherwise return `(SELF_ADDED, 0)`
- Empty `priority_role_ids` always returns `(SELF_ADDED, 0)`

Required test cases (all xfail initially, then passing after implementation):

1. User has highest-priority role (index 0) → `(ROLE_MATCHED, 0)`
2. User has second-priority role only → `(ROLE_MATCHED, 1)`
3. User has no matching role → `(SELF_ADDED, 0)`
4. Empty `priority_role_ids` → `(SELF_ADDED, 0)`
5. User has multiple matching roles → first match (lowest index) wins

- **Files**:
  - `tests/unit/test_participant_sorting.py` — new test cases for `resolve_role_position`
  - `shared/utils/participant_sorting.py` — add `resolve_role_position` function
- **Success**:
  - All 5 new test cases pass
  - All existing participant sorting tests pass unchanged
  - Function is a pure sync function with no side effects
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 98-120) — resolve_role_position design and sort key table
- **Dependencies**:
  - Task 1.1 complete (ROLE_MATCHED enum value needed)

### Task 3.2: TDD seed_user_roles on RoleChecker

Following TDD: write a failing test first, then implement the method.

Add `async seed_user_roles(user_id: str, guild_id: str, role_ids: list[str]) -> None` to
`services/bot/auth/role_checker.py`. It delegates to `self.cache.set_user_roles(user_id, guild_id, role_ids)`.
This keeps Redis access encapsulated — no caller ever touches Redis directly.

The method mirrors the cache-write already performed by `get_user_role_ids` after a live fetch,
but is called with caller-supplied data from the interaction payload.

- **Files**:
  - `tests/unit/test_role_checker.py` — new test for `seed_user_roles`
  - `services/bot/auth/role_checker.py` — add `seed_user_roles` async method
- **Success**:
  - `seed_user_roles` writes to cache; subsequent `get_user_role_ids` returns the seeded data
  - Test verifies cache delegation without direct Redis access from the test
  - No direct Redis access from outside `RoleChecker`/`RoleCache`
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 121-133) — Cache seeding design
- **Dependencies**:
  - None

## Phase 4: Join Path Updates

### Task 4.1: Update GameService.join_game Signature

Add two optional parameters to `GameService.join_game` in `services/api/services/games.py`:

- `position_type: int = ParticipantType.SELF_ADDED`
- `position: int = 0`

The participant creation line (currently hardcoded to `SELF_ADDED, 0`) uses these parameters.
Existing callers are unaffected because both parameters have defaults that preserve current behaviour.

- **Files**:
  - `services/api/services/games.py` — update `join_game` signature and participant creation (line ~1844)
- **Success**:
  - Existing unit tests for `join_game` pass unchanged
  - New `position_type`/`position` values are stored when provided
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 53-57) — Current join_game implementation
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 140-153) — Updated signature design
- **Dependencies**:
  - Task 3.1 complete

### Task 4.2: Update API Join Route

In `services/api/routes/games.py` `join_game` route handler (~line 627), after
`verify_game_access` and before calling `game_service.join_game`:

1. Read `priority_role_ids = game.template.signup_priority_role_ids or []`
2. If non-empty, call `role_service.get_user_role_ids(discord_id, guild_id)` — Redis hit,
   already fetched by `verify_game_access`
3. Call `resolve_role_position(user_role_ids, priority_role_ids)`
4. Pass resolved `position_type` and `position` to `game_service.join_game`

Import `resolve_role_position` from `shared.utils.participant_sorting`.

- **Files**:
  - `services/api/routes/games.py` — update `join_game` route handler
- **Success**:
  - User with a matching priority role receives `ROLE_MATCHED` participant type
  - User with no matching role receives `SELF_ADDED`
  - Game with null/empty `signup_priority_role_ids` behaves identically to today
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 136-153) — API join path design
- **Dependencies**:
  - Task 3.1, 4.1 complete

### Task 4.3: Update Bot handle_join_game

In `services/bot/handlers/join_game.py`, update `handle_join_game`:

1. Read `priority_role_ids = game.template.signup_priority_role_ids or []`
2. If non-empty and `isinstance(interaction.user, discord.Member)`:
   - Extract `user_role_ids = [str(r.id) for r in interaction.user.roles if str(r.id) != str(interaction.guild_id)]`
     (exclude `@everyone` pseudo-role whose ID equals the guild ID)
   - Call `await role_checker.seed_user_roles(user_id, guild_id, user_role_ids)`
   - Call `resolve_role_position(user_role_ids, priority_role_ids)`
3. Otherwise use `(SELF_ADDED, 0)`
4. Create `GameParticipant` with the resolved `position_type` and `position`

Import `resolve_role_position` from `shared.utils.participant_sorting`.

- **Files**:
  - `services/bot/handlers/join_game.py` — update `handle_join_game`
- **Success**:
  - Bot uses roles from interaction payload (zero extra API calls)
  - Cache is warmed as a side effect via `seed_user_roles`
  - Guild-only intents constraint is satisfied (`discord.Member` check)
  - Non-ROLE_BASED games and non-guild-context interactions continue to work
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 116-133) — Bot join path design
- **Dependencies**:
  - Task 3.1, 3.2 complete

## Phase 5: Frontend Updates

### Task 5.2: Update TemplateForm.tsx with Role Priority Section

Add a "Role Priority" locked-settings section to `frontend/src/components/TemplateForm.tsx`:

- Visible only when `ROLE_BASED` is in `allowed_signup_methods`
- Multi-select picker sourced from the existing `roles` prop (guild role list)
- Selected roles render as a draggable ordered list (order = priority index)
- Disable "Add" button when 8 roles are already selected
- Serialize as `signup_priority_role_ids: string[]` in priority order; submit `null` when empty

Follow the existing multi-select pattern used for `notify_role_ids`, `allowed_player_role_ids`,
and `allowed_host_role_ids` for consistency. Check existing frontend dependencies before
choosing a drag library (prefer HTML5 drag API if no drag library is already installed).

- **Files**:
  - `frontend/src/components/TemplateForm.tsx` — add role priority section
- **Success**:
  - Section renders in the locked settings area
  - Drag-to-reorder changes the order in the submitted payload
  - Max-8 cap is enforced in the UI as well as the API
  - `signup_priority_role_ids` in submitted form data matches displayed order
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 185-198) — Frontend changes specification
- **Dependencies**:
  - Task 1.3, 2.3 complete

## Phase 6: E2E Test

### Task 6.1: Write E2E Test for Role-Based Join

Create `tests/e2e/test_role_based_signup.py`. Uses only the API join path (not the bot
button); the bot path is covered by unit/integration tests.

Parametrize over 4 cases:

1. Bot has role at index 0 → `(ROLE_MATCHED, 0)`
2. Bot has role at index 1 only → `(ROLE_MATCHED, 1)`
3. Bot has no matching role → `(SELF_ADDED, 0)`
4. Template `signup_priority_role_ids` is empty → `(SELF_ADDED, 0)`

Fixtures: `authenticated_admin_client`, `admin_db`, `synced_guild`, `bot_discord_id`
(all existing). Template objects are created directly in the DB following the pattern
in `test_game_authorization.py`. Role IDs used must be real roles in `DISCORD_GUILD_A_ID`
that `DISCORD_ADMIN_BOT_TOKEN` already holds. Document required test roles in
`docs/developer/TESTING.md`.

Each case asserts both the API response and the DB row for `position_type` and `position`.

- **Files**:
  - `tests/e2e/test_role_based_signup.py` — new E2E test
  - `docs/developer/TESTING.md` — add section documenting required test guild roles
- **Success**:
  - All 4 parametrized cases pass in the E2E environment
  - DB row confirms stored `position_type` and `position` values
  - Test follows the fixture and DB-setup pattern from `test_game_authorization.py`
- **Research References**:
  - #file:../research/20260324-01-role-based-scheduling-research.md (Lines 207-243) — E2E test specification
- **Dependencies**:
  - All Phase 4 tasks complete

## Dependencies

- Python packages: `alembic`, `sqlalchemy`, `pydantic`, `discord.py` (all installed)
- Frontend: check `frontend/package.json` for existing drag library before choosing one
- All Python and TypeScript changes must follow TDD methodology per `.github/instructions/test-driven-development.instructions.md`

## Success Criteria

- Sort order for a ROLE_BASED game: HOST_ADDED → ROLE_MATCHED (by role index, then `joined_at`) → SELF_ADDED (by `joined_at`)
- `partition_participants`, `sort_participants`, and all 6 call sites are completely unchanged
- Non-ROLE_BASED games behave identically to today
- Max 8 role IDs enforced at API layer (HTTP 422 on violation)
- All new code has passing unit tests written before implementation (TDD)
