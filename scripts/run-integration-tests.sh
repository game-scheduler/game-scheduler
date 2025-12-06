#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

echo "Building integration test container..."
docker compose -f docker-compose.integration.yml build integration-tests init

cleanup() {
  echo "Cleaning up integration test environment..."
  docker compose -f docker-compose.integration.yml --env-file .env.integration down -v
}

trap cleanup EXIT

echo "Running integration tests..."
if [ $# -eq 0 ]; then
  docker compose -f docker-compose.integration.yml --env-file .env.integration run --rm integration-tests
else
  docker compose -f docker-compose.integration.yml --env-file .env.integration run --rm integration-tests "$@"
fi

echo "Integration tests passed!"
