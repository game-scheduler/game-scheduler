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

### [x] Phase 5: Restore Script

- [x] Task 5.1: Create scripts/restore.sh
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 161-180)

### [x] Phase 6: Orphaned Embed Sweep

- [x] Task 6.1 (Tests): Write tests for \_sweep_orphaned_embeds
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 183-196)

- [x] Task 6.2 (Implement): Add \_sweep_orphaned_embeds to services/bot/bot.py
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 197-217)

### [x] Phase 7: pytest backup Marker and E2E Test Infrastructure

- [x] Task 7.1: Add backup pytest marker to pyproject.toml
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 239-253)

- [x] Task 7.2: Add MinIO service and init container to compose.e2e.yaml
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 254-268)

- [x] Task 7.3: Add backup env vars to config/env.e2e
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 269-283)

### [ ] Phase 8: Backup Test Files

- [ ] Task 8.1: Create tests/backup/ package and conftest
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 286-300)

- [ ] Task 8.2: Create test_backup_create_game_a.py (Phase 1)
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 301-314)

- [ ] Task 8.3: Create test_backup_create_game_b.py (Phase 2)
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 315-329)

- [ ] Task 8.4: Create test_backup_post_restore.py (Phases 3 and 4)
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 330-348)

### [ ] Phase 9: Test Runner and Operator Scripts

- [ ] Task 9.1: Create scripts/run-backup-tests.sh
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 351-367)

- [ ] Task 9.2: Create scripts/backup-now.sh
  - Details: .copilot-tracking/planning/details/20260408-01-backup-restore-details.md (Lines 368-382)

## Dependencies

- `uv` for Python dependency management
- `docker` and `docker compose` for container orchestration
- AWS CLI (installed in backup Docker image) for S3 operations
- S3-compatible storage bucket with credentials
- MinIO Docker image (`minio/minio`) for local S3 in backup tests
- MinIO Client image (`minio/mc`) for test bucket initialization

## Success Criteria

- `docker compose --profile backup up -d` starts automated backup without affecting other services
- `scripts/restore.sh` completes a full restore with no manual steps beyond selection and confirmation
- After restore, `docker compose up -d` starts all services and Alembic migrates forward from backup revision
- Restore works for Postgres major version upgrades
- Bot startup after restore deletes all Discord embeds whose game UUIDs are absent from the DB
- Fresh installs (no `backup_metadata` rows) skip the embed sweep entirely
- All new unit tests pass
- `scripts/run-backup-tests.sh` completes with all backup pytest phases passing
- After restore, gameA row exists and gameB row is absent from DB
- After restore, gameB's Discord embed is deleted (verified via Discord API)
- Cron test confirms `backup-script.sh` runs within 90s with `* * * * *` schedule
- No real AWS credentials required; MinIO serves all S3 operations locally
