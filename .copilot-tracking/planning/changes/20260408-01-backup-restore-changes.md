<!-- markdownlint-disable-file -->

# Task Changes: Backup and Restore

## Overview

Implement automated 12-hour Postgres backups to S3-compatible storage and a script-driven restore flow, including post-restore orphaned Discord embed cleanup.

## Phase 1: INIT_ROLES_ONLY Flag — COMPLETE

### Added

- `tests/unit/services/init/test_main_roles_only.py` — Four unit tests covering: flag set → exits 0 after role creation, skips migrations/schema/rabbitmq; flag set → logs INIT_ROLES_ONLY message; flag absent → all five phases run; flag empty → all five phases run.

### Modified

- `services/init/main.py` — Added `import os`; added `INIT_ROLES_ONLY` check after `create_database_users()` that logs and returns 0 immediately when truthy, skipping migrations, schema verification, and RabbitMQ init.

---

## Phase 2: backup_metadata Model and Migration — COMPLETE

### Added

- `shared/models/backup_metadata.py` — BackupMetadata ORM model mapping to backup_metadata table with integer PK and TIMESTAMPTZ backed_up_at column.
- `alembic/versions/20260412_add_backup_metadata.py` — Migration creating the backup_metadata table; downgrade drops it.
- `tests/unit/shared/models/test_backup_metadata.py` — Five unit tests covering table name, pk, column nullability, instantiation, and **all** export.

### Modified

- `shared/models/__init__.py` — Added BackupMetadata import and export.

---

## Phase 3: Backup Infrastructure — NOT STARTED

### Added

### Modified

### Removed

---

## Phase 4: Compose Changes — NOT STARTED

### Added

### Modified

### Removed

---

## Phase 5: Restore Script — NOT STARTED

### Added

### Modified

### Removed

---

## Phase 6: Orphaned Embed Sweep — NOT STARTED

### Added

### Modified

### Removed
