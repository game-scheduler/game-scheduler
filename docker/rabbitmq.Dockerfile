FROM rabbitmq:4.2-management-alpine AS builder

# Build arguments for credentials
ARG RABBITMQ_USER=gamebot
ARG RABBITMQ_PASS=dev_password_change_in_prod

# Install gettext for envsubst
RUN apk add --no-cache gettext

# Copy template
COPY rabbitmq/definitions.json.template /tmp/definitions.json.template

# Generate password hash
RUN rabbitmqctl hash_password "${RABBITMQ_PASS}" > /tmp/password_hash.txt

# Substitute with envsubst
RUN RABBITMQ_PASSWORD_HASH=$(cat /tmp/password_hash.txt | tail -1) \
    envsubst < /tmp/definitions.json.template > /tmp/definitions.json

# Final image
FROM rabbitmq:4.2-management-alpine

# Copy configuration files
COPY rabbitmq/rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
COPY --from=builder /tmp/definitions.json /etc/rabbitmq/definitions.json
