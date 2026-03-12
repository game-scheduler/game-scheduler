<!-- markdownlint-disable-file -->

# Release Changes: Game Announcement Archive Feature

**Related Plan**: 20260311-01-game-archive-feature.plan.md
**Implementation Date**: 2026-03-11

## Summary

Add archive metadata fields to templates and game sessions, including schema and status transition updates for archiving.

## Changes

### Added

- alembic/versions/20260311_add_archive_fields.py - add archive delay and archive channel fields to templates and sessions.
- tests/unit/schemas/test_template_schema.py - cover template schema archive fields.

### Modified

- shared/models/channel.py - disambiguate game-channel relationship foreign keys.
- shared/models/game.py - add archive fields and channel relationships with explicit foreign keys.
- shared/models/template.py - add archive fields and channel relationships with explicit foreign keys.
- shared/utils/status_transitions.py - add ARCHIVED status and allow transitions from COMPLETED.
- tests/services/scheduler/test_status_transitions.py - cover ARCHIVED transitions and enum values.
- tests/unit/shared/utils/test_status_transitions.py - assert ARCHIVED display name.
- shared/schemas/template.py - add archive fields to template schemas and validation.
- services/api/routes/templates.py - wire archive fields through template routes and responses.
- services/api/services/games.py - copy archive fields into new game sessions.
- tests/services/api/routes/test_templates.py - validate archive fields in template route helpers.
- tests/services/api/services/test_games.py - verify archive fields are copied when building sessions.
- services/bot/events/handlers.py - add archive announcement stub for TDD coverage.
- tests/services/bot/events/test_handlers.py - add xfail tests for archive scheduling and archiving behavior.
- services/bot/events/handlers.py - schedule ARCHIVED transitions and archive announcements on status changes.
- tests/services/bot/events/test_handlers.py - remove xfail markers and add edge case coverage for archive handling.

### Removed

- None.
