<!-- markdownlint-disable-file -->

# Release Changes: Game Announcement Archive Feature

**Related Plan**: 20260311-01-game-archive-feature.plan.md
**Implementation Date**: 2026-03-11

## Summary

Add archive metadata fields to templates and game sessions, including schema and status transition updates for archiving.

## Changes

### Added

- alembic/versions/20260311_add_archive_fields.py - add archive delay and archive channel fields to templates and sessions.

### Modified

- shared/models/channel.py - disambiguate game-channel relationship foreign keys.
- shared/models/game.py - add archive fields and channel relationships with explicit foreign keys.
- shared/models/template.py - add archive fields and channel relationships with explicit foreign keys.
- shared/utils/status_transitions.py - add ARCHIVED status and allow transitions from COMPLETED.
- tests/services/scheduler/test_status_transitions.py - cover ARCHIVED transitions and enum values.
- tests/unit/shared/utils/test_status_transitions.py - assert ARCHIVED display name.

### Removed

- None.
