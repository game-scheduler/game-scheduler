# Changes: Role-Based Scheduling Method

## Status

Phases 1, 2, 3, and 4 complete. Phases 5–6 pending.

## Added

- `alembic/versions/b7c8d9e0f1a2_add_signup_priority_role_ids.py` — Alembic migration adds nullable JSON `signup_priority_role_ids` column to `game_templates`

## Modified

- `shared/models/participant.py` — Added `ROLE_MATCHED = 16000` to `ParticipantType` IntEnum between `HOST_ADDED` and `SELF_ADDED`
- `shared/models/signup_method.py` — Added `ROLE_BASED = "ROLE_BASED"` to `SignupMethod` StrEnum with display_name and description
- `shared/models/template.py` — Added `signup_priority_role_ids: Mapped[list[str] | None]` JSON column to `GameTemplate`
- `shared/schemas/template.py` — Added `signup_priority_role_ids` field with max-8 validator to `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, and `TemplateListItem`
- `shared/utils/participant_sorting.py` — Added `resolve_role_position(user_role_ids, priority_role_ids) -> tuple[int, int]` pure function
- `services/api/services/games.py` — Added `position_type` and `position` optional params to `join_game`; added `selectinload(GameSession.template)` to `get_game` eager load
- `services/api/routes/games.py` — Added `_resolve_role_position_for_user` helper; updated `join_game` route to resolve role priority and pass to service
- `services/bot/auth/role_checker.py` — Added `seed_user_roles` async method
- `services/bot/handlers/join_game.py` — Updated `_validate_join_game` to load template with `selectinload`; added `_resolve_bot_role_position` helper; updated participant creation to use resolved position
- `frontend/src/types/index.ts` — Added `ROLE_BASED` to `SignupMethod` enum, `ROLE_MATCHED = 16000` to `ParticipantType` enum, `ROLE_BASED` entry to `SIGNUP_METHOD_INFO`, and `signup_priority_role_ids?: string[] | null` to `GameTemplate` and `TemplateCreateRequest` interfaces
- `tests/unit/shared/utils/test_participant_sorting.py` — Added `TestResolveRolePosition` class with 5 tests; added `resolve_role_position` to imports; added `test_role_matched_participant_type_value`
- `tests/unit/shared/models/test_signup_method.py` — Added `test_role_based_signup_method`; updated `test_signup_method_members` count from 2 to 3; added `import pytest`
- `tests/unit/schemas/test_schemas_template_schema.py` — Added three tests for `signup_priority_role_ids` acceptance, max-8 enforcement, and `TemplateResponse` exposure; added `import pytest`
- `tests/unit/services/bot/auth/test_role_checker.py` — Added `test_seed_user_roles_writes_to_cache`

## Removed

None.

## Divergences from Plan

None.
