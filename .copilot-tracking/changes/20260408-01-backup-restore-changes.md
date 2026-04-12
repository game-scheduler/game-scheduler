---
plan: '.copilot-tracking/planning/plans/20260408-01-backup-restore.plan.md'
---

# Change Record: Backup and Restore

## Summary

Implement automated 12-hour Postgres backups to S3-compatible storage and a script-driven restore flow, including post-restore orphaned Discord embed cleanup.

## Changes

### Phase 1: INIT_ROLES_ONLY Flag

#### Added

- `tests/unit/init/test_init_roles_only.py` — unit tests for INIT_ROLES_ONLY environment variable behavior in the init service

#### Modified

- `services/init/main.py` — added INIT_ROLES_ONLY environment variable check that exits after phase 2 (role creation) when set to a truthy value

### Phase 2: backup_metadata Model and Migration

#### Added

- `tests/unit/models/test_backup_metadata.py` — unit tests for BackupMetadata ORM model confirming table name and column types
- `shared/models/backup_metadata.py` — BackupMetadata SQLAlchemy model with id and backed_up_at columns
- `alembic/versions/20260408_add_backup_metadata.py` — Alembic migration creating the backup_metadata table

#### Modified

- `shared/models/__init__.py` — exported BackupMetadata from shared models package

### Phase 3: Backup Infrastructure

#### Added

- `docker/backup.Dockerfile` — multi-stage Dockerfile for the backup service using postgres:17-alpine and AWS CLI
- `docker/backup-script.sh` — backup script that inserts a backup_metadata row, runs pg_dump to S3, and retains the last N backups
- `docker/backup-entrypoint.sh` — entrypoint that runs the backup on a 12-hour cron schedule

### Phase 4: Compose Changes

#### Added

- `compose.restore.yaml` — Docker Compose override for the one-shot restore workflow

#### Modified

- `compose.yaml` — added backup service under the `backup` profile using a cron-based schedule
- `config.template/env.template` — added backup-related environment variables (S3 bucket, prefix, region, endpoint, access key, secret key, retain count)

### Phase 5: Restore Script

#### Added

- `scripts/restore.sh` — interactive restore script that lists available backups from S3, prompts for selection and confirmation, and runs the restore via Docker Compose

### Phase 6: Orphaned Embed Sweep

#### Added

- `tests/unit/bot/test_sweep_orphaned_embeds.py` — unit tests for \_sweep_orphaned_embeds covering: no backup_metadata rows (skip), rows present with missing game (delete), rows present with existing game (no delete)

#### Modified

- `services/bot/bot.py` — added \_sweep_orphaned_embeds coroutine that deletes Discord embeds for games absent from the DB after a restore, called from on_ready and on_resumed via \_trigger_sweep
