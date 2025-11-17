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

### [ ] Phase 2: Discord Bot Service

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

- [ ] Task 2.6: Implement role authorization checks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 202-217)

### [ ] Phase 3: Web API Service

- [ ] Task 3.1: Initialize FastAPI application with middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 219-234)

- [ ] Task 3.2: Implement Discord OAuth2 authentication flow

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 236-257)

- [ ] Task 3.3: Create role-based authorization middleware

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 259-275)

- [ ] Task 3.4: Build guild and channel configuration endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 277-297)

- [ ] Task 3.5: Implement game management endpoints

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 299-324)

- [ ] Task 3.6: Build display name resolution service

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 326-347)

- [ ] Task 3.7: Implement settings inheritance resolution logic
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 349-365)

### [ ] Phase 4: Scheduler Service

- [ ] Task 4.1: Set up Celery worker with RabbitMQ broker

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 367-382)

- [ ] Task 4.2: Implement notification check task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 384-401)

- [ ] Task 4.3: Build notification delivery task

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 403-417)

- [ ] Task 4.4: Add game status update tasks
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 419-433)

### [ ] Phase 5: Web Dashboard Frontend

- [ ] Task 5.1: Set up React application with Material-UI

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 435-450)

- [ ] Task 5.2: Implement OAuth2 login flow with redirect handling

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 452-467)

- [ ] Task 5.3: Build guild and channel management pages

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 469-487)

- [ ] Task 5.4: Create game management interface

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 489-511)

- [ ] Task 5.5: Implement participant pre-population with validation
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 513-534)

### [ ] Phase 6: Integration & Testing

- [ ] Task 6.1: Integration tests for inter-service communication

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 536-551)

- [ ] Task 6.2: End-to-end tests for user workflows

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 553-571)

- [ ] Task 6.3: Load testing for concurrent operations

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 573-587)

- [ ] Task 6.4: Test display name resolution scenarios

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 589-607)

- [ ] Task 6.5: Test pre-populated participants feature
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 609-629)

### [ ] Phase 7: Advanced Features

- [ ] Task 7.1: Implement waitlist support

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 631-645)

- [ ] Task 7.2: Add game templates for recurring sessions

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 647-660)

- [ ] Task 7.3: Build calendar export functionality

  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 662-674)

- [ ] Task 7.4: Create statistics dashboard
  - Details: .copilot-tracking/details/20251114-discord-game-scheduling-system-details.md (Lines 676-689)

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
