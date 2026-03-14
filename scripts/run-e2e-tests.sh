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


# Run end-to-end tests in isolated Docker environment
# These tests verify the complete notification flow including Discord bot interactions
#
# REQUIRED: Set up test Discord bot and guild first (see docs/developer/TESTING.md)
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
#   First run:       SKIP_CLEANUP=1 ./scripts/run-e2e-tests.sh
#   Re-run:          SKIP_STARTUP=1 SKIP_CLEANUP=1 ./scripts/run-e2e-tests.sh
#   Final/clean run: SKIP_STARTUP=1 ./scripts/run-e2e-tests.sh
#
# AGENT NOTE: This script takes MORE THAN 10 MINUTES to run.
#   - Always use a terminal timeout of at least 900000ms (15 minutes).
#   - Always capture output with tee BEFORE any filtering:
#       scripts/run-e2e-tests.sh |& tee output-e2e.txt
#   - NEVER pipe directly to grep/tail/head without first saving via tee.
#     If a test fails and output was filtered, you must rerun the entire suite.
#   - When reading captured output, use at least 200 lines.

set -e

# Environment file location
ENV_FILE="config/env.e2e"

# Check for env file
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE file not found"
  echo "Create $ENV_FILE with test Discord credentials"
  echo "See docs/developer/TESTING.md for setup instructions"
  exit 1
fi

# Source env file to check required variables
source "$ENV_FILE"

# Export COMPOSE_PROFILES if set in env file so docker compose recognizes it
if [ -n "$COMPOSE_PROFILES" ]; then
  export COMPOSE_PROFILES
fi

# Check for required test Discord credentials
if [ -z "$DISCORD_BOT_TOKEN" ]; then
  echo "ERROR: DISCORD_BOT_TOKEN environment variable is required in $ENV_FILE"
  echo "See docs/developer/TESTING.md for setup instructions"
  exit 1
fi

if [ -z "$DISCORD_GUILD_A_ID" ] || [ -z "$DISCORD_GUILD_A_CHANNEL_ID" ] || [ -z "$DISCORD_ARCHIVE_CHANNEL_ID" ]; then
  echo "WARNING: DISCORD_GUILD_A_ID, DISCORD_GUILD_A_CHANNEL_ID, and DISCORD_ARCHIVE_CHANNEL_ID should be set in $ENV_FILE"
  echo "Tests may fail without these. See docs/developer/TESTING.md for setup instructions"
fi

cleanup() {
  if [ -n "$SKIP_CLEANUP" ]; then
    echo "Skipping e2e test environment cleanup (SKIP_CLEANUP is set)"
  else
    echo "Cleaning up e2e test environment..."
    docker compose --progress quiet --env-file "$ENV_FILE" down -v
  fi
}
trap cleanup EXIT

echo "Running e2e tests..."

if [ -n "$SKIP_STARTUP" ]; then
  echo "Skipping e2e test environment startup (SKIP_STARTUP is set)"
else
  # Ensure full stack (including bot) is healthy before running tests
  docker compose --progress quiet --env-file "$ENV_FILE" up -d --build system-ready
fi

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --progress quiet --env-file "$ENV_FILE" run --build --no-deps --rm e2e-tests "$@"

echo "End-to-end tests passed!"
