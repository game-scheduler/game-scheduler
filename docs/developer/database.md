# Database Schema

This document provides an entity relationship diagram (ERD) of the game scheduler database schema.

## Row-Level Security (RLS)

The following tables have Row-Level Security enabled for guild isolation:

- **game_sessions** - Isolates games by guild_id
- **game_templates** - Isolates templates by guild_id
- **game_participants** - Isolates participants via game_sessions join

RLS policies use the `app.current_guild_ids` session variable to filter rows accessible to the current request. This ensures complete guild isolation at the database layer.

## Entity Relationship Diagram

```mermaid
erDiagram
    guild_configurations ||--o{ channel_configurations : "has"
    guild_configurations ||--o{ game_sessions : "has"
    guild_configurations ||--o{ game_templates : "defines"

    channel_configurations ||--o{ game_sessions : "hosts"
    channel_configurations ||--o| game_templates : "assigned_to"

    users ||--o{ game_sessions : "hosts"
    users ||--o{ game_participants : "participates"

    game_templates ||--o{ game_sessions : "instantiates"

    game_sessions ||--o{ game_participants : "has"
    game_sessions ||--o{ notification_schedule : "schedules"
    game_sessions ||--o{ game_status_schedule : "transitions"

    game_participants ||--o{ notification_schedule : "notifies"

    guild_configurations {
        string id PK
        string guild_id UK "Discord guild ID"
        json bot_manager_role_ids "Role IDs for bot managers"
        datetime created_at
        datetime updated_at
    }

    channel_configurations {
        string id PK
        string guild_id FK
        string channel_id UK "Discord channel ID"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    users {
        string id PK
        string discord_id UK "Discord user ID"
        json notification_preferences
        datetime created_at
        datetime updated_at
    }

    game_templates {
        string id PK
        string guild_id FK "RLS: guild isolation"
        string name
        text description
        int order
        boolean is_default
        string channel_id FK "Locked field"
        json notify_role_ids "Locked field"
        json allowed_player_role_ids "Locked field"
        json allowed_host_role_ids "Locked field"
        int max_players "Pre-populated default"
        int expected_duration_minutes "Pre-populated default"
        json reminder_minutes "Pre-populated default"
        text where "Pre-populated default"
        text signup_instructions "Pre-populated default"
        json allowed_signup_methods "Pre-populated default"
        string default_signup_method "Pre-populated default"
        datetime created_at
        datetime updated_at
    }

    game_sessions {
        string id PK
        string template_id FK
        string title
        text description
        text signup_instructions
        datetime scheduled_at
        text where
        int max_players
        string guild_id FK "RLS: guild isolation"
        string channel_id FK
        string message_id "Discord message ID"
        string host_id FK
        json reminder_minutes
        json notify_role_ids
        json allowed_player_role_ids
        int expected_duration_minutes
        string status "SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED"
        string signup_method "SELF_SIGNUP|HOST_SELECTED"
        binary thumbnail_data
        string thumbnail_mime_type
        binary image_data
        string image_mime_type
        datetime created_at
        datetime updated_at
    }

    game_participants {
        string id PK
        string game_session_id FK "RLS: via game_sessions"
        string user_id FK "NULL for placeholders"
        string display_name "NULL for real users"
        datetime joined_at
        int position_type "8000=HOST_ADDED, 24000=SELF_ADDED"
        int position "Order within type"
    }

    notification_schedule {
        string id PK
        string game_id FK
        int reminder_minutes
        datetime notification_time
        datetime game_scheduled_at
        boolean sent
        string notification_type "reminder|join_notification"
        string participant_id FK "NULL for reminders"
        datetime created_at
    }

    game_status_schedule {
        string id PK
        string game_id FK
        string target_status "Status to transition to"
        datetime transition_time
        boolean executed
        datetime created_at
    }
```

## Key Relationships

### Guild Hierarchy

- **Guilds** (Discord servers) contain channels, templates, and games
- Each guild can have multiple channels configured for game scheduling
- Templates are guild-specific and define game types

### Template System

- Templates define game types (e.g., "D&D Campaign", "Board Game Night")
- **Locked fields**: Set by bot managers, cannot be changed by hosts (channel, role restrictions)
- **Pre-populated fields**: Provide defaults that hosts can override (max players, duration, etc.)

### Game Sessions

- Core entity representing a scheduled game
- Each game is associated with a template (or custom if template_id is NULL)
- Games belong to a guild, are posted in a channel, and are hosted by a user
- Support both self-signup and host-selected participant management

### Participant Management

- Supports two types of participants:
  - **Real users**: `user_id` set, `display_name` NULL (fetched dynamically from Discord)
  - **Placeholders**: `user_id` NULL, `display_name` set (host-entered names)
- Position tracking with two-tier system (type + position within type)

### Notification System

- Database-backed reminders calculated when game is created/updated
- Two notification types:
  - **reminder**: Game-wide notifications sent to all participants
  - **join_notification**: Individual participant join confirmations
- Daemon uses PostgreSQL LISTEN/NOTIFY for efficient event-driven processing

### Status Transitions

- Automated status changes managed by daemon
- Transitions: SCHEDULED → IN_PROGRESS → COMPLETED
- Games can also be manually marked as CANCELLED
