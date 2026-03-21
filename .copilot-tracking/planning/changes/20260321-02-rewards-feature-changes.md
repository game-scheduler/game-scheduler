<!-- markdownlint-disable-file -->

# Changes: Rewards Feature

## Summary

Add `rewards` (nullable text) and `remind_host_rewards` (bool) fields to game sessions and
templates, with Discord spoiler display, a host DM reminder on completion, and a
"Save and Archive" shortcut button in the frontend.

## Added

- `.copilot-tracking/planning/changes/20260321-02-rewards-feature-changes.md` — this changes tracking file

## Modified

- `shared/models/game.py` — added `rewards: Mapped[str | None]` (Text, nullable) and `remind_host_rewards: Mapped[bool]` (Boolean, server_default false) to `GameSession`; added `Boolean` import
- `shared/models/template.py` — added `remind_host_rewards: Mapped[bool]` (Boolean, server_default false) to `GameTemplate` pre-populated fields section
- `shared/schemas/game.py` — added `rewards`, `remind_host_rewards`, `archive_delay_seconds` to `GameUpdateRequest`; added `remind_host_rewards` to `GameCreateRequest`; added `rewards`, `remind_host_rewards`, `archive_channel_id` to `GameResponse`
- `shared/schemas/template.py` — added `remind_host_rewards` to `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, and `TemplateListItem`
- `services/api/services/games.py` — `_update_simple_text_fields` handles `rewards`; `_update_remaining_fields` handles `remind_host_rewards` and `archive_delay_seconds` (triggers status schedule update); `_build_game_session` copies `remind_host_rewards` from template; `clone_game` copies `remind_host_rewards` and sets `rewards=None`
- `services/api/routes/games.py` — `_build_game_response` maps `rewards`, `remind_host_rewards`, `archive_channel_id` to response; response schema population complete
- `services/bot/formatters/game_message.py` — `create_game_embed` accepts `rewards: str | None = None`; adds `🏆 Rewards` spoiler field (`||{rewards}||`) as an embed field when non-empty; `format_game_announcement` accepts and forwards `rewards` parameter
- `services/bot/events/handlers.py` — imports `get_config`; `_create_game_announcement` passes `rewards=game.rewards` to `format_game_announcement`; `_handle_post_transition_actions` sends `DMFormats.rewards_reminder` DM to the host via `_send_dm` when transitioning to COMPLETED with `remind_host_rewards=True` and `rewards` empty
- `shared/message_formats.py` — added `DMFormats.rewards_reminder(game_title, edit_url)` static method; added `DMPredicates.rewards_reminder(game_title)` predicate

## Added

- `.copilot-tracking/planning/changes/20260321-02-rewards-feature-changes.md` — this changes tracking file
- `tests/unit/shared/test_message_formats.py` — unit tests for `DMFormats.rewards_reminder` and `DMPredicates.rewards_reminder`
- `tests/unit/bot/test_game_message_formatter.py` — unit tests for `GameMessageFormatter.create_game_embed` rewards field

---

## Phase Progress

- [x] Phase 1: Database Migration
- [x] Phase 2: Backend Models & Schemas
- [x] Phase 3: API Service & Routes
- [x] Phase 4: Bot Formatters & Handlers
- [ ] Phase 5: Frontend
- [ ] Phase 6: Tests (TDD)
