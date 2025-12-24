# Microservice Communication Architecture

## System Architecture Diagram

```mermaid
graph TB
    %% External Services
    Discord[Discord API<br/>External Service]

    %% Core Services
    API[API Service<br/>FastAPI REST]
    Bot[Bot Service<br/>discord.py Gateway]
    NotifDaemon[Notification Daemon<br/>Scheduler]
    StatusDaemon[Status Transition Daemon<br/>Scheduler]
    Init[Init Service<br/>One-time Setup]

    %% Infrastructure
    PG[(PostgreSQL<br/>Database)]
    RMQ[RabbitMQ<br/>Event Broker]
    Redis[(Valkey/Redis<br/>Cache)]

    %% Frontend
    Frontend[Frontend<br/>React SPA]

    %% Infrastructure connections
    API -->|SQL Queries| PG
    Bot -->|SQL Queries| PG
    NotifDaemon -->|SQL Queries| PG
    StatusDaemon -->|SQL Queries| PG
    Init -->|Migrations & Seeds| PG

    API -->|Cache| Redis
    Bot -->|Cache| Redis

    %% Event flow from API
    API -->|GAME_CREATED| RMQ
    API -->|GAME_UPDATED| RMQ
    API -->|GAME_CANCELLED| RMQ
    API -->|PLAYER_REMOVED| RMQ
    API -->|NOTIFICATION_SEND_DM| RMQ

    %% Event flow from Daemons
    NotifDaemon -->|NOTIFICATION_DUE| RMQ
    StatusDaemon -->|GAME_STATUS_TRANSITION_DUE| RMQ

    %% Bot consumes all events
    RMQ -->|All Events| Bot

    %% Bot to Discord
    Bot <-->|Gateway WebSocket| Discord

    %% Frontend connections
    Frontend -->|HTTP REST| API
    Frontend -->|OAuth Redirect| API

    %% Daemon polling patterns
    PG -.->|LISTEN/NOTIFY<br/>notification_schedule| NotifDaemon
    PG -.->|LISTEN/NOTIFY<br/>game_status_schedule| StatusDaemon

    %% Styling
    classDef tested fill:#90EE90,stroke:#333,stroke-width:2px
    classDef untested fill:#FFB6C1,stroke:#333,stroke-width:2px
    classDef infrastructure fill:#87CEEB,stroke:#333,stroke-width:2px
    classDef external fill:#DDA0DD,stroke:#333,stroke-width:2px

    class API,Bot,NotifDaemon tested
    class StatusDaemon untested
    class PG,RMQ,Redis infrastructure
    class Discord,Frontend external
```

## Event Communication Paths

```mermaid
sequenceDiagram
    autonumber

    participant User
    participant Frontend
    participant API
    participant RMQ as RabbitMQ
    participant Bot
    participant NotifD as Notification<br/>Daemon
    participant StatusD as Status<br/>Daemon
    participant DB as PostgreSQL
    participant Discord

    %% Game Creation Flow (TESTED)
    rect rgb(200, 255, 200)
        note right of User: TESTED: Game Creation
        User->>Frontend: Create Game
        Frontend->>API: POST /games
        API->>DB: Insert game_sessions
        API->>DB: Insert game_status_schedule (2 entries)
        API->>RMQ: Publish GAME_CREATED
        RMQ->>Bot: Consume GAME_CREATED
        Bot->>Discord: Post announcement message
        Discord-->>Bot: message_id
        Bot->>DB: Update game.message_id
    end

    %% Game Update Flow (TESTED)
    rect rgb(200, 255, 200)
        note right of User: TESTED: Game Update
        User->>API: PUT /games/{id}
        API->>DB: Update game_sessions
        API->>RMQ: Publish GAME_UPDATED
        RMQ->>Bot: Consume GAME_UPDATED
        Bot->>Discord: Edit message
    end

    %% Game Cancellation Flow (UNTESTED)
    rect rgb(255, 200, 200)
        note right of User: UNTESTED: Game Cancellation
        User->>API: DELETE /games/{id}
        API->>DB: Update game.status = CANCELLED
        API->>RMQ: Publish GAME_CANCELLED
        RMQ->>Bot: Consume GAME_CANCELLED
        Bot->>Discord: Update/Delete message
    end

    %% Player Removal Flow (UNTESTED)
    rect rgb(255, 200, 200)
        note right of User: UNTESTED: Player Removal
        User->>API: DELETE /games/{id}/participants/{user_id}
        API->>DB: Delete participant
        API->>RMQ: Publish PLAYER_REMOVED
        RMQ->>Bot: Consume PLAYER_REMOVED
        Bot->>Discord: Send DM to removed user
        Bot->>Discord: Edit game message
    end

    %% Notification Daemon Flow - Reminders (TESTED)
    rect rgb(200, 255, 200)
        note right of NotifD: TESTED: Reminder Notifications
        DB-->>NotifD: NOTIFY notification_schedule_changed
        NotifD->>DB: Query due reminders
        NotifD->>RMQ: Publish NOTIFICATION_DUE (type=reminder)
        RMQ->>Bot: Consume NOTIFICATION_DUE
        Bot->>DB: Load game + participants
        Bot->>Discord: Send DM to each participant
    end

    %% Notification Daemon Flow - Join Notification (UNTESTED)
    rect rgb(255, 200, 200)
        note right of NotifD: UNTESTED: Join Notifications
        NotifD->>DB: Query due join_notifications
        NotifD->>RMQ: Publish NOTIFICATION_DUE (type=join_notification)
        RMQ->>Bot: Consume NOTIFICATION_DUE
        Bot->>Discord: Send signup instructions DM
    end

    %% Waitlist Promotion Flow (UNTESTED)
    rect rgb(255, 200, 200)
        note right of API: UNTESTED: Waitlist Promotion
        API->>DB: Detect promotion (participant moves to active)
        API->>RMQ: Publish NOTIFICATION_SEND_DM
        RMQ->>Bot: Consume NOTIFICATION_SEND_DM
        Bot->>Discord: Send promotion DM
    end

    %% Status Transition Flow (UNTESTED)
    rect rgb(255, 200, 200)
        note right of StatusD: UNTESTED: Status Transitions
        DB-->>StatusD: NOTIFY game_status_schedule_changed
        StatusD->>DB: Query due transitions
        StatusD->>RMQ: Publish GAME_STATUS_TRANSITION_DUE
        RMQ->>Bot: Consume GAME_STATUS_TRANSITION_DUE
        Bot->>DB: Update game.status
        Bot->>Discord: Edit message with new status
    end
```

## Event Type Reference

### API Service Events (Immediate)

| Event Type | Trigger | Bot Action | E2E Test Status |
|------------|---------|------------|-----------------|
| `GAME_CREATED` | POST /games | Post announcement to channel | ✅ Tested |
| `GAME_UPDATED` | PUT /games/{id} | Edit Discord message | ✅ Tested |
| `GAME_CANCELLED` | DELETE /games/{id} | Update/delete message | ❌ Not tested |
| `PLAYER_REMOVED` | DELETE /games/{id}/participants | Send DM + update message | ❌ Not tested |
| `NOTIFICATION_SEND_DM` | Waitlist promotion | Send promotion DM | ❌ Not tested |

### Notification Daemon Events (Scheduled)

| Event Type | Trigger | Bot Action | E2E Test Status |
|------------|---------|------------|-----------------|
| `NOTIFICATION_DUE` (reminder) | Game reminder time reached | Send DM to all participants | ✅ Tested |
| `NOTIFICATION_DUE` (join_notification) | Delayed join notification | Send signup instructions DM | ❌ Not tested |

### Status Transition Daemon Events (Scheduled)

| Event Type | Trigger | Bot Action | E2E Test Status |
|------------|---------|------------|-----------------|
| `GAME_STATUS_TRANSITION_DUE` | scheduled_at or completion time | Update status + edit message | ❌ Not tested |

## Database Trigger Patterns

```mermaid
graph LR
    subgraph "PostgreSQL LISTEN/NOTIFY"
        NS[notification_schedule<br/>table]
        SS[game_status_schedule<br/>table]

        NS -->|INSERT/UPDATE| N1[NOTIFY<br/>notification_schedule_changed]
        SS -->|INSERT/UPDATE| N2[NOTIFY<br/>game_status_schedule_changed]
    end

    subgraph "Daemons"
        ND[Notification Daemon]
        SD[Status Daemon]

        N1 -.->|LISTEN| ND
        N2 -.->|LISTEN| SD
    end

    ND -->|Wake up immediately| Query1[Query MIN<br/>notification_time]
    SD -->|Wake up immediately| Query2[Query MIN<br/>transition_time]
```

## Test Coverage Summary

**Pattern 1: Immediate API Events** - 2/5 tested (40%)
- ✅ GAME_CREATED
- ✅ GAME_UPDATED
- ❌ GAME_CANCELLED
- ❌ PLAYER_REMOVED
- ❌ NOTIFICATION_SEND_DM

**Pattern 2: Scheduled Notification Events** - 1/2 tested (50%)
- ✅ NOTIFICATION_DUE (type=reminder)
- ❌ NOTIFICATION_DUE (type=join_notification)

**Pattern 3: Scheduled Status Events** - 0/1 tested (0%)
- ❌ GAME_STATUS_TRANSITION_DUE

**Overall E2E Coverage**: 3/8 critical paths tested (37.5%)

## Missing Test Files (Recommended)

1. `tests/e2e/test_game_cancellation.py` - Game cancellation flow
2. `tests/e2e/test_player_removal.py` - Player removal DM flow
3. `tests/e2e/test_waitlist_promotion.py` - Waitlist promotion DM flow
4. `tests/e2e/test_join_notification.py` - Delayed join notification flow
5. `tests/e2e/test_game_status_transitions.py` - Status transition daemon flow
