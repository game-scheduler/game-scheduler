<!-- markdownlint-disable-file -->
# Task Research Notes: Multiple Signup Methods

## Research Executed

### File Analysis

- [shared/models/game.py](shared/models/game.py#L38-L110)
  - GameStatus enum exists as str, Enum base class
  - GameSession model has all core game fields
  - No signup_method field currently exists
- [shared/models/template.py](shared/models/template.py#L46-L145)
  - GameTemplate model includes locked and pre-populated fields
  - No signup method configuration currently present
  - Has allowed_host_role_ids and allowed_player_role_ids for role permissions
- [shared/models/guild.py](shared/models/guild.py#L36-L64)
  - GuildConfiguration has bot_manager_role_ids (JSON array)
  - No signup method configuration present
  - Simple structure with just role-based permissions
- [shared/schemas/game.py](shared/schemas/game.py#L34-L175)
  - GameCreateRequest includes template_id, title, scheduled_at, optional overrides
  - GameResponse includes all game fields plus participants
  - No signup_method field in any schema
- [services/bot/views/game_view.py](services/bot/views/game_view.py#L29-L100)
  - GameView has join_button and leave_button
  - Buttons disabled based on is_started flag
  - No signup method configuration currently exists
- [shared/models/participant.py](shared/models/participant.py#L43-L50)
  - ParticipantType enum uses IntEnum with HOST_ADDED=8000, SELF_ADDED=24000
  - Pattern for sparse value enums for future expansion exists
- [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx#L1-L400)
  - Game creation form with guild selector, template selector
  - GameForm component used with initialData from template defaults
  - No signup method selection UI present

### Code Search Results

- **GameStatus enum pattern**
  - Uses `class GameStatus(str, Enum)` pattern
  - Values: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
  - Located in shared/models/game.py
- **StrEnum usage in project**
  - tests/e2e/conftest.py uses `from enum import StrEnum`
  - TimeoutType(StrEnum) and DMType(StrEnum) patterns exist
  - Python 3.11+ StrEnum preferred over str, Enum
- **Template-based configuration pattern**
  - Templates have locked fields (channel_id, role_ids) and pre-populated fields (max_players, duration)
  - Guild-scoped templates with order and is_default flags
  - Frontend loads templates per guild and auto-selects default

### External Research

#githubRepo:"python/cpython enum" StrEnum str Enum
- Python 3.11+ introduced StrEnum as specialized str-based enum
- Benefits: cleaner string enum definition, automatic str methods
- Usage: `from enum import StrEnum` then `class MyEnum(StrEnum): VALUE = "value"`
- Backwards compatible: can use `class MyEnum(str, Enum)` for Python < 3.11

#githubRepo:"pallets/flask enum" form dropdown select enum
- Common pattern: Enum values in dropdown/select with `enum.value` as option value
- Display names: use `@property` on enum or separate dict mapping
- Form validation: validate against `MyEnum.__members__` or enum values

#fetch:https://docs.python.org/3/library/enum.html#enum.StrEnum
- StrEnum members are strings and can be used anywhere strings are used
- `auto()` generates string values from member names
- Recommended for enums that need to be strings (database values, API responses)

## Key Discoveries

### Current Signup Behavior

**Join Button Mechanics** (services/bot/views/game_view.py):
- Persistent buttons with `timeout=None` survive bot restarts
- Join button uses `custom_id=f"join_game_{game_id}"`
- Button disabled when `is_started=True` (game IN_PROGRESS or COMPLETED)
- Currently NO signup method restriction - anyone can click join

**Participant Creation Flow**:
1. User clicks Discord "Join Game" button
2. Bot handler (services/bot/handlers/join_game.py) validates user not duplicate
3. Creates GameParticipant with `position_type=SELF_ADDED`
4. Commits to database and publishes game.updated event
5. Bot refreshes Discord message with updated participant list

### Template Configuration Pattern

**Locked vs Pre-populated Fields**:
- **Locked**: channel_id, notify_role_ids, allowed_player_role_ids, allowed_host_role_ids
  - Cannot be changed by host during game creation
  - Enforced at template level
- **Pre-populated**: max_players, duration, reminders, where, signup_instructions
  - Provide defaults but host can edit during game creation
  - Optional overrides in GameCreateRequest

**Configuration Storage**:
- Templates are guild-scoped (one guild = many templates)
- **Each template independently configures its signup methods**
- No guild-level or server-wide signup method configuration
- All configuration is at the **template level**, giving fine-grained control per game type

### Database Migration Patterns

**Recent Migrations** (alembic/versions/):
- c2135ff3d5cd_initial_schema.py - Initial tables
- 8438728f8184_replace_prefilled_position_with_.py - Participant position refactor
- 790845a2735f_make_reminder_minutes_nullable.py - Field nullability change
- 3aeec3d09d7c_add_game_image_storage.py - Add image storage fields
- bcecd82ff82f_add_notification_type_participant_id.py - Notification enhancements

**Migration Pattern**:
```python
def upgrade() -> None:
    op.add_column("table_name", sa.Column("field_name", sa.Type(), nullable=True))

def downgrade() -> None:
    op.drop_column("table_name", "field_name")
```

**Data Migration for Enum Defaults**:
```python
# Set default value for existing rows
op.execute("UPDATE game_sessions SET signup_method = 'SELF_SIGNUP'")

# Make column non-nullable after backfill
op.alter_column("game_sessions", "signup_method", nullable=False)
```

## Recommended Approach

### Design Overview

**Signup Method Enum** (StrEnum):
```python
from enum import StrEnum

class SignupMethod(StrEnum):
    """Game signup method controlling participant addition."""

    SELF_SIGNUP = "SELF_SIGNUP"  # Players can join via Discord button (current behavior)
    HOST_SELECTED = "HOST_SELECTED"  # Only host can add players (button disabled)

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        return {
            "SELF_SIGNUP": "Self Signup",
            "HOST_SELECTED": "Host Selected",
        }[self.value]

    @property
    def description(self) -> str:
        """Description for UI tooltip/helper text."""
        return {
            "SELF_SIGNUP": "Players can join the game by clicking the Discord button",
            "HOST_SELECTED": "Only the host can add players (Discord button disabled)",
        }[self.value]
```

**Configuration Storage - Template Level (NOT Guild/Server Level)**:

1. **GameTemplate** (each template has its own configuration):
   - Add `allowed_signup_methods: list[str] | None`
     - Specifies which signup methods are available for games created with this template
     - Empty/null list = all methods allowed (SELF_SIGNUP and HOST_SELECTED)
     - Examples:
       - `["SELF_SIGNUP"]` = only self-signup allowed
       - `["HOST_SELECTED"]` = only host-selected allowed
       - `["SELF_SIGNUP", "HOST_SELECTED"]` = both allowed, user chooses
       - `null` or `[]` = all methods available
   - Add `default_signup_method: str | None`
     - Pre-selected value in UI dropdown when creating game
     - Must be one of the allowed_signup_methods if both are specified
     - If null, first allowed method is selected by default

2. **GameSession** (stores the selected method):
   - Add `signup_method: str` (non-nullable, defaults to SELF_SIGNUP)
   - Stores which method was selected when game was created
   - Used at runtime to control Discord button behavior

**Example Template Configurations**:
- **D&D Campaign** template: `allowed_signup_methods=["HOST_SELECTED"]`, `default_signup_method="HOST_SELECTED"` → Host curates the party
- **Open Board Game Night** template: `allowed_signup_methods=["SELF_SIGNUP"]`, `default_signup_method="SELF_SIGNUP"` → Anyone can join
- **Flexible Game** template: `allowed_signup_methods=["SELF_SIGNUP", "HOST_SELECTED"]`, `default_signup_method="SELF_SIGNUP"` → Host decides per game

**Button Control Logic**:
```python
# In services/bot/views/game_view.py GameView.__init__()
self.join_button.disabled = is_started or (signup_method == SignupMethod.HOST_SELECTED)
```

### Implementation Strategy

**Phase 1: Backend Schema and Model** (1-2 hours)

1. **Create SignupMethod Enum** (shared/models/signup_method.py)
   - Define StrEnum with SELF_SIGNUP and HOST_SELECTED
   - Add display_name and description properties
   - Export from shared/models/__init__.py

2. **Update GameTemplate Model** (shared/models/template.py)
   - Add `allowed_signup_methods: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)`
   - Add `default_signup_method: Mapped[str | None] = mapped_column(String(50), nullable=True)`
   - Add validation: default must be in allowed list if both specified

3. **Update GameSession Model** (shared/models/game.py)
   - Add `signup_method: Mapped[str] = mapped_column(String(50), default=SignupMethod.SELF_SIGNUP.value)`
   - Import SignupMethod enum for default value

4. **Create Database Migration** (alembic/versions/YYYYMMDD_add_signup_method.py)
   ```python
   def upgrade() -> None:
       # Add fields to game_templates
       op.add_column("game_templates", sa.Column("allowed_signup_methods", sa.JSON(), nullable=True))
       op.add_column("game_templates", sa.Column("default_signup_method", sa.String(50), nullable=True))

       # Add signup_method to game_sessions (nullable first)
       op.add_column("game_sessions", sa.Column("signup_method", sa.String(50), nullable=True))

       # Backfill existing games with SELF_SIGNUP
       op.execute("UPDATE game_sessions SET signup_method = 'SELF_SIGNUP'")

       # Make column non-nullable
       op.alter_column("game_sessions", "signup_method", nullable=False)
   ```

**Phase 2: API Schema and Service** (2-3 hours)

1. **Update Schemas** (shared/schemas/game.py)
   - Add `signup_method: str | None` to GameCreateRequest (optional override)
   - Add `signup_method: str` to GameResponse
   - Add validation: ensure signup_method is valid enum value
   - Update GameTemplate schemas to include signup method fields

2. **Update GameService** (services/api/services/games.py)
   - In `create_game()`: resolve signup_method from request, template default, or SELF_SIGNUP fallback
   - Validate signup_method against template's allowed_signup_methods list
   - Store selected method in GameSession

3. **Update Template API** (services/api/routes/templates.py)
   - Include signup method fields in template responses
   - Allow bot managers to configure signup methods on templates

**Phase 3: Discord Bot Button Control** (1-2 hours)

1. **Update GameView** (services/bot/views/game_view.py)
   - Add `signup_method: str` parameter to `__init__()`
   - Modify join_button disabled logic:
     ```python
     self.join_button.disabled = is_started or (signup_method == SignupMethod.HOST_SELECTED.value)
     ```

2. **Update Message Formatter** (services/bot/formatters/game_message.py)
   - Add signup_method parameter to `format_game_announcement()`
   - Pass signup_method to GameView constructor

3. **Update Event Handlers** (services/bot/events/handlers.py)
   - Include signup_method when creating GameView instances
   - Fetch from game.signup_method field

**Phase 4: Frontend UI** (3-4 hours)

1. **Update GameForm Component** (frontend/src/components/GameForm.tsx)
   - Add `signupMethod` to GameFormData interface
   - Add FormControl with Select dropdown:
     ```tsx
     <FormControl fullWidth>
       <InputLabel>Signup Method</InputLabel>
       <Select
         value={formData.signupMethod}
         onChange={handleChange}
         label="Signup Method"
       >
         {availableSignupMethods.map(method => (
           <MenuItem key={method.value} value={method.value}>
             {method.displayName}
           </MenuItem>
         ))}
       </Select>
       <FormHelperText>{selectedMethodDescription}</FormHelperText>
     </FormControl>
     ```

2. **Update CreateGame Page** (frontend/src/pages/CreateGame.tsx)
   - Fetch available signup methods from selected template
   - Pass to GameForm as prop
   - Auto-select default_signup_method from template
   - Include signup_method in form submission payload

3. **Update Types** (frontend/src/types/index.ts)
   - Add signup_method to GameSession interface
   - Add allowed_signup_methods, default_signup_method to GameTemplate interface
   - Create SignupMethod type/enum

4. **Display Signup Method** (frontend/src/pages/GameDetails.tsx)
   - Show selected signup method in game details view
   - Badge or info display: "Self Signup" vs "Host Selected"

**Phase 5: Testing and Validation** (2-3 hours)

1. **Unit Tests**
   - SignupMethod enum serialization
   - GameService validation of signup methods
   - Button disabled state logic

2. **Integration Tests**
   - Create game with each signup method
   - Verify button state in Discord messages
   - Verify HOST_SELECTED prevents join button clicks

3. **E2E Tests**
   - Template with restricted signup methods
   - Game creation with dropdown selection
   - Discord button behavior verification

## Implementation Guidance

### Objectives
- Add StrEnum-based signup method system with SELF_SIGNUP and HOST_SELECTED
- Store allowed methods and default in GameTemplate (optional, null = all methods)
- Store selected method in GameSession (required, defaults to SELF_SIGNUP)
- Control Discord join button enabled/disabled based on signup method
- Provide dropdown in game creation form with template-driven defaults
- Migrate existing games to SELF_SIGNUP method

### Key Tasks

**Backend Implementation**:
1. Create SignupMethod StrEnum in shared/models/signup_method.py
2. Add signup method fields to GameTemplate and GameSession models
3. Create database migration with backfill for existing games
4. Update GameCreateRequest/GameResponse schemas
5. Implement validation and resolution logic in GameService

**Bot Implementation**:
1. Update GameView to accept signup_method parameter
2. Modify join_button.disabled logic to check signup method
3. Update message formatter to pass signup_method to GameView
4. Update all event handlers that create GameView instances

**Frontend Implementation**:
1. Add signup method fields to TypeScript interfaces
2. Create signup method selector dropdown in GameForm
3. Load available methods from template and auto-select default
4. Include signup_method in game creation payload
5. Display selected method in game details view

### Dependencies
- Python 3.11+ (StrEnum support) - already in use (pyproject.toml)
- Existing template system (already implemented)
- GameSession and GameTemplate models (already implemented)
- Discord button view system (already implemented)

### Success Criteria
- ✅ SignupMethod StrEnum with SELF_SIGNUP and HOST_SELECTED values
- ✅ GameTemplate has allowed_signup_methods (JSON array, nullable) and default_signup_method (string, nullable)
- ✅ GameSession has signup_method (string, non-nullable, defaults to SELF_SIGNUP)
- ✅ Empty/null allowed_signup_methods list means all methods available
- ✅ Game creation form dropdown shows available methods with default selected
- ✅ Discord join button disabled when signup_method = HOST_SELECTED
- ✅ Existing games migrated to SELF_SIGNUP via database migration
- ✅ API validates signup_method against template's allowed list
- ✅ Frontend displays selected signup method in game details
