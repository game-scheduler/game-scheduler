#!/bin/bash
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


# restore.sh
#
# Interactive restore script for the Game Scheduler Postgres database.
#
# Steps:
#   1. Lists available S3 backups using the backup container image
#   2. Prompts for backup selection
#   3. Confirms before destroying postgres_data and redis_data volumes
#   4. Stops all services, removes volumes, runs compose.restore.yaml
#   5. Starts all services normally after restore completes
#
# Usage:
#   ENV_FILE=config/env.prod ./scripts/restore.sh
#
# ENV_FILE defaults to config/env.dev if not set.
set -e

ENV_FILE="${ENV_FILE:-config/env.dev}"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Error: env file not found: ${ENV_FILE}" >&2
    echo "Set ENV_FILE to the path of your environment file." >&2
    exit 1
fi

# Source the env file so S3 credentials and compose project name are available
# in this shell for listing backups and constructing volume names.
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

PROJECT="${COMPOSE_PROJECT_NAME:-$(basename "$PWD")}"

echo "Fetching available backups from s3://${BACKUP_S3_BUCKET}/backup/..."

EXTRA_ARGS=()
if [[ -n "${BACKUP_S3_ENDPOINT}" ]]; then
    EXTRA_ARGS=("--endpoint-url" "${BACKUP_S3_ENDPOINT}")
fi

BACKUP_LIST=$(docker run --rm \
    -e AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID}" \
    -e AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY}" \
    -e AWS_DEFAULT_REGION="${BACKUP_S3_REGION:-us-east-1}" \
    --entrypoint aws \
    "${IMAGE_REGISTRY:-}game-scheduler-backup:${IMAGE_TAG:-latest}" \
    "${EXTRA_ARGS[@]}" s3 ls "s3://${BACKUP_S3_BUCKET}/backup/")

if [[ -z "${BACKUP_LIST}" ]]; then
    echo "No backups found in s3://${BACKUP_S3_BUCKET}/backup/" >&2
    exit 1
fi

echo ""
echo "Available backups:"
mapfile -t FILES < <(echo "${BACKUP_LIST}" | awk '{print $NF}')
for i in "${!FILES[@]}"; do
    echo "  $((i + 1))) backup/${FILES[$i]}"
done

echo ""
read -rp "Select backup number (or q to quit): " SELECTION

if [[ "${SELECTION}" == "q" ]]; then
    echo "Restore cancelled."
    exit 0
fi

if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] \
        || [[ "${SELECTION}" -lt 1 ]] \
        || [[ "${SELECTION}" -gt "${#FILES[@]}" ]]; then
    echo "Invalid selection: ${SELECTION}" >&2
    exit 1
fi

BACKUP_KEY="backup/${FILES[$((SELECTION - 1))]}"

echo ""
echo "Selected: s3://${BACKUP_S3_BUCKET}/${BACKUP_KEY}"
echo ""
echo "WARNING: This will permanently destroy and recreate the following volumes:"
echo "  - ${PROJECT}_postgres_data"
echo "  - ${PROJECT}_redis_data"
echo ""
read -rp "Type 'yes' to confirm: " CONFIRM

if [[ "${CONFIRM}" != "yes" ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Stopping all services..."
docker compose --env-file "${ENV_FILE}" down

echo "Removing postgres_data and redis_data volumes..."
docker volume rm "${PROJECT}_postgres_data" "${PROJECT}_redis_data"

echo "Restoring from ${BACKUP_KEY}..."
RESTORE_BACKUP_KEY="${BACKUP_KEY}" docker compose \
    --env-file "${ENV_FILE}" \
    -f compose.yaml \
    -f compose.restore.yaml \
    up --exit-code-from restore

echo ""
echo "Restore complete. Starting all services..."
docker compose --env-file "${ENV_FILE}" up -d

echo "All services started."
