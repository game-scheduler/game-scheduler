# Changes: Dependency Version Audit and Upgrade Strategy

**Plan**: [20251215-dependency-version-audit-plan.instructions.md](../plans/20251215-dependency-version-audit-plan.instructions.md)
**Details**: [20251215-dependency-version-audit-details.md](../details/20251215-dependency-version-audit-details.md)
**Research**: [20251215-dependency-version-audit-research.md](../research/20251215-dependency-version-audit-research.md)

## Phase Status

- [x] **Phase 1: PostgreSQL 18 Upgrade + Alembic Reset** - In Progress
  - [x] Task 1.1: Fix SQLAlchemy models server_default - ✅ Complete
  - [ ] Task 1.2: Install alembic-utils
  - [ ] Task 1.3: Update PostgreSQL to 18-alpine
  - [ ] Task 1.4: Reset Alembic migrations
  - [ ] Task 1.5: Verify database schema and services
- [ ] **Phase 2: Node.js 24 LTS Upgrade**
- [ ] **Phase 3: Python Dependency Modernization**
- [ ] **Phase 4: NPM Package Updates**

## Changes Log

### Phase 1: PostgreSQL 18 Upgrade + Alembic Reset

#### Task 1.1: Fix SQLAlchemy models server_default ✅

**Purpose**: Add `server_default` declarations to all SQLAlchemy models to prevent Alembic autogenerate from dropping PostgreSQL server defaults during migration reset.

**Files Modified**:
- [shared/models/guild.py](../../../shared/models/guild.py) - Lines 21, 47-52
- [shared/models/channel.py](../../../shared/models/channel.py) - Lines 21, 45-49
- [shared/models/game.py](../../../shared/models/game.py) - Lines 21, 75-84
- [shared/models/template.py](../../../shared/models/template.py) - Lines 21, 51-58
- [shared/models/participant.py](../../../shared/models/participant.py) - Lines 21, 53
- [shared/models/user.py](../../../shared/models/user.py) - Lines 21, 45-51
- [shared/models/notification_schedule.py](../../../shared/models/notification_schedule.py) - Lines 21, 50-53
- [shared/models/game_status_schedule.py](../../../shared/models/game_status_schedule.py) - Lines 21, 48-51

**Changes Made**:
1. **Added SQLAlchemy imports**: Added `func` and `text` imports to all model files
2. **Boolean columns**: Added `server_default=text('false')` or `text('true')` to:
   - `GuildConfiguration.require_host_role`
   - `ChannelConfiguration.is_active`
   - `GameTemplate.is_default`
   - `NotificationSchedule.sent`
   - `GameStatusSchedule.executed`
3. **Integer columns**: Added `server_default=text('0')` to:
   - `GameTemplate.order`
4. **String columns**: Added `server_default=text("'SCHEDULED'")` to:
   - `GameSession.status`
5. **JSON columns**: Added `server_default=text("'{}'")` to:
   - `User.notification_preferences`
6. **Timestamp columns**: Added `server_default=func.now()` to all `created_at` and `updated_at` columns across all models

**Verification**:
- ✅ All models import successfully
- ✅ All model unit tests pass (19 tests)
- ✅ All Python unit tests pass (679 tests, 18.62s)
- ✅ All frontend tests pass (51 tests, 8.78s)
- ✅ All integration tests pass (37 tests, 112.95s)
- ✅ No breaking changes to existing behavior
- ✅ Total: **767 tests passing**

**Key Design Decisions**:
- Used SQLAlchemy's `text()` for literal values (booleans, strings, JSON)
- Used SQLAlchemy's `func.now()` for timestamp defaults (translates to PostgreSQL's `now()`)
- Maintained Python-side `default=` for backward compatibility with existing code
- Server defaults ensure database consistency even when SQLAlchemy is bypassed

#### Task 1.2: Install alembic-utils (Next)

**Purpose**: Install alembic-utils package and register PostgreSQL functions and triggers to ensure they are tracked in Alembic migrations.

**Status**: Not started

---

**Last Updated**: 2025-12-16 07:33 UTC
