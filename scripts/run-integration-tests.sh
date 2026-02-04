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

set -e

# Environment file location
ENV_FILE="config/env.int"

if [ -z "$ASSUME_SYSTEM_READY" ]; then
  cleanup() {
    echo "Cleaning up integration test environment..."
    docker compose --env-file "$ENV_FILE" down -v
  }
  trap cleanup EXIT
fi

echo "Running integration tests..."

if [ -z "$ASSUME_SYSTEM_READY" ]; then
  # Ensure full stack (including init) is healthy before running tests
  docker compose --env-file "$ENV_FILE" up -d --build system-ready
else
  echo "Skipping system-ready startup and cleanup (ASSUME_SYSTEM_READY is set)"
fi

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --env-file "$ENV_FILE" run --build --no-deps --rm integration-tests "$@"

echo "Integration tests passed!"
