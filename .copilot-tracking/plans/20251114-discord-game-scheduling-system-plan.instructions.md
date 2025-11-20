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

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 12-27)

- [x] Task 1.2: Configure PostgreSQL database with schema

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 29-48)

- [x] Task 1.3: Set up RabbitMQ message broker

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 50-65)

- [x] Task 1.4: Configure Redis for caching

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 67-79)

- [x] Task 1.5: Create shared data models package
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 81-96)

### [x] Phase 2: Discord Bot Service

- [x] Task 2.1: Initialize discord.py bot with Gateway connection

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 98-114)

- [x] Task 2.2: Implement slash commands for game management

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 116-136)

- [x] Task 2.3: Build game announcement message formatter with buttons

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 138-159)

- [x] Task 2.4: Implement button interaction handlers

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 161-181)

- [x] Task 2.5: Set up RabbitMQ event publishing and subscriptions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 183-200)

- [x] Task 2.6: Implement role authorization checks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 202-217)

### [x] Phase 3: Web API Service

- [x] Task 3.1: Initialize FastAPI application with middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 219-234)

- [x] Task 3.2: Implement Discord OAuth2 authentication flow

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 236-257)

- [x] Task 3.3: Create role-based authorization middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 259-275)

- [x] Task 3.4: Build guild and channel configuration endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 277-297)

- [x] Task 3.5: Implement game management endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 299-324)

- [x] Task 3.6: Build display name resolution service

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 326-347)

- [x] Task 3.7: Implement settings inheritance resolution logic
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 349-365)

### [x] Phase 4: Web Dashboard Frontend

- [x] Task 4.1: Set up React application with Material-UI

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 435-450)

- [x] Task 4.2: Implement OAuth2 login flow with redirect handling

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 452-467)

- [x] Task 4.3: Build guild and channel management pages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 469-487)

- [x] Task 4.4: Create game management interface

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 489-511)

- [x] Task 4.5: Implement participant pre-population with validation
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 513-534)

### [x] Phase 5: Scheduler Service

- [x] Task 5.1: Set up Celery worker with RabbitMQ broker

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 367-382)

- [x] Task 5.2: Implement notification check task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 384-401)

- [x] Task 5.3: Build notification delivery task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 403-417)

- [x] Task 5.4: Add game status update tasks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 419-433)

### [ ] Phase 6: Refactor Host from Participants

- [x] Task 6.1: Remove host from participants during game creation

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 691-707)

- [ ] Task 6.2: Update API responses to show host separately

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 709-727)

- [ ] Task 6.3: Update database migration for existing data

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 729-744)

- [ ] Task 6.4: Update frontend to display host separately
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 746-763)

### [ ] Phase 7: Min Players Field Implementation

- [ ] Task 7.1: Add min_players field to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 927-943)

- [ ] Task 7.2: Update schemas to include min_players

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 945-957)

- [ ] Task 7.3: Implement validation and service logic

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 959-971)

- [ ] Task 7.4: Update frontend to handle min_players
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 973-990)

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

### [ ] Phase 8: Description and Signup Instructions Fields

- [ ] Task 8.1: Add description and signup_instructions fields to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1000-1014)

- [ ] Task 8.2: Update schemas to include description and signup_instructions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1016-1030)

- [ ] Task 8.3: Update service and bot logic to handle new fields

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1032-1045)

- [ ] Task 8.4: Update frontend to display and edit new fields
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1047-1065)

### [ ] Phase 9: Bot Managers Role List

- [ ] Task 9.1: Add botManagerRoleIds field to GuildConfiguration model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1077-1092)

- [ ] Task 9.2: Update schemas and permissions middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1094-1110)

- [ ] Task 9.3: Implement Bot Manager authorization in game routes

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1112-1131)

- [ ] Task 9.4: Update bot commands and frontend for Bot Manager configuration
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1133-1149)
- Bot Manager roles can be configured by guild admins
- Bot Managers have permission to edit/delete any game in their guild
- Authorization correctly distinguishes between hosts, Bot Managers, and admins
- Permission checks cached and performant

### [ ] Phase 10: Notify Roles Field

- [ ] Task 10.1: Add notifyRoleIds field to GameSession model

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1152-1165)

- [ ] Task 10.2: Update schemas to include notifyRoleIds

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1167-1183)

- [ ] Task 10.3: Implement role mention formatting in bot announcements

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1185-1201)

- [ ] Task 10.4: Update frontend for role selection
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 1203-1222)
- Notify roles field validated and stored correctly
- Role mentions appear in Discord game announcements
- Users with mentioned roles receive Discord notifications
- Frontend allows role selection with visual indicators

### [ ] Phase 11: Integration & Testing

- [ ] Task 11.1: Integration tests for inter-service communication

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 536-551)

- [ ] Task 11.2: End-to-end tests for user workflows

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 553-571)

- [ ] Task 11.3: Load testing for concurrent operations

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 573-587)

- [ ] Task 11.4: Test display name resolution scenarios

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 589-607)

- [ ] Task 11.5: Test pre-populated participants feature
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 609-629)

### [ ] Phase 12: Advanced Features

- [ ] Task 12.1: Implement waitlist support

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 631-645)

- [ ] Task 12.2: Add game templates for recurring sessions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 647-660)

- [ ] Task 12.3: Build calendar export functionality

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 662-674)

- [ ] Task 12.4: Create statistics dashboard
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 676-689)
