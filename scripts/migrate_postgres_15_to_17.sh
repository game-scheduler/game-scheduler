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


# PostgreSQL 15 to 17 Migration Script
#
# This script performs a safe migration of PostgreSQL data from version 15 to 17.
# It uses pg_dump/pg_restore to ensure data compatibility across major versions.
#
# IMPORTANT: This script assumes you are using Docker Compose and have a backup
# of your data. Always test in non-production first.
#
# NOTE: If you don't have existing data to preserve, you can simply:
#   1. Stop services: docker compose down
#   2. Delete volume: docker volume rm gamebot_postgres_data (or postgres_data)
#   3. Start services: docker compose up -d
#   The init service will run Alembic migrations to create the schema on PostgreSQL 17.
#
# Usage (for data migration):
#   1. Stop all services: docker compose down
#   2. Run this script: ./scripts/migrate_postgres_15_to_17.sh
#   3. Start services with new version: docker compose up -d

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/postgres_migration_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Set defaults if not in environment
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-game_scheduler}
CONTAINER_PREFIX=${CONTAINER_PREFIX:-gamebot}

echo "=================================================="
echo "PostgreSQL 15 to 17 Migration"
echo "=================================================="
echo "Timestamp: $TIMESTAMP"
echo "Database: $POSTGRES_DB"
echo "User: $POSTGRES_USER"
echo "Backup Directory: $BACKUP_DIR"
echo "=================================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Step 1: Check if postgres is running
echo ""
echo "Step 1: Checking PostgreSQL container status..."
if docker ps | grep -q "${CONTAINER_PREFIX}-postgres"; then
    echo "ERROR: PostgreSQL container is running. Please stop all services first:"
    echo "  docker compose down"
    exit 1
fi
echo "✓ PostgreSQL container is not running"

# Step 2: Check if old data exists
echo ""
echo "Step 2: Checking for existing PostgreSQL 15 data..."
VOLUME_NAME="${CONTAINER_PREFIX}_postgres_data"
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    # Try without prefix
    VOLUME_NAME="postgres_data"
    if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
        echo "ERROR: PostgreSQL data volume not found"
        echo "Tried: ${CONTAINER_PREFIX}_postgres_data and postgres_data"
        exit 1
    fi
fi
echo "✓ Found data volume: $VOLUME_NAME"

# Step 3: Backup existing data using pg_dump with PostgreSQL 15
echo ""
echo "Step 3: Creating backup of PostgreSQL 15 database..."
BACKUP_FILE="$BACKUP_DIR/postgres_15_backup_${TIMESTAMP}.sql"

docker run --rm \
    -v "$VOLUME_NAME:/var/lib/postgresql/data" \
    -v "$BACKUP_DIR:/backup" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    postgres:15-alpine \
    sh -c "
        # Start PostgreSQL temporarily
        docker-entrypoint.sh postgres &
        PG_PID=\$!

        # Wait for PostgreSQL to be ready
        until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do
            sleep 1
        done

        # Create backup
        pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -F p -f /backup/postgres_15_backup_${TIMESTAMP}.sql

        # Stop PostgreSQL
        kill \$PG_PID
        wait \$PG_PID 2>/dev/null || true
    "

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file was not created"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✓ Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# Step 4: Rename old volume for safety
echo ""
echo "Step 4: Preserving old data volume..."
OLD_VOLUME_NAME="${VOLUME_NAME}_pg15_backup_${TIMESTAMP}"
docker volume create "$OLD_VOLUME_NAME"
docker run --rm \
    -v "$VOLUME_NAME:/source" \
    -v "$OLD_VOLUME_NAME:/target" \
    alpine \
    sh -c "cp -a /source/. /target/"
echo "✓ Old data preserved in volume: $OLD_VOLUME_NAME"

# Step 5: Remove old data from volume
echo ""
echo "Step 5: Clearing data volume for PostgreSQL 17..."
docker run --rm \
    -v "$VOLUME_NAME:/var/lib/postgresql/data" \
    alpine \
    sh -c "rm -rf /var/lib/postgresql/data/*"
echo "✓ Data volume cleared"

# Step 6: Initialize PostgreSQL 17 with restored data
echo ""
echo "Step 6: Initializing PostgreSQL 17 and restoring data..."
docker run --rm \
    -v "$VOLUME_NAME:/var/lib/postgresql/data" \
    -v "$BACKUP_DIR:/backup" \
    -e POSTGRES_USER="$POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e POSTGRES_DB="$POSTGRES_DB" \
    postgres:17-alpine \
    sh -c "
        # Initialize and start PostgreSQL
        docker-entrypoint.sh postgres &
        PG_PID=\$!

        # Wait for PostgreSQL to be ready
        until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do
            sleep 1
        done

        # Restore backup
        psql -U $POSTGRES_USER -d $POSTGRES_DB -f /backup/postgres_15_backup_${TIMESTAMP}.sql

        # Stop PostgreSQL
        kill \$PG_PID
        wait \$PG_PID 2>/dev/null || true
    "
echo "✓ PostgreSQL 17 initialized and data restored"

# Step 7: Verify migration
echo ""
echo "Step 7: Verifying migration..."
echo "Starting PostgreSQL 17 for verification..."
docker run --rm -d \
    --name "${CONTAINER_PREFIX}-postgres-verify" \
    -v "$VOLUME_NAME:/var/lib/postgresql/data" \
    -e POSTGRES_USER="$POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e POSTGRES_DB="$POSTGRES_DB" \
    postgres:17-alpine

# Wait for it to start
sleep 5

# Check version and table count
docker exec "${CONTAINER_PREFIX}-postgres-verify" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();" \
    > "$BACKUP_DIR/postgres_17_version_${TIMESTAMP}.txt"

docker exec "${CONTAINER_PREFIX}-postgres-verify" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        SELECT
            schemaname,
            tablename
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schemaname, tablename;
    " > "$BACKUP_DIR/postgres_17_tables_${TIMESTAMP}.txt"

# Stop verification container
docker stop "${CONTAINER_PREFIX}-postgres-verify"

echo "✓ Verification complete"
echo ""
echo "=================================================="
echo "Migration Summary"
echo "=================================================="
echo "✓ Backup created: $BACKUP_FILE"
echo "✓ Old data volume: $OLD_VOLUME_NAME"
echo "✓ PostgreSQL 17 data initialized in: $VOLUME_NAME"
echo "✓ Verification logs: $BACKUP_DIR/postgres_17_*_${TIMESTAMP}.txt"
echo ""
echo "Next steps:"
echo "1. Review verification logs in $BACKUP_DIR"
echo "2. Start your services: docker compose up -d"
echo "3. Run application tests to verify functionality"
echo "4. If successful, the old volume can be removed after testing:"
echo "   docker volume rm $OLD_VOLUME_NAME"
echo ""
echo "To rollback (if needed):"
echo "1. Stop services: docker compose down"
echo "2. Clear current volume: docker run --rm -v $VOLUME_NAME:/data alpine rm -rf /data/*"
echo "3. Restore old data: docker run --rm -v $OLD_VOLUME_NAME:/source -v $VOLUME_NAME:/target alpine cp -a /source/. /target/"
echo "4. Update compose.yaml to use postgres:15-alpine"
echo "5. Start services: docker compose up -d"
echo "=================================================="
