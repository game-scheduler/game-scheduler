#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

echo "Starting integration test environment..."
docker compose -f docker-compose.integration.yml --env-file .env.integration up \
  --build \
  --abort-on-container-exit \
  --exit-code-from integration-tests

echo "Cleaning up integration test environment..."
docker compose -f docker-compose.integration.yml --env-file .env.integration down -v

echo "Integration tests complete!"
