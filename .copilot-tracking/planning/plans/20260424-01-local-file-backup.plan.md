---
applyTo: '.copilot-tracking/changes/20260424-01-local-file-backup-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Local File Backup Support

## Overview

Replace the five-variable `BACKUP_S3_BUCKET` + S3-creds pattern with a single `BACKUP_DEST` URL and add `file://` dispatch to backup and restore scripts.

## Objectives

- Replace `BACKUP_S3_BUCKET` with `BACKUP_DEST` base URL across all scripts and compose files
- Add scheme-based dispatch (`s3://` vs `file://`) to `backup-script.sh` and `restore-script.sh`
- Rename `RESTORE_BACKUP_KEY` to `RESTORE_SRC` (full URL, not bucket-relative path)
- Make S3 credential vars optional (empty default) so they don't cause Docker Compose warnings in `file://` mode
- Add a `backup_data` named volume mount in `compose.yaml` for local file persistence
- Update all `config/env.*` and `config.template/env.template` to match new structure

## Research Summary

### Project Files

- `docker/backup-script.sh` — single-pipeline `pg_dump | gzip | aws_s3 cp`; write path is exactly one line
- `docker/restore-script.sh` — `aws_s3 cp <key> - | gunzip > tmpfile`; uses `RESTORE_BACKUP_KEY`
- `docker/backup.Dockerfile` — installs `awscli`; no changes needed
- `docker/backup-entrypoint.sh` — builds DB URL, writes crontab; no changes needed
- `compose.yaml` — backup service env block; no volume mounts yet
- `compose.restore.yaml` — restore service env block
- `compose.e2e.yaml` — backup override using MinIO (stays on `s3://` path)
- `config.template/env.template` — declares all `BACKUP_S3_*` vars
- `config/env.dev`, `config/env.prod`, `config/env.staging`, `config/env.e2e`, `config/env.int`

### External References

- #file:../research/20260424-01-local-file-backup-research.md — full analysis, proposed script changes, compose diffs, env table

## Implementation Checklist

### [ ] Phase 1: Update backup and restore scripts

- [ ] Task 1.1: Add `backup_write` function and update `backup-script.sh`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 18-56)

- [ ] Task 1.2: Add `backup_read` function and rename var in `restore-script.sh`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 58-90)

### [ ] Phase 2: Update Docker Compose files

- [ ] Task 2.1: Update `compose.yaml` — replace `BACKUP_S3_BUCKET`, make creds optional, add `backup_data` volume
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 93-139)

- [ ] Task 2.2: Update `compose.restore.yaml` — replace `BACKUP_S3_BUCKET` + `RESTORE_BACKUP_KEY`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 141-163)

- [ ] Task 2.3: Update `compose.e2e.yaml` — replace `BACKUP_S3_BUCKET: test-backups` with `BACKUP_DEST: s3://test-backups`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 165-181)

### [ ] Phase 3: Update environment configuration files

- [ ] Task 3.1: Update `config.template/env.template` Backup Configuration section
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 184-228)

- [ ] Task 3.2: Update `config/env.dev`, `config/env.prod`, `config/env.staging`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 230-265)

- [ ] Task 3.3: Update `config/env.e2e`
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 267-285)

- [ ] Task 3.4: Verify `config/env.int` remains correctly commented out
  - Details: .copilot-tracking/planning/details/20260424-01-local-file-backup-details.md (Lines 287-297)

## Dependencies

- No Python code changes — purely shell and Docker Compose
- `awscli` already installed in backup image (needed for `s3://` mode)

## Success Criteria

- Existing e2e backup tests pass unchanged (MinIO still uses `s3://test-backups`)
- `BACKUP_DEST=file:///var/lib/backups` produces a gzipped dump at that path inside the container
- `RESTORE_SRC=file:///var/lib/backups/slot-0.dump.gz` restores correctly
- No `BACKUP_S3_BUCKET` references remain in any file
- No `RESTORE_BACKUP_KEY` references remain in any file
- All `config/env.*` files match `config.template/env.template` structure
