---
applyTo: '.copilot-tracking/changes/20260408-01-backup-restore-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Backup and Restore

## Overview

Implement automated 12-hour Postgres backups to S3-compatible storage and a script-driven restore flow, including post-restore orphaned Discord embed cleanup.

## Objectives

- Automatic 12-hour Postgres backups to S3-compatible storage (AWS S3, Cloudflare R2, Backblaze B2)
- Simple, script-driven restore that is hard to get wrong — no manual Docker or psql steps
- Support Postgres major version upgrades via logical dump/restore
- Post-restore bot startup deletes Discord embeds for games that no longer exist in the DB

## Research Summary

### Project Files

- `compose.yaml` — three named volumes; `cloudflared` profiles pattern for opt-in `backup` service
- `services/init/main.py` — five-phase init; `INIT_ROLES_ONLY` hook added after phase 2
- `services/init/database_users.py` — idempotent role creation; authoritative source for roles
- `config.template/env.template` — existing DB role env vars; backup env vars to be added
- `services/bot/bot.py` — `on_ready` (line 177) and `on_resumed` (line 352) insertion points
- `services/bot/views/game_view.py` — `custom_id=f"join_game_{game_id}"` format (line 81)

### External References

- #file:../research/20260408-01-backup-restore-research.md — full research with verified findings

## Implementation Checklist

### [x] Phase 1: INIT_ROLES_ONLY Flag

- [x] Task 1.1 (Tests): Write tests for INIT_ROLES_ONLY behavior
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 13-26)

- [x] Task 1.2 (Implement): Add INIT_ROLES_ONLY to services/init/main.py
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 27-43)

### [x] Phase 2: backup_metadata Model and Migration

- [x] Task 2.1 (Tests): Write tests for BackupMetadata model
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 46-58)

- [x] Task 2.2 (Implement): Create BackupMetadata SQLAlchemy model
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 59-72)

- [x] Task 2.3: Create Alembic migration for backup_metadata
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 73-88)

### [x] Phase 3: Backup Infrastructure

- [x] Task 3.1: Create backup Dockerfile and scripts
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 91-111)

### [x] Phase 4: Compose Changes

- [x] Task 4.1: Add backup service to compose.yaml
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 114-128)

- [x] Task 4.2: Create compose.restore.yaml
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 129-143)

- [x] Task 4.3: Add backup env vars to config.template/env.template
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 144-158)

### [ ] Phase 5: Restore Script

- [ ] Task 5.1: Create scripts/restore.sh
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 161-180)

### [ ] Phase 6: Orphaned Embed Sweep

- [ ] Task 6.1 (Tests): Write tests for \_sweep_orphaned_embeds
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 183-196)

- [ ] Task 6.2 (Implement): Add \_sweep_orphaned_embeds to services/bot/bot.py
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 197-217)

## Dependencies

- `uv` for Python dependency management
- `docker` and `docker compose` for container orchestration
- AWS CLI (installed in backup Docker image) for S3 operations
- S3-compatible storage bucket with credentials

## Success Criteria

- `docker compose --profile backup up -d` starts automated backup without affecting other services
- `scripts/restore.sh` completes a full restore with no manual steps beyond selection and confirmation
- After restore, `docker compose up -d` starts all services and Alembic migrates forward from backup revision
- Restore works for Postgres major version upgrades
- Bot startup after restore deletes all Discord embeds whose game UUIDs are absent from the DB
- Fresh installs (no `backup_metadata` rows) skip the embed sweep entirely
- All new unit tests pass
