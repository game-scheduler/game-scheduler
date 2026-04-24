<!-- markdownlint-disable-file -->

# Task Research Notes: Local File Backup Support

## Research Executed

### File Analysis

- `docker/backup-script.sh`
  - Single streaming pipeline: `pg_dump | gzip | aws_s3 cp - "s3://${BUCKET}/${BACKUP_KEY}"`
  - All S3 specificity is in the `aws_s3` helper and the final `cp` destination
  - Slot rotation uses a local state file `/var/lib/backup-slot` — no changes needed
  - Key is built as `backup/slot-${SLOT}.dump.gz` using separate `BUCKET` + path vars

- `docker/restore-script.sh`
  - `aws_s3 cp "s3://${BUCKET}/${RESTORE_BACKUP_KEY}" - | gunzip > "${TMPFILE}"`
  - `RESTORE_BACKUP_KEY` is a bucket-relative path (e.g. `backup/slot-0.dump.gz`)
  - Downloads to a `mktemp` file, then runs `pg_restore` from that file

- `docker/backup.Dockerfile`
  - Installs `awscli` via pip; no changes needed since it's still needed for `s3://` destinations

- `docker/backup-entrypoint.sh`
  - Builds `BACKUP_DATABASE_URL`, writes crontab, execs supercronic — no changes needed

- `compose.yaml` (backup service env block)
  - Passes: `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`,
    `BACKUP_S3_REGION`, `BACKUP_S3_ENDPOINT`, `BACKUP_RETENTION_COUNT`, `BACKUP_SCHEDULE`
  - No volume mounts currently defined on the backup service

- `compose.restore.yaml`
  - Passes same `BACKUP_S3_*` vars plus `RESTORE_BACKUP_KEY`

- `compose.e2e.yaml`
  - Backup service override: hardcodes `BACKUP_S3_BUCKET=test-backups`,
    `BACKUP_S3_ENDPOINT=http://minio:9000`, `BACKUP_S3_ACCESS_KEY_ID=minioadmin`,
    `BACKUP_S3_SECRET_ACCESS_KEY=minioadmin`
  - MinIO uses S3 protocol with `s3://` keys — will continue using S3 path with new design

- `config.template/env.template` (Backup Configuration section, line ~370)
  - Declares: `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`,
    `BACKUP_S3_REGION`, `BACKUP_S3_ENDPOINT`, `BACKUP_RETENTION_COUNT`, `BACKUP_SCHEDULE`

- `config/env.dev`, `config/env.prod`, `config/env.staging`
  - All have the same Backup Configuration section as template with empty/default values
  - `env.prod` and `env.staging` comment out `BACKUP_SCHEDULE` and set it to empty (no auto-run)

- `config/env.e2e`
  - Has filled-in values: `BACKUP_S3_BUCKET=test-backups`, `BACKUP_S3_ENDPOINT=http://minio:9000`,
    creds `minioadmin/minioadmin`, `BACKUP_SCHEDULE="0 */12 * * *"`

- `config/env.int`
  - Entire Backup Configuration section is commented out (backup not used in integration tests)

### Code Search Results

- `BACKUP_S3_BUCKET`
  - Appears in: `backup-script.sh`, `restore-script.sh`, `compose.yaml`, `compose.restore.yaml`,
    `compose.e2e.yaml`, `config.template/env.template`, all 5 `config/env.*` files
- `RESTORE_BACKUP_KEY`
  - Appears in: `restore-script.sh`, `compose.restore.yaml`

## Key Discoveries

### The Entire S3 Write Is One Line

```sh
pg_dump --format=custom "${BACKUP_DATABASE_URL}" \
  | gzip \
  | aws_s3 cp - "s3://${BUCKET}/${BACKUP_KEY}"
```

The S3-specific surface is exactly: `aws_s3 cp - "<url>"`. Swapping it for `cat > "<path>"` is
the entire write-path change. The read path in restore-script.sh is equally narrow.

### Slot Key Construction

Currently the script builds the destination from two variables:

```sh
BUCKET="${BACKUP_S3_BUCKET}"
BACKUP_KEY="backup/slot-${SLOT}.dump.gz"
# used as: s3://${BUCKET}/${BACKUP_KEY}
```

With the proposed design, both collapse into a single base URL env var:

```sh
BACKUP_DEST="s3://my-bucket/backup"         # S3 example
BACKUP_DEST="file:///var/lib/backups"        # local example
# key: "${BACKUP_DEST}/slot-${SLOT}.dump.gz"
```

### MinIO (e2e) Stays on S3 Path

The e2e tests use MinIO with `BACKUP_S3_ENDPOINT=http://minio:9000`. MinIO speaks the S3
protocol so it uses `s3://` URLs. After the change, `BACKUP_DEST=s3://test-backups` plus
the existing `BACKUP_S3_ENDPOINT` continues to work unchanged in behavior — only the env var
name changes.

## Recommended Approach

Replace `BACKUP_S3_BUCKET` (plus the hardcoded `backup/` path prefix in the script) with a
single `BACKUP_DEST` base URL. The scheme (`s3://` vs `file://`) drives dispatch.

### backup-script.sh changes

```sh
BACKUP_DEST="${BACKUP_DEST}"

backup_write() {
    case "$1" in
        s3://*)   aws_s3 cp - "$1" ;;
        file://*) cat > "${1#file://}" ;;
        *)        echo "Unknown backup destination scheme: $1" >&2; exit 1 ;;
    esac
}

BACKUP_KEY="${BACKUP_DEST}/slot-${SLOT}.dump.gz"

pg_dump --format=custom --no-password "${BACKUP_DATABASE_URL}" \
  | gzip \
  | backup_write "${BACKUP_KEY}"
```

### restore-script.sh changes

Rename `RESTORE_BACKUP_KEY` (bucket-relative path) to `RESTORE_SRC` (full URL):

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

Callers set e.g. `RESTORE_SRC=s3://my-bucket/backup/slot-0.dump.gz` or
`RESTORE_SRC=file:///var/lib/backups/slot-0.dump.gz`.

### Volume mount for local backup persistence

A `file://` destination inside a Docker container needs a persistent path. Add a named volume
`backup_data` mounted at `/var/lib/backups` in the backup service in `compose.yaml`. It is
harmless when using S3 mode (mount exists but is unused).

```yaml
# compose.yaml backup service
volumes:
  - backup_data:/var/lib/backups
```

```yaml
# compose.yaml top-level volumes
volumes:
  backup_data:
    driver: local
```

For production local use, users can override with a bind mount in `compose.override.yaml`:

```yaml
volumes:
  backup_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/on/host/backups
```

### compose.yaml env block changes

```yaml
# Before
BACKUP_S3_BUCKET: ${BACKUP_S3_BUCKET}
BACKUP_S3_ACCESS_KEY_ID: ${BACKUP_S3_ACCESS_KEY_ID}
BACKUP_S3_SECRET_ACCESS_KEY: ${BACKUP_S3_SECRET_ACCESS_KEY}
BACKUP_S3_REGION: ${BACKUP_S3_REGION:-us-east-1}
BACKUP_S3_ENDPOINT: ${BACKUP_S3_ENDPOINT:-}

# After
BACKUP_DEST: ${BACKUP_DEST}
BACKUP_S3_ACCESS_KEY_ID: ${BACKUP_S3_ACCESS_KEY_ID:-}
BACKUP_S3_SECRET_ACCESS_KEY: ${BACKUP_S3_SECRET_ACCESS_KEY:-}
BACKUP_S3_REGION: ${BACKUP_S3_REGION:-us-east-1}
BACKUP_S3_ENDPOINT: ${BACKUP_S3_ENDPOINT:-}
```

S3 credential vars become optional (default empty) so they don't cause Docker Compose warnings
when using `file://` mode.

### compose.restore.yaml changes

```yaml
# Before
BACKUP_S3_BUCKET: ${BACKUP_S3_BUCKET}
RESTORE_BACKUP_KEY: ${RESTORE_BACKUP_KEY}

# After
BACKUP_DEST: ${BACKUP_DEST} # needed so aws_s3() helper env is populated
RESTORE_SRC: ${RESTORE_SRC}
```

### compose.e2e.yaml changes

```yaml
# Before
backup:
  environment:
    BACKUP_S3_BUCKET: test-backups
    BACKUP_S3_ENDPOINT: http://minio:9000
    BACKUP_S3_ACCESS_KEY_ID: minioadmin
    BACKUP_S3_SECRET_ACCESS_KEY: minioadmin

# After
backup:
  environment:
    BACKUP_DEST: s3://test-backups
    BACKUP_S3_ENDPOINT: http://minio:9000
    BACKUP_S3_ACCESS_KEY_ID: minioadmin
    BACKUP_S3_SECRET_ACCESS_KEY: minioadmin
```

### env.template Backup Configuration section replacement

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

### Per-env config values

| File          | `BACKUP_DEST`       | S3 creds                | Notes                                |
| ------------- | ------------------- | ----------------------- | ------------------------------------ |
| `env.dev`     | _(empty)_           | empty                   | matches template defaults            |
| `env.prod`    | _(empty)_           | empty                   | `BACKUP_SCHEDULE=` (no auto-run)     |
| `env.staging` | _(empty)_           | empty                   | `BACKUP_SCHEDULE=` (no auto-run)     |
| `env.e2e`     | `s3://test-backups` | `minioadmin/minioadmin` | endpoint stays `http://minio:9000`   |
| `env.int`     | all commented out   | commented out           | backup not used in integration tests |

## Implementation Guidance

- **Objectives**: Replace the 5-variable `BACKUP_S3_BUCKET + S3 creds` pattern with a single
  `BACKUP_DEST` URL; add `file://` dispatch to backup and restore scripts; keep MinIO e2e path
  unchanged in behavior
- **Key Tasks**:
  1. Update `docker/backup-script.sh`: add `backup_write` function, derive key from `BACKUP_DEST`
  2. Update `docker/restore-script.sh`: add `backup_read` function, rename `RESTORE_BACKUP_KEY` → `RESTORE_SRC`
  3. Update `compose.yaml`: replace `BACKUP_S3_BUCKET` with `BACKUP_DEST`, make S3 creds optional, add `backup_data` volume mount and named volume
  4. Update `compose.restore.yaml`: replace `BACKUP_S3_BUCKET` + `RESTORE_BACKUP_KEY` with `BACKUP_DEST` + `RESTORE_SRC`
  5. Update `compose.e2e.yaml`: replace `BACKUP_S3_BUCKET: test-backups` with `BACKUP_DEST: s3://test-backups`
  6. Update `config.template/env.template`: replace `BACKUP_S3_BUCKET` with `BACKUP_DEST`, annotate S3 creds as conditional
  7. Update `config/env.dev`, `config/env.prod`, `config/env.staging`, `config/env.e2e`, `config/env.int` to match template structure
- **Dependencies**: None — purely shell and compose changes; no Python code touched
- **Success Criteria**:
  - Existing e2e backup tests pass unchanged (MinIO still uses `s3://test-backups`)
  - `BACKUP_DEST=file:///var/lib/backups` produces a gzipped dump at that path inside the container
  - `RESTORE_SRC=file:///var/lib/backups/slot-0.dump.gz` restores correctly
  - No `BACKUP_S3_BUCKET` references remain in any file
  - All `config/env.*` files match `config.template/env.template` structure
