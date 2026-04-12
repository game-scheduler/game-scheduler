# syntax=docker/dockerfile:1
FROM postgres:18.1-alpine

# Install aws-cli v2 via pip (lightweight apk alternative)
RUN apk add --no-cache python3 py3-pip && \
    pip install --no-cache-dir --break-system-packages awscli && \
    apk add --no-cache dcron

COPY docker/backup-entrypoint.sh /usr/local/bin/backup-entrypoint.sh
COPY docker/backup-script.sh /usr/local/bin/backup-script.sh
COPY docker/restore-script.sh /usr/local/bin/restore-script.sh

RUN chmod +x /usr/local/bin/backup-entrypoint.sh /usr/local/bin/backup-script.sh /usr/local/bin/restore-script.sh

ENTRYPOINT ["/usr/local/bin/backup-entrypoint.sh"]
