#!/bin/sh
# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# backup-script.sh
#
# Runs a single Postgres backup cycle:
#   1. Insert a backup_metadata row (timestamp is thus included in the dump)
#   2. pg_dump to custom format, gzip, upload to S3 using slot-based rotation
#
# Slot key format: backup/slot-<N>.dump.gz  where N cycles 0..(RETENTION_COUNT-1)
set -e

RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
BUCKET="${BACKUP_S3_BUCKET}"
REGION="${BACKUP_S3_REGION:-us-east-1}"

# Build aws s3 command, adding --endpoint-url only when BACKUP_S3_ENDPOINT is set
aws_s3() {
    if [ -n "${BACKUP_S3_ENDPOINT}" ]; then
        AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID}" \
        AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY}" \
        aws --region "${REGION}" --endpoint-url "${BACKUP_S3_ENDPOINT}" s3 "$@"
    else
        AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID}" \
        AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY}" \
        aws --region "${REGION}" s3 "$@"
    fi
}

# Determine which slot to write this run (slot cycles 0..RETENTION_COUNT-1)
SLOT_FILE=/var/lib/backup-slot
if [ -f "${SLOT_FILE}" ]; then
    LAST_SLOT=$(cat "${SLOT_FILE}")
    SLOT=$(( (LAST_SLOT + 1) % RETENTION_COUNT ))
else
    SLOT=0
fi

BACKUP_KEY="backup/slot-${SLOT}.dump.gz"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting backup to s3://${BUCKET}/${BACKUP_KEY}"

# Insert backup_metadata row before dumping so the timestamp is in the dump
psql "${ADMIN_DATABASE_URL}" -c "INSERT INTO backup_metadata (backed_up_at) VALUES (now());"

# Dump, compress, and upload in one pipeline to avoid writing a temp file
pg_dump \
    --format=custom \
    --no-password \
    "${ADMIN_DATABASE_URL}" \
  | gzip \
  | aws_s3 cp - "s3://${BUCKET}/${BACKUP_KEY}"

# Persist the slot so the next run advances to the next slot
echo "${SLOT}" > "${SLOT_FILE}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete: s3://${BUCKET}/${BACKUP_KEY}"
