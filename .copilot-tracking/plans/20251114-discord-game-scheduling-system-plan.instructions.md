---
applyTo: ".copilot-tracking/changes/20251114-discord-game-scheduling-system-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Game Scheduling System

## Overview

Implement a complete Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support with settings inheritance, and automated notifications.

## Objectives

- Enable Discord users to create game sessions through web dashboard and join games via Discord buttons
- Implement Discord OAuth2 authentication with role-based authorization using guild roles
- Support multiple channels per guild with hierarchical settings inheritance (Guild → Channel → Game)
- Use Discord mention format for automatic display name resolution in messages
- Implement display name resolution service for web interface rendering
- Send automated notifications before games start with inherited reminder settings
- Support pre-populated participants with @mention validation and placeholder strings
- Build microservices architecture with independent scaling and reliable event-driven communication

## Research Summary

### Project Files

- No existing project files - greenfield implementation

### External References

- #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1-1612) - Complete system research
- #githubRepo:"Rapptz/discord.py button interactions" - Discord.py button patterns
- #githubRepo:"tiangolo/fastapi oauth2" - FastAPI OAuth2 implementations
- #fetch:https://discord.com/developers/docs/intro - Discord API documentation
- #fetch:https://discord.com/developers/docs/interactions/message-components - Button components
- #fetch:https://discord.com/developers/docs/topics/oauth2 - OAuth2 authentication

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices

## Implementation Checklist

### [x] Phase 1: Infrastructure Setup

- [x] Task 1.1: Create Docker development environment

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 11-30)

- [x] Task 1.2: Configure PostgreSQL database with schema

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 32-56)

- [x] Task 1.3: Set up RabbitMQ message broker

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 58-78)

- [x] Task 1.4: Configure Redis for caching

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 80-98)

- [x] Task 1.5: Create shared data models package
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 100-121)

### [x] Phase 2: Discord Bot Service

- [x] Task 2.1: Initialize discord.py bot with Gateway connection

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 123-142)

- [x] Task 2.2: Implement slash commands for game management

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 144-167)

- [x] Task 2.3: Build game announcement message formatter with buttons

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 169-187)

- [x] Task 2.4: Implement button interaction handlers

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 189-209)

- [x] Task 2.5: Set up RabbitMQ event publishing and subscriptions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 211-229)

- [x] Task 2.6: Implement role authorization checks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 231-255)

### [x] Phase 3: Web API Service

- [x] Task 3.1: Initialize FastAPI application with middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 257-279)

- [x] Task 3.2: Implement Discord OAuth2 authentication flow

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 281-303)

- [x] Task 3.3: Create role-based authorization middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 305-324)

- [x] Task 3.4: Build guild and channel configuration endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 326-347)

- [x] Task 3.5: Implement game management endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 349-371)

- [x] Task 3.6: Build display name resolution service

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 373-393)

- [x] Task 3.7: Implement settings inheritance resolution logic
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 395-415)

### [x] Phase 4: Web Dashboard Frontend

- [x] Task 4.1: Set up React application with Material-UI

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 417-440)

- [x] Task 4.2: Implement OAuth2 login flow with redirect handling

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 442-463)

- [x] Task 4.3: Build guild and channel management pages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 465-486)

- [x] Task 4.4: Create game management interface

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 488-512)

- [x] Task 4.5: Implement participant pre-population with validation
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 514-538)

### [x] Phase 5: Scheduler Service

- [x] Task 5.1: Set up Celery worker with RabbitMQ broker

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 540-561)

- [x] Task 5.2: Implement notification check task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 563-583)

- [x] Task 5.3: Build notification delivery task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 585-603)

- [x] Task 5.4: Add game status update tasks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 605-625)

### [x] Phase 6: Refactor Host from Participants

- [x] Task 6.1: Remove host from participants during game creation

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 627-644)

- [x] Task 6.2: Update API responses to show host separately

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 646-662)

- [x] Task 6.3: Update database migration for existing data

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 664-678)

- [x] Task 6.4: Update frontend to display host separately
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 680-711)

### [x] Phase 7: Min Players Field Implementation

- [x] Task 7.1: Add min_players field to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 713-728)

- [x] Task 7.2: Update schemas to include min_players

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 730-746)

- [x] Task 7.3: Implement validation and service logic

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 748-764)

- [x] Task 7.4: Update frontend to handle min_players
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 766-785)

## Dependencies

- Python 3.11+ with async/await support
- PostgreSQL 15+ for primary data store
- RabbitMQ 3.12+ for message broker
- Redis 7+ for caching and Celery backend
- Docker and Docker Compose for containerization
- Discord Application with bot token and OAuth2 credentials
- discord.py v2.x for bot framework
- FastAPI for web API framework
- SQLAlchemy 2.0 for async ORM
- Celery for distributed task queue
- React with Material-UI for frontend

## Success Criteria

- Users authenticate via Discord OAuth2 with role-based permissions
- Game hosts create games via web dashboard with timezone support
- Discord bot posts announcements to configured channels with interactive buttons
- Players join/leave via buttons with immediate feedback (< 3 seconds)
- Discord messages use mention format for automatic display name resolution
- Web interface resolves and displays correct guild-specific display names
- Participant list synchronized between Discord and database in real-time
- Notifications sent reliably at scheduled times using inherited reminder settings
- System supports multiple channels per guild with independent configurations
- Game settings properly inherit from channel → guild hierarchy
- Role-based authorization works for game creation and management
- Game hosts can pre-populate participants with validated @mentions
- Invalid @mentions fail with clear validation errors and disambiguation
- Placeholder strings reserve slots for non-Discord users
- Services can be deployed and scaled independently
- System recovers gracefully from individual service failures
- Message delivery guaranteed via RabbitMQ acknowledgments
- Host is stored separately from participants list
- Host does not appear in participant count
- API responses clearly separate host from participants
- Frontend displays host with visual distinction from players

- Min players field validated and stored correctly
- API prevents min_players > max_players
- Frontend displays min-max participant count (X/min-max format)
- Minimum player threshold enforced in game management
- Description and signup instructions fields stored and displayed correctly
- Discord messages include truncated description
- Game cards show description preview with "Read more" option
- Signup instructions visible near Join button

### [x] Phase 8: Description and Signup Instructions Fields

- [x] Task 8.1: Add description and signup_instructions fields to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 787-800)

- [x] Task 8.2: Update schemas to include description and signup_instructions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 802-820)

- [x] Task 8.3: Update service and bot logic to handle new fields

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 822-838)

- [x] Task 8.4: Update frontend to display and edit new fields
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 840-861)

### [x] Phase 9: Bot Managers Role List

- [x] Task 9.1: Add botManagerRoleIds field to GuildConfiguration model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 863-877)

- [x] Task 9.2: Update schemas and permissions middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 879-896)

- [x] Task 9.3: Implement Bot Manager authorization in game routes

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 898-915)

- [x] Task 9.4: Update bot commands and frontend for Bot Manager configuration
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 917-940)
- Bot Manager roles can be configured by guild admins
- Bot Managers have permission to edit/delete any game in their guild
- Authorization correctly distinguishes between hosts, Bot Managers, and admins
- Permission checks cached and performant

### [x] Phase 10: Notify Roles Field

- [x] Task 10.1: Add notifyRoleIds field to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 942-956)

- [x] Task 10.2: Update schemas to include notifyRoleIds

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 958-975)

- [x] Task 10.3: Implement role mention formatting in bot announcements

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 977-994)

- [x] Task 10.4: Update frontend for role selection

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 996-1019)

- [x] Task 10.5: Fix compile errors

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1021-1032)

- Notify roles field validated and stored correctly
- Role mentions appear in Discord game announcements
- Users with mentioned roles receive Discord notifications
- Frontend allows role selection with visual indicators

### [ ] Phase 11: Bug Fixes

- [x] Task 11.1: Fix missing default values for min/max players in create game form

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1036-1052)

- [x] Task 11.2: Fix game time default value to use current time

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1054-1070)

- [x] Task 11.3: Auto-select channel when only one is available

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1072-1092)

- [x] Task 11.4: Move Scheduled Time field to top of game display and edit pages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1094-1115)

- [x] Task 11.5: Move Channel field under Scheduled Time field on game display and edit pages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1117-1138)

- [x] Task 11.6: Move reminder box directly below scheduled time box

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1140-1165)

- [x] Task 11.7: Fix all unit test and lint messages for Python and TypeScript

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1167-1192)

- [x] Task 11.8: Install eslint and prettier and fix any issues found

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1191-1217)

- [x] Task 11.9: Display min players and max players on the same line

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1219-1240)

- [x] Task 11.10: Remove the rules field

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1241-1281)

- [x] Task 11.11: Fix API crash when specifying an @user

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1283-1320)

### [ ] Phase 12: Enhance functionality

- [x] Task 12.1: Implement waitlist support

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1311-1328)

- [x] Task 12.2: Change pre-filled participant ordering to use explicit position

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1330-1356)

- [x] Task 12.3: Fix default_rules related problem in bot

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1358-1376)

- [x] Task 12.4: Refactor Create/Edit Game Pages with Shared Form Component

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1378-1602)

- [x] Task 12.5: Integrate EditableParticipantList into GameForm Component

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1601-1693)

- [x] Task 12.6: Replace adaptive backoff with Redis-based rate limiting

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1694-1711)

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1694-1711)
  - Simplify message update throttling by replacing in-memory state tracking with Redis cache
  - Use Redis key existence check with 1.5s TTL for rate limiting
  - Maintains instant updates when idle, simpler code, multi-instance ready
  - Research: .copilot-tracking/research/20251122-redis-rate-limiting-research.md

- [x] Task 12.7: Change "Pre-Populated" to "Added by host" on web pages and messages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1712-1731)

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1712-1731)
  - Update all frontend components to use "Added by host" terminology
  - Update Discord bot message formatters to use "Added by host"
  - Ensure consistent terminology across all user-facing text

- [x] Task 12.8: Change "Guild" to "Server" on web pages and messages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1732-1754)

  - Update all frontend components to use "Server" instead of "Guild"
  - Update Discord bot messages to use "Server" terminology
  - Keep internal code and database models using "guild" for Discord API consistency
  - Only change user-facing text and UI labels

- [x] Task 12.9: Send notification of waitlist clearing

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1756-1785)

  - Notify users when they move from overflow to confirmed participant list
  - Triggered by: player removal, max_players increase, or host reordering
  - Send DM with game details and confirmation message
  - Update message immediately to reflect promotion

- [x] Task 12.10: Fix participant count to include placeholder participants

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1787-1812)

  - Update participant_count calculation to include both Discord users and placeholder participants
  - Ensure "My Games" screen shows accurate player counts
  - Match displayed participant list count in game details

- [x] Task 12.11: Add play time field for expected game duration

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1814-1851)

  - Add expected_duration_minutes field to track how long game will run
  - Display on My Games summary, game details, and Discord messages
  - Position on same line as Reminder times in create/edit forms

- [x] Task 12.12: Rename "Allowed Host Role IDs" to "Host Roles" on server configuration

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1853-1873)

  - Simplify label from "Allowed Host Role IDs" to "Host Roles" on server config
  - Update channel config label from "Allowed Host Role IDs (override)" to "Host Roles (override)"
  - Keep helper text and functionality unchanged

- [x] Task 12.13: Convert role ID fields to multi-select dropdowns with actual server roles

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1875-1910)

  - Replace text input fields with Material-UI Autocomplete multi-select components
  - Fetch and display actual role names from the server using existing /roles endpoint
  - Apply to Host Roles and Bot Manager Roles fields on server configuration page
  - Apply to Host Roles (override) field on channel configuration page

- [x] Task 12.14: Upgrade Docker Compose for multi-architecture builds with Docker Bake

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1925-2035)

  - Configure docker-compose.yml with x-bake sections for multi-architecture support
  - Add tags and platforms configuration for linux/arm64 and linux/amd64
  - Use `docker buildx bake --push` command for building and pushing multi-arch images
  - Support environment variables for registry prefix and image tags
  - Document Docker Bake workflow in README.md

- [x] Task 12.15: Fix bot manager role changes not saving in API responses

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 2037-2064)

  - Add bot_manager_role_ids field to all GuildConfigResponse constructions in guilds.py
  - Ensure bot manager roles are returned when fetching guild configuration
  - Verify frontend receives and displays bot manager role selections correctly
  - Fix issue where bot manager role changes appear to save but don't persist

- [ ] Task 12.16: Fix notifications not being sent to game participants

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 2066-2102)

  - Diagnose and fix notification system end-to-end
  - Verify scheduler service is running and checking for games
  - Verify Celery beat is scheduling notification check tasks
  - Verify notification events are being published to RabbitMQ
  - Verify bot service is consuming and handling notification events
  - Test complete notification flow with actual game

### [ ] Phase 13: Additional Functionality

- [ ] Task 13.1: Add game templates for recurring sessions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1989-2007)

- [ ] Task 13.2: Build calendar export functionality

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 2009-2027)

- [ ] Task 13.3: Create statistics dashboard

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 2029-2044)
