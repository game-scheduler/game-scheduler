<!-- markdownlint-disable-file -->

# Task Details: Local File Backup Support

## Research Reference

**Source Research**: #file:../research/20260424-01-local-file-backup-research.md

---

## Phase 1: Update backup and restore scripts

### Task 1.1: Add `backup_write` function and update `backup-script.sh`

Replace the hardcoded `aws_s3 cp - "s3://${BUCKET}/${BACKUP_KEY}"` pipeline tail with a
scheme-dispatching `backup_write` helper. The key is now derived from `BACKUP_DEST`.

Current slot key construction:

```sh
BUCKET="${BACKUP_S3_BUCKET}"
BACKUP_KEY="backup/slot-${SLOT}.dump.gz"
# destination: s3://${BUCKET}/${BACKUP_KEY}
```

New construction:

```sh
BACKUP_DEST="${BACKUP_DEST}"
BACKUP_KEY="${BACKUP_DEST}/slot-${SLOT}.dump.gz"
```

New `backup_write` helper and updated pipeline:

```sh
backup_write() {
    case "$1" in
        s3://*)   aws_s3 cp - "$1" ;;
        file://*) cat > "${1#file://}" ;;
        *)        echo "Unknown backup destination scheme: $1" >&2; exit 1 ;;
    esac
}

pg_dump --format=custom --no-password "${BACKUP_DATABASE_URL}" \
  | gzip \
  | backup_write "${BACKUP_KEY}"
```

- **Files**:
  - `docker/backup-script.sh` — remove `BUCKET` var, add `backup_write`, update pipeline
- **Success**:
  - No `BACKUP_S3_BUCKET` references remain in the script
  - `backup_write` dispatches correctly on scheme
  - Script is still valid `sh` (not `bash`)
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 68-100) — proposed backup-script.sh changes
- **Dependencies**:
  - None

### Task 1.2: Add `backup_read` function and rename var in `restore-script.sh`

Replace `aws_s3 cp "${RESTORE_BACKUP_KEY}" -` with a scheme-dispatching `backup_read`
helper that accepts a full `RESTORE_SRC` URL.

New `backup_read` helper:

```sh
backup_read() {
    case "$1" in
        s3://*)   aws_s3 cp "$1" - | gunzip > "${TMPFILE}" ;;
        file://*) gunzip < "${1#file://}" > "${TMPFILE}" ;;
        *)        echo "Unknown restore source scheme: $1" >&2; exit 1 ;;
    esac
}

backup_read "${RESTORE_SRC}"
```

- **Files**:
  - `docker/restore-script.sh` — add `backup_read`, replace `RESTORE_BACKUP_KEY` usage with `RESTORE_SRC`
- **Success**:
  - No `RESTORE_BACKUP_KEY` references remain in the script
  - `backup_read` dispatches correctly on scheme
  - Script is still valid `sh`
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 102-125) — proposed restore-script.sh changes
- **Dependencies**:
  - None

---

## Phase 2: Update Docker Compose files

### Task 2.1: Update `compose.yaml`

Three changes in `compose.yaml`:

1. Replace `BACKUP_S3_BUCKET: ${BACKUP_S3_BUCKET}` with `BACKUP_DEST: ${BACKUP_DEST}` in the backup service env block.
2. Make S3 credential vars optional with empty defaults so Docker Compose doesn't warn when they're unset in `file://` mode:
   - `BACKUP_S3_ACCESS_KEY_ID: ${BACKUP_S3_ACCESS_KEY_ID:-}`
   - `BACKUP_S3_SECRET_ACCESS_KEY: ${BACKUP_S3_SECRET_ACCESS_KEY:-}`
3. Add `backup_data` volume mount to the backup service and declare the named volume at the top-level `volumes` block:

```yaml
# backup service volumes:
volumes:
  - backup_data:/var/lib/backups

# top-level volumes block (add alongside existing named volumes):
volumes:
  backup_data:
    driver: local
```

- **Files**:
  - `compose.yaml` — env block and volumes section of backup service, top-level volumes block
- **Success**:
  - `BACKUP_DEST` env var present, `BACKUP_S3_BUCKET` absent
  - S3 cred vars have `:-` empty defaults
  - `backup_data` volume declared and mounted
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 152-183) — compose.yaml env block diff and volume design
- **Dependencies**:
  - None

### Task 2.2: Update `compose.restore.yaml`

Replace:

```yaml
BACKUP_S3_BUCKET: ${BACKUP_S3_BUCKET}
RESTORE_BACKUP_KEY: ${RESTORE_BACKUP_KEY}
```

With:

```yaml
BACKUP_DEST: ${BACKUP_DEST}
RESTORE_SRC: ${RESTORE_SRC}
```

- **Files**:
  - `compose.restore.yaml` — restore service env block
- **Success**:
  - No `BACKUP_S3_BUCKET` or `RESTORE_BACKUP_KEY` references remain
  - `BACKUP_DEST` and `RESTORE_SRC` vars present
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 185-201) — compose.restore.yaml diff
- **Dependencies**:
  - None

### Task 2.3: Update `compose.e2e.yaml`

Replace:

```yaml
backup:
  environment:
    BACKUP_S3_BUCKET: test-backups
```

With:

```yaml
backup:
  environment:
    BACKUP_DEST: s3://test-backups
```

The remaining env vars (`BACKUP_S3_ENDPOINT`, creds) stay unchanged — MinIO continues to
work via the `s3://` path.

- **Files**:
  - `compose.e2e.yaml` — backup service environment override
- **Success**:
  - `BACKUP_DEST: s3://test-backups` present, `BACKUP_S3_BUCKET` absent
  - All other MinIO env vars unchanged
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 203-220) — compose.e2e.yaml diff
- **Dependencies**:
  - None

---

## Phase 3: Update environment configuration files

### Task 3.1: Update `config.template/env.template` Backup Configuration section

Replace the entire `Backup Configuration` section with:

```sh
# ==========================================
# Backup Configuration
# ==========================================

# Backup destination URL (determines backup mode by scheme)
# S3 example:    BACKUP_DEST=s3://my-bucket/backup
# Local example: BACKUP_DEST=file:///var/lib/backups
# Only needed when COMPOSE_PROFILES includes 'backup'
BACKUP_DEST=

# AWS/S3 credentials — only needed when BACKUP_DEST starts with s3://
BACKUP_S3_ACCESS_KEY_ID=
BACKUP_S3_SECRET_ACCESS_KEY=

# AWS region for the backup bucket (default: us-east-1)
BACKUP_S3_REGION=us-east-1

# Custom S3 endpoint URL for non-AWS providers (MinIO, Backblaze B2, etc.)
# Leave unset to use the default AWS endpoint
BACKUP_S3_ENDPOINT=

# Number of backup rotation slots (default: 14)
BACKUP_RETENTION_COUNT=14

# Cron schedule for automated backups (default: twice daily at midnight and noon)
BACKUP_SCHEDULE=0 */12 * * *
```

- **Files**:
  - `config.template/env.template` — Backup Configuration section
- **Success**:
  - `BACKUP_DEST` declared with scheme examples
  - `BACKUP_S3_BUCKET` absent
  - S3 creds annotated as conditional on `s3://` mode
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 222-260) — full template section
- **Dependencies**:
  - None

### Task 3.2: Update `config/env.dev`, `config/env.prod`, `config/env.staging`

Per-env changes (see research table):

| File          | `BACKUP_DEST` | `BACKUP_SCHEDULE`                |
| ------------- | ------------- | -------------------------------- |
| `env.dev`     | empty         | `0 */12 * * *`                   |
| `env.prod`    | empty         | `BACKUP_SCHEDULE=` (no auto-run) |
| `env.staging` | empty         | `BACKUP_SCHEDULE=` (no auto-run) |

For all three: replace `BACKUP_S3_BUCKET=...` with `BACKUP_DEST=`, and annotate S3 creds
as conditional (matching template). Keep `BACKUP_S3_BUCKET` removed.

- **Files**:
  - `config/env.dev`
  - `config/env.prod`
  - `config/env.staging`
- **Success**:
  - No `BACKUP_S3_BUCKET` in any of these files
  - Backup section matches template structure
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 262-282) — per-env config table
- **Dependencies**:
  - Task 3.1 complete (use template as reference)

### Task 3.3: Update `config/env.e2e`

Replace `BACKUP_S3_BUCKET=test-backups` with `BACKUP_DEST=s3://test-backups`. Keep all
other values (`BACKUP_S3_ENDPOINT`, creds, schedule) unchanged.

- **Files**:
  - `config/env.e2e` — Backup Configuration section
- **Success**:
  - `BACKUP_DEST=s3://test-backups` present, `BACKUP_S3_BUCKET` absent
  - All other backup values unchanged
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 262-282) — per-env config table
- **Dependencies**:
  - Task 3.1 complete

### Task 3.4: Verify `config/env.int` remains correctly commented out

`config/env.int` has the entire Backup Configuration section commented out. Verify no
`BACKUP_S3_BUCKET` reference exists (commented or otherwise); if the old var name appears
in a comment, update it to `BACKUP_DEST` to stay consistent.

- **Files**:
  - `config/env.int` — Backup Configuration section (commented out)
- **Success**:
  - No uncommented `BACKUP_S3_BUCKET` reference
  - Section remains commented out
- **Research References**:
  - #file:../research/20260424-01-local-file-backup-research.md (Lines 262-282) — env.int note
- **Dependencies**:
  - None

---

## Dependencies

- No Python code changes
- `awscli` already installed in backup image (continues to handle `s3://` mode)

## Success Criteria

- Existing e2e backup tests pass unchanged
- `BACKUP_DEST=file:///var/lib/backups` produces a gzipped dump at that path
- `RESTORE_SRC=file:///var/lib/backups/slot-0.dump.gz` restores correctly
- No `BACKUP_S3_BUCKET` references remain in any file
- No `RESTORE_BACKUP_KEY` references remain in any file
- All `config/env.*` files match `config.template/env.template` structure
