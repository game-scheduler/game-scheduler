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


# backup-entrypoint.sh
#
# Writes runtime environment variables into a file that crond can source,
# installs the cron schedule, then execs crond in the foreground so the
# container stays alive and Docker can manage its lifecycle.
set -e

CRON_ENV_FILE=/etc/backup-env

# Export all env vars crond needs — crond runs jobs with a minimal shell
# that does not inherit the container environment.
cat > "${CRON_ENV_FILE}" <<EOF
PGHOST=${PGHOST:-postgres}
PGPORT=${PGPORT:-5432}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
ADMIN_DATABASE_URL=${ADMIN_DATABASE_URL}
BACKUP_S3_BUCKET=${BACKUP_S3_BUCKET}
BACKUP_S3_ACCESS_KEY_ID=${BACKUP_S3_ACCESS_KEY_ID}
BACKUP_S3_SECRET_ACCESS_KEY=${BACKUP_S3_SECRET_ACCESS_KEY}
BACKUP_S3_REGION=${BACKUP_S3_REGION:-us-east-1}
BACKUP_S3_ENDPOINT=${BACKUP_S3_ENDPOINT:-}
BACKUP_RETENTION_COUNT=${BACKUP_RETENTION_COUNT:-14}
EOF
chmod 600 "${CRON_ENV_FILE}"

SCHEDULE="${BACKUP_SCHEDULE:-0 */12 * * *}"

# Install cron job — source the env file first so all vars are available
echo "${SCHEDULE} . ${CRON_ENV_FILE} && /usr/local/bin/backup-script.sh >> /var/log/backup.log 2>&1" \
    > /etc/crontabs/root

exec crond -f -l 8
