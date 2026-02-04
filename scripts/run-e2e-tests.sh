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

# Check for required test Discord credentials
if [ -z "$DISCORD_BOT_TOKEN" ]; then
  echo "ERROR: DISCORD_BOT_TOKEN environment variable is required in $ENV_FILE"
  echo "See docs/developer/TESTING.md for setup instructions"
  exit 1
fi

if [ -z "$DISCORD_GUILD_A_ID" ] || [ -z "$DISCORD_GUILD_A_CHANNEL_ID" ]; then
  echo "WARNING: DISCORD_GUILD_A_ID and DISCORD_GUILD_A_CHANNEL_ID should be set in $ENV_FILE"
  echo "Tests may fail without these. See docs/developer/TESTING.md for setup instructions"
fi

cleanup() {
  if [ -n "$SKIP_CLEANUP" ]; then
    echo "Skipping e2e test environment cleanup (SKIP_CLEANUP is set)"
    return
  fi
  echo "Cleaning up e2e test environment..."
  docker compose --env-file "$ENV_FILE" down -v
}

trap cleanup EXIT

echo "Running e2e tests..."
# Ensure full stack (including bot) is healthy before running tests
docker compose --env-file "$ENV_FILE" up -d --build system-ready

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --env-file "$ENV_FILE" run --build --no-deps --rm e2e-tests "$@"

echo "End-to-end tests passed!"
