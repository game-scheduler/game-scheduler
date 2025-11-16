#!/bin/bash
set -e

# Install shared package in editable mode if not already installed
if [ -d "/app/shared" ]; then
    pip install --user -e /app/shared --quiet
fi

# Execute the main command
exec "$@"
