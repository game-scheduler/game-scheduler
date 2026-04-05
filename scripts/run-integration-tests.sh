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


# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY
#
# Environment variables:
#   SKIP_STARTUP=1   - Skip building and starting the test environment.
#                      Use when the environment is already running from a prior
#                      SKIP_CLEANUP=1 run. Do NOT use for a first run or after
#                      making service code changes, because it skips rebuilding
#                      the containers.
#   SKIP_CLEANUP=1   - Skip teardown after tests (leaves containers and volumes
#                      running). Use when you want to re-run tests quickly without
#                      rebuilding, or to inspect logs and state after a failure.
#                      Without this, cleanup destroys all volumes (resets database
#                      state) and docker logs become unavailable.
#
# Iterative debugging pattern:
#   First run:       SKIP_CLEANUP=1 ./scripts/run-integration-tests.sh
#   Re-run:          SKIP_STARTUP=1 SKIP_CLEANUP=1 ./scripts/run-integration-tests.sh
#   Final/clean run: SKIP_STARTUP=1 ./scripts/run-integration-tests.sh
#
# AGENT NOTE: This script takes MORE THAN 5 MINUTES to run.
#   - Always use a terminal timeout of at least 600000ms (10 minutes).
#   - Always capture output with tee BEFORE any filtering:
#       scripts/run-integration-tests.sh |& tee output-integration.txt
#   - NEVER pipe directly to grep/tail/head without first saving via tee.
#     If a test fails and output was filtered, you must rerun the entire suite.
#   - When reading captured output, use at least 200 lines.

set -e

# Environment file location (can be overridden by setting ENV_FILE before calling)
ENV_FILE="${ENV_FILE:-tests/integration/env.int}"

cleanup() {
  if [ -n "$SKIP_CLEANUP" ]; then
    echo "Skipping integration test environment cleanup (SKIP_CLEANUP is set)"
  else
    echo "Cleaning up integration test environment..."
    docker compose --progress quiet --env-file "$ENV_FILE" down -v
  fi
}
trap cleanup EXIT

echo "Running integration tests..."

if [ -n "$SKIP_STARTUP" ]; then
  echo "Skipping integration test environment startup (SKIP_STARTUP is set)"
else
  # Ensure full stack (including init) is healthy before running tests
  docker compose --progress quiet --env-file "$ENV_FILE" up -d --build system-ready
fi

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --progress quiet --env-file "$ENV_FILE" run --build --no-deps --rm integration-tests "$@"

echo "Integration tests passed!"
