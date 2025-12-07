<!-- markdownlint-disable-file -->

# Release Changes: Docker Development Volume Mount Strategy

**Related Plan**: 20251207-docker-development-volume-mount-plan.instructions.md
**Implementation Date**: 2025-12-07

## Summary

Enable instant hot-reload development workflow by adding development stages to
Dockerfiles and creating compose.override.yaml for automatic volume mounting of
source code.

## Changes

### Added

### Modified

- docker/api.Dockerfile - Added development stage with hot-reload support using
  uvicorn --reload
- docker/bot.Dockerfile - Added development stage with python -m execution for
  Discord bot service
- docker/notification-daemon.Dockerfile - Added development stage with python -m
  execution for notification daemon
- docker/status-transition-daemon.Dockerfile - Added development stage with
  python -m execution for status transition daemon

### Removed
