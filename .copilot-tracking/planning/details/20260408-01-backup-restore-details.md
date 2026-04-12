<!-- markdownlint-disable-file -->

# Task Details: Backup and Restore

## Research Reference

**Source Research**: #file:../research/20260408-01-backup-restore-research.md

---

## Phase 1: INIT_ROLES_ONLY Flag

### Task 1.1 (Tests): Write tests for INIT_ROLES_ONLY behavior

Write unit tests verifying that `services/init/main.py` exits 0 after role creation when `INIT_ROLES_ONLY=true`, and proceeds through all five phases when the flag is absent.

- **Files**:
  - `tests/unit/init/test_main_roles_only.py` — new test file
- **Success**:
  - Tests fail (red) before implementation
  - Cases covered: flag set → exits after `create_database_users`; flag absent → all phases run
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 101-115) — INIT_ROLES_ONLY decision and phase sequence
- **Dependencies**:
  - None

### Task 1.2 (Implement): Add INIT_ROLES_ONLY to services/init/main.py

After `create_database_users` phase succeeds, read the `INIT_ROLES_ONLY` env var. If truthy, log and return 0 immediately — skipping migrations, schema verification, and RabbitMQ init.

- **Files**:
  - `services/init/main.py` — add flag check after phase 2 (currently ~line 121)
- **Success**:
  - All Phase 1 tests pass (green)
  - Normal startup unaffected when flag is absent or empty
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 101-115) — decision rationale
  - #file:../research/20260408-01-backup-restore-research.md (Lines 14-25) — main.py phase structure
- **Dependencies**:
  - Task 1.1

---

## Phase 2: backup_metadata Model and Migration

### Task 2.1 (Tests): Write tests for BackupMetadata model

Write unit tests verifying the `BackupMetadata` SQLAlchemy model maps to `backup_metadata` with `id` (SERIAL PK) and `backed_up_at` (TIMESTAMPTZ NOT NULL).

- **Files**:
  - `tests/unit/shared/models/test_backup_metadata.py` — new test file
- **Success**:
  - Tests fail (red) before model exists
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 207-222) — table schema definition
- **Dependencies**:
  - None

### Task 2.2 (Implement): Create BackupMetadata SQLAlchemy model

Create `shared/models/backup_metadata.py` with the `BackupMetadata` ORM class and export it from `shared/models/__init__.py`.

- **Files**:
  - `shared/models/backup_metadata.py` — new model
  - `shared/models/__init__.py` — add export
- **Success**:
  - All Phase 2.1 tests pass (green)
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 207-222) — schema
- **Dependencies**:
  - Task 2.1

### Task 2.3: Create Alembic migration for backup_metadata

Generate and validate an Alembic migration that creates the `backup_metadata` table.

- **Files**:
  - `alembic/versions/<hash>_add_backup_metadata.py` — new migration file
- **Success**:
  - `alembic upgrade head` applies cleanly on a fresh DB
  - `alembic downgrade -1` removes the table cleanly
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 207-222) — table schema
- **Dependencies**:
  - Task 2.2

---

## Phase 3: Backup Infrastructure

### Task 3.1: Create backup Dockerfile and scripts

Multi-stage build using `postgres:18.1-alpine` as base, installing `aws-cli`, and copying backup scripts.

- **Files**:
  - `docker/backup.Dockerfile` — Dockerfile
  - `docker/backup-entrypoint.sh` — writes cron env file, installs cron job, execs crond
  - `docker/backup-script.sh` — inserts `backup_metadata` row, then `pg_dump | gzip | aws s3 cp`, 14-slot rotation
- **Success**:
  - Image builds without error
  - `backup-script.sh` inserts into `backup_metadata` before `pg_dump` (so timestamp is inside the dump)
  - 14-slot key rotation overwrites oldest slot
  - `BACKUP_S3_ENDPOINT` is optional (empty → omit from aws-cli args)
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 118-132) — backup format, slots, schedule
  - #file:../research/20260408-01-backup-restore-research.md (Lines 215-222) — metadata INSERT before dump ordering
- **Dependencies**:
  - Task 2.3 (backup_metadata table exists when script runs)

---

## Phase 4: Compose Changes

### Task 4.1: Add backup service to compose.yaml

Add a `backup` service under `profiles: [backup]`, mirroring the `cloudflared` pattern. Wire all backup env vars and mount no volumes beyond what the image needs.

- **Files**:
  - `compose.yaml` — add backup service block
- **Success**:
  - `docker compose --profile backup config` validates without error
  - Backup service is absent when `--profile backup` is not specified
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 8-12) — cloudflared profiles pattern
  - #file:../research/20260408-01-backup-restore-research.md (Lines 118-132) — service specification
- **Dependencies**:
  - Task 3.1 (Dockerfile must exist)

### Task 4.2: Create compose.restore.yaml

Create an override compose file with: `init` environment override (`INIT_ROLES_ONLY: "true"`) and a `restore` service that uses the backup image, depends on postgres healthy + init completed, and runs `pg_restore`.

- **Files**:
  - `compose.restore.yaml` — new compose override
- **Success**:
  - `docker compose -f compose.yaml -f compose.restore.yaml config` validates
  - Dependency chain: postgres healthy → init completed → restore executes
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 133-155) — restore compose spec
- **Dependencies**:
  - Task 1.2 (INIT_ROLES_ONLY flag must be implemented)
  - Task 3.1 (backup image used by restore service)

### Task 4.3: Add backup env vars to config.template/env.template

Add a documented backup env vars block.

- **Files**:
  - `config.template/env.template` — add backup section
- **Success**:
  - All 7 env vars present with inline comments: `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`, `BACKUP_S3_REGION`, `BACKUP_S3_ENDPOINT`, `BACKUP_RETENTION_COUNT`, `BACKUP_SCHEDULE`
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 163-171) — env var list and defaults
- **Dependencies**:
  - None

---

## Phase 5: Restore Script

### Task 5.1: Create scripts/restore.sh

Interactive shell script implementing the full restore sequence.

- **Files**:
  - `scripts/restore.sh` — new script (chmod +x)
- **Success**:
  - Lists available S3 backups via the backup container image (`aws s3 ls`)
  - Prompts user to select a backup key
  - Requires explicit `yes` confirmation before destroying volumes
  - Full sequence: `docker compose down` → `docker volume rm postgres_data redis_data` → compose restore `up --exit-code-from restore` → `docker compose up -d`
  - `set -e` — exits non-zero on any failure
  - Does not duplicate backup/restore logic from the Dockerfile scripts
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 133-155) — restore steps
- **Dependencies**:
  - Task 4.2 (compose.restore.yaml must exist)

---

## Phase 6: Orphaned Embed Sweep

### Task 6.1 (Tests): Write tests for \_sweep_orphaned_embeds

Write unit tests for the `_sweep_orphaned_embeds()` coroutine covering: (a) no `backup_metadata` rows → skip sweep entirely; (b) rows present → delete messages whose UUID is absent from DB; (c) message UUID exists in DB → not deleted.

- **Files**:
  - `tests/unit/bot/test_sweep_orphaned_embeds.py` — new test file
- **Success**:
  - Tests fail (red) before implementation
  - All three behavioral cases covered
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 224-265) — algorithm and relevant code
- **Dependencies**:
  - Task 2.2 (BackupMetadata model available)

### Task 6.2 (Implement): Add \_sweep_orphaned_embeds to services/bot/bot.py

Add `async def _sweep_orphaned_embeds(self)` to the Bot class. Query `backup_metadata` for the most recent `backed_up_at`; if no row, return immediately. Set `cutoff = backed_up_at - timedelta(minutes=5)`. For each `channel_configurations` entry with a `channel_id`, call `channel.history(after=cutoff, limit=None)`, filter by `message.author.id == self.user.id`, extract UUID from `join_game_` custom_id, query DB, delete on miss.

Call from `on_ready` (line 177) and `on_resumed` (line 352).

- **Files**:
  - `services/bot/bot.py` — add `_sweep_orphaned_embeds` and two call sites
- **Success**:
  - All Phase 6.1 tests pass (green)
  - Called from `on_ready` and `on_resumed`
  - Fresh install (no `backup_metadata` rows) skips without error
  - Live game embeds (game exists in DB) are not deleted
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 226-280) — full algorithm, insertion points, custom_id format
- **Dependencies**:
  - Task 6.1
  - Task 2.3 (migration applied so table exists at runtime)

---

## Dependencies

- `uv` for Python dependency management
- `docker` and `docker compose` for container orchestration
- AWS CLI (installed in backup image) for S3 operations
- S3-compatible storage (AWS S3, Cloudflare R2, or Backblaze B2)

## Success Criteria

- `docker compose --profile backup up -d` starts automated backup without affecting other services
- `scripts/restore.sh` completes a full restore with no manual steps beyond selection and confirmation
- After restore, `docker compose up -d` starts all services and Alembic migrates forward from backup revision
- Restore works for Postgres major version upgrades (logical dump compatible across versions)
- Bot startup after restore deletes all Discord embeds whose game UUIDs are absent from the DB
- Fresh installs (no `backup_metadata` rows) skip the embed sweep entirely
- All new unit tests pass

---

## Phase 7: pytest backup Marker and E2E Test Infrastructure

### Task 7.1: Add backup pytest marker to pyproject.toml

Add a `backup` marker to the `[tool.pytest.ini_options]` markers list and exclude it from the default `addopts` filter alongside `e2e` and `integration`.

- **Files**:
  - `pyproject.toml` — update markers list and addopts
- **Success**:
  - `pytest --markers` shows the `backup` marker
  - Default test run (`pytest`) does not execute tests marked `@pytest.mark.backup`
  - `pytest -m backup` selects only backup tests
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 305-333) — marker definition and addopts update
- **Dependencies**:
  - None

### Task 7.2: Add MinIO service and init container to compose.e2e.yaml

Add `minio` (always-on) and `minio-init` (creates test bucket idempotently on each stack start) services to `compose.e2e.yaml`. MinIO is idle during normal e2e runs; backup tests activate the backup profile on top of it.

- **Files**:
  - `compose.e2e.yaml` — add minio and minio-init service blocks
- **Success**:
  - `docker compose -f compose.yaml -f compose.e2e.yaml config` validates without error
  - `minio-init` creates the `test-backups` bucket idempotently on each stack start
  - MinIO reachable at `http://minio:9000` from other services on `app-network`
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 363-408) — MinIO service spec and healthcheck
- **Dependencies**:
  - None

### Task 7.3: Add backup env vars to config/env.e2e

Add the MinIO-backed backup env vars block to `config/env.e2e` so backup tests use the local MinIO instance with no real AWS credentials.

- **Files**:
  - `config/env.e2e` — add BACKUP\_\* env var block
- **Success**:
  - All 7 backup env vars present and pointing at MinIO (`BACKUP_S3_ENDPOINT=http://minio:9000`, `BACKUP_S3_BUCKET=test-backups`, MinIO root credentials)
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 391-408) — env var values and defaults
- **Dependencies**:
  - Task 7.2

---

## Phase 8: Backup Test Files

### Task 8.1: Create tests/backup/ package and conftest

Create the `tests/backup/` Python package with `__init__.py` and `conftest.py`. The conftest imports shared fixtures from `tests/e2e/conftest.py` (db session, http client, Discord helper).

- **Files**:
  - `tests/backup/__init__.py` — empty package marker
  - `tests/backup/conftest.py` — shared fixture imports
- **Success**:
  - `pytest tests/backup/` collects without import errors
  - Fixtures from `tests/e2e/conftest.py` are accessible in backup tests
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 320-333) — conftest import pattern
- **Dependencies**:
  - Task 7.1

### Task 8.2: Create test_backup_create_game_a.py (Phase 1)

Test that creates gameA before the backup and asserts it is present in the DB. Run before the backup is triggered.

- **Files**:
  - `tests/backup/test_backup_create_game_a.py` — Phase 1 test
- **Success**:
  - gameA created via API and confirmed present in DB
  - Marked `@pytest.mark.backup`
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 320-362) — test file layout and Phase 1 description
- **Dependencies**:
  - Task 8.1

### Task 8.3: Create test_backup_create_game_b.py (Phase 2)

Test that creates gameB after the backup, waits for the Discord embed to appear, records the embed `message_id` to the file path in `GAMEB_MESSAGE_ID_FILE`, and asserts the embed is visible.

- **Files**:
  - `tests/backup/test_backup_create_game_b.py` — Phase 2 test
- **Success**:
  - gameB created after backup; embed `message_id` written to `GAMEB_MESSAGE_ID_FILE`
  - gameB's embed is visible in Discord at assertion time
  - Marked `@pytest.mark.backup`
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 334-362) — Phase 2 description and shared state file pattern
- **Dependencies**:
  - Task 8.1

### Task 8.4: Create test_backup_post_restore.py (Phases 3 and 4)

Post-restore assertions: gameA present in DB, gameB absent, gameB embed deleted from Discord. Includes the cron test: start backup container with `BACKUP_SCHEDULE=* * * * *`, wait ≤90s, assert `backup_metadata` row inserted and `slot-0.dump.gz` present in MinIO.

- **Files**:
  - `tests/backup/test_backup_post_restore.py` — Phase 3/4 assertions and cron test
- **Success**:
  - gameA row exists in DB; gameB row is absent
  - gameB's Discord embed (identified via `GAMEB_MESSAGE_ID_FILE`) is deleted
  - Cron test: `backup-script.sh` runs within 90s; `backup_metadata` row inserted; `slot-0.dump.gz` present in MinIO
  - Marked `@pytest.mark.backup`
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 334-362) — post-restore assertion sequence
  - #file:../research/20260408-01-backup-restore-research.md (Lines 409-420) — cron test specification
- **Dependencies**:
  - Task 8.2, Task 8.3

---

## Phase 9: Test Runner and Operator Scripts

### Task 9.1: Create scripts/run-backup-tests.sh

Shell script that owns the full backup test lifecycle across four phases: bring up full stack → Phase 1 pytest → trigger one-shot backup → Phase 2 pytest → stop non-storage services → run restore compose → bring services back up → Phase 3/4 pytest.

- **Files**:
  - `scripts/run-backup-tests.sh` — new script (chmod +x)
- **Success**:
  - Implements the four-phase sequence from research exactly
  - All three pytest invocations (`test_backup_create_game_a.py`, `test_backup_create_game_b.py`, `test_backup_post_restore.py`) pass
  - Uses `tee` for full output capture before any filtering
  - `set -e` exits non-zero on any failure
  - Passes `GAMEB_MESSAGE_ID_FILE` env var between phases
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 334-362) — full four-phase script structure
- **Dependencies**:
  - Task 7.2, Tasks 8.1–8.4, Task 4.2 (compose.restore.yaml must exist)

### Task 9.2: Create scripts/backup-now.sh

One-shot operator script that triggers an immediate backup using the running backup container's credentials and environment.

- **Files**:
  - `scripts/backup-now.sh` — new script (chmod +x)
- **Success**:
  - `./scripts/backup-now.sh` invokes `backup-script.sh` inside the running backup container
  - Produces a clear Docker error if the backup container is not running
  - Marked executable
- **Research References**:
  - #file:../research/20260408-01-backup-restore-research.md (Lines 421-438) — backup-now.sh specification
- **Dependencies**:
  - Task 3.1 (backup container image exists)
  - Task 4.1 (backup service in compose.yaml)
