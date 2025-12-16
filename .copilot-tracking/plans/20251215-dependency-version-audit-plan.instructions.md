---
applyTo: ".copilot-tracking/changes/20251215-dependency-version-audit-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Dependency Version Audit and Upgrade Strategy

## Overview

Systematically audit and upgrade infrastructure services (PostgreSQL, Node.js) and dependency constraints (Python, NPM) to modern versions with improved security, performance, and long-term support.

## Objectives

- Upgrade PostgreSQL 17 to PostgreSQL 18 with clean Alembic migration reset
- Upgrade Node.js 22 to Node.js 24 LTS for extended support
- Modernize Python dependency constraints using compatible release operator (~=)
- Update critical NPM packages (axios, TypeScript) to latest stable versions
- Establish clear upgrade procedures and rollback plans

## Research Summary

### Infrastructure Analysis

- #file:../research/20251215-dependency-version-audit-research.md (Lines 7-64) - PostgreSQL, RabbitMQ, Redis, Python, Node.js version analysis
- PostgreSQL 18: Latest stable, minimal migration complexity, opportunity for Alembic reset
- Node.js 24: Active LTS until April 2026, Node 22 enters maintenance mode April 2025
- Redis 8: Performance improvements but license review required (deferred)

### Database Migration Lessons

- #file:../research/20251215-dependency-version-audit-research.md (Lines 109-116) - Critical lessons from failed Alembic reset
- Alembic autogenerate drops PostgreSQL server defaults if models only use Python-side `default=`
- Alembic cannot detect PostgreSQL functions/triggers without alembic-utils
- Must fix models with `server_default` and register functions/triggers before reset

### Python Dependency Management

- #file:../research/20251215-dependency-version-audit-research.md (Lines 66-132) - Package constraint analysis and recommendations
- Current approach uses unbounded minimum constraints (>=), allows breaking changes
- Recommended approach: Compatible release operator (~=) for automatic patches, blocked majors
- Key packages outdated: fastapi (0.104→0.115), pydantic (2.5→2.10), cryptography (41→44)

### NPM Package Status

- #file:../research/20251215-dependency-version-audit-research.md (Lines 134-173) - Recently upgraded and remaining updates
- Recent upgrades: React 19, MUI 7, ESLint 9, Vite 6, React Router 7 (completed)
- Remaining updates: axios (1.6→1.7), TypeScript (5.3→5.7), optional Vite 7 upgrade

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding standards

## Implementation Checklist

### [x] Phase 1: PostgreSQL 18 Upgrade + Alembic Reset

- [x] Task 1.1: Fix SQLAlchemy models to include server_default declarations
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 17-42)

- [x] Task 1.2: Install and configure alembic-utils for functions/triggers
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 44-70)

- [x] Task 1.3: Update PostgreSQL image references to 18-alpine
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 72-88)

- [x] Task 1.4: Reset Alembic migration history with corrected models
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 90-116)

- [x] Task 1.5: Verify database schema and services
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 118-132)

### [ ] Phase 2: Node.js 24 LTS Upgrade

- [ ] Task 2.1: Update Node.js base images
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 136-159)

- [ ] Task 2.2: Test frontend builds and CI/CD
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 161-175)

### [ ] Phase 3: Python Dependency Modernization

- [ ] Task 3.1: Update pyproject.toml with compatible release constraints
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 179-197)

- [ ] Task 3.2: Upgrade packages and validate
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 199-217)

### [ ] Phase 4: NPM Package Updates

- [ ] Task 4.1: Update axios and TypeScript
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 221-238)

- [ ] Task 4.2: Evaluate and optionally upgrade Vite 7
  - Details: .copilot-tracking/details/20251215-dependency-version-audit-details.md (Lines 240-259)

## Dependencies

- Docker and Docker Compose (installed)
- Python 3.13 with uv (installed in dev container)
- Node.js and npm (for local frontend development)
- Git (for version control)
- Access to all compose files and Dockerfiles

## Success Criteria

- PostgreSQL 18-alpine running with clean single-migration Alembic history
- All database tables match current model definitions with correct schema
- Node.js 24-alpine images build successfully for frontend
- Python packages use compatible release constraints (~=) and upgrade cleanly
- All test suites pass (unit, integration, e2e)
- No deprecation warnings in logs
- CI/CD pipeline passes successfully
- All services start and connect properly
- Documentation updated with upgrade procedures
